#!/usr/bin/env python3
"""
Police Shootings of Dogs — Incident Tracker Generator

There is no national, systematic tracking of police shootings of dogs. This
script builds one from news coverage, using the same approach as Charles Fain
Lehman's flock-crime-tracker (flockstopscrime.com):

  1. discover  - Google News RSS (primary) + GDELT DOC 2.0 API (best-effort;
                 unreliable from GitHub Actions, never fails the run)
  2. extract   - pull article body text with trafilatura
  3. classify  - one Claude (Haiku) call per article: does it describe a
                 sworn officer firing a gun at a dog? plus structured fields
  4. dedupe    - one Claude call to fold a new article into an existing
                 incident (candidates blocked by state; the model adjudicates)
                 rather than creating a duplicate row
  5. store     - append qualifying incidents to datasets/dog-shootings.csv
                 (the durable dataset; git history is the audit log)
  6. emit      - aggregates JSON for the dashboard page + a published CSV copy

Outputs:
  - datasets/dog-shootings.csv           -- incident dataset (source of truth)
  - datasets/dog-shootings-seen-urls.json -- URL-level dedup cache
  - static/data/dog-shooting-tracker.json -- aggregates for the dashboard
  - static/data/dog-shootings.csv        -- published copy (download)

Consumed by:
  - content/dog-shooting-tracker/_index.md
  - static/js/dog-shooting-tracker.js

Requires ANTHROPIC_API_KEY in the environment (a GitHub Actions secret in CI),
except in --discover-only mode which only tests the news queries.

Usage:
  python scripts/generate_dog_shooting_tracker.py                 # daily run (last 3 days)
  python scripts/generate_dog_shooting_tracker.py --days 30       # wider window
  python scripts/generate_dog_shooting_tracker.py --discover-only # list candidate URLs, no LLM
  python scripts/generate_dog_shooting_tracker.py --limit 25      # cap articles classified this run
  python scripts/generate_dog_shooting_tracker.py --dry-run       # classify but don't write files
  python scripts/generate_dog_shooting_tracker.py --rebuild-json  # rebuild dashboard JSON from the CSV only
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# --------------------------------------------------------------------------- #
# 0. Configuration
# --------------------------------------------------------------------------- #

# NOT under data/ -- that is Hugo's reserved data directory, and Hugo tries to
# parse every file in it as site data. A CSV there fails the build outright:
# "unexpected data type [][]string in file dog-shootings.csv".
INCIDENTS_CSV = "datasets/dog-shootings.csv"
SEEN_URLS_FILE = "datasets/dog-shootings-seen-urls.json"
DASHBOARD_JSON = "static/data/dog-shooting-tracker.json"
PUBLISHED_CSV = "static/data/dog-shootings.csv"

MODEL = "claude-haiku-4-5"
# Bump when the classification prompt / schema changes materially, so rows can
# be traced to the logic that produced them.
PROMPT_VERSION = "2026-09-01.3"

DEFAULT_DAYS_BACK = 3
DEFAULT_ARTICLE_LIMIT = 60  # max NEW articles classified in one run (cost guard)
MAX_DEDUPE_CANDIDATES = 20   # cap on same-state rows sent to the dedupe model
# GDELT is unreliable from the GitHub Actions IP range: CI runs on 2026-09-01
# saw ~half of all requests connect-timeout even on trivial single-term queries
# at a 45s timeout. Query *shape* is no longer the problem (that was the OR
# groups); the endpoint itself is just slow/flaky from Actions. So the GDELT leg
# is built to finish fast even when it is mostly failing: a short list of
# non-overlapping queries, a smaller record cap (the server responds quicker for
# 100 than 250), and a longer pause so a burst of failures backs off instead of
# retrying into the same congestion.
GDELT_PAUSE_SEC = 5
# (connect, read). A *connect* timeout beyond ~10s is pointless — if GDELT has
# not accepted the socket by then it is down for this request, not slow. Read
# gets 30s for the JSON body. Successful CI queries returned in 2–25s, so this
# only clips genuine failures.
GDELT_TIMEOUT = (10, 30)
GDELT_RETRIES = 2
GDELT_MAX_RECORDS = 100
GNEWS_PAUSE_SEC = 1

# The CSV schema. Order matters — this is the on-disk column order.
CSV_FIELDS = [
    "id",                     # sequential int, stable
    "date_added",             # ISO date the row was first written
    "incident_date",          # ISO date of the shooting (may be approximate)
    "date_precision",         # day | month | approximate | unknown
    "city",
    "county",
    "state",                  # 2-letter USPS code
    "agency_name",            # full agency name, always populated when known
    "agency_type",            # see AGENCY_TYPES
    "on_duty",                # yes | no | unknown
    "officer_named",          # individual officer name ONLY if in an official record; else ""
    "dogs_fired_at",          # integer count of dogs fired at
    "dog_outcome",            # see DOG_OUTCOMES
    "dog_breed_reported",     # verbatim breed language from the source
    "dog_restrained",         # yes | no | unknown (leashed/crated/fenced/held)
    "circumstance",           # see CIRCUMSTANCES
    "warrant_type",           # search warrant | arrest warrant | no-knock | none | unknown
    "human_injured_by_fire",  # yes | no | unknown (a person hit by a shot aimed at the dog)
    "dept_response",          # short verbatim-ish summary of the department's stated position
    "litigation",             # none | claim/suit filed | settled | verdict | unknown
    "summary",                # 1-2 sentence neutral summary
    "source_name",            # primary outlet domain
    "source_url",             # primary article URL
    "additional_sources",     # space-separated additional URLs for the same incident
    "confidence",             # high | medium | low (model's self-rating)
    "prompt_version",         # PROMPT_VERSION that produced/updated the row
]

AGENCY_TYPES = [
    "municipal PD", "county SO", "state", "federal", "tribal", "campus", "other", "unknown",
]
DOG_OUTCOMES = [
    "killed", "injured-survived", "injured-euthanized", "unharmed", "unknown",
]
CIRCUMSTANCES = [
    "welfare check", "warrant service", "wrong address", "traffic stop",
    "loose/roaming dog", "unrelated call response", "pursuit", "domestic call",
    "noise complaint", "other", "unknown",
]
DATE_PRECISIONS = ["day", "month", "approximate", "unknown"]

# Every enum field, mapped to (allowed values, fallback). The classify tool
# schema already carries these enums, but `strict` mode is off (SDK-version
# compatibility — see requirements.txt), so the model can and does drift, e.g.
# circumstance "domestic call response" (a blend of "domestic call" and
# "unrelated call response"). Coerce rather than reject: a bad secondary field
# should not sink an otherwise-good incident row.
ENUM_FIELDS = {
    "date_precision": (DATE_PRECISIONS, "unknown"),
    "agency_type": (AGENCY_TYPES, "unknown"),
    "on_duty": (["yes", "no", "unknown"], "unknown"),
    "dog_outcome": (DOG_OUTCOMES, "unknown"),
    "dog_restrained": (["yes", "no", "unknown"], "unknown"),
    "circumstance": (CIRCUMSTANCES, "other"),
    "warrant_type": (["search warrant", "arrest warrant", "no-knock", "none", "unknown"], "unknown"),
    "human_injured_by_fire": (["yes", "no", "unknown"], "unknown"),
    "litigation": (["none", "claim/suit filed", "settled", "verdict", "unknown"], "unknown"),
    "confidence": (["high", "medium", "low"], "low"),
}


def coerce_enum(value, allowed, default):
    """Map a model-supplied enum value onto the allowed set. Exact match wins;
    then case-insensitive; then a single allowed value contained in a blended
    response ("domestic call response" -> "domestic call"); else the default."""
    v = (value or "").strip()
    if v in allowed:
        return v
    lv = v.lower()
    ci = [a for a in allowed if a.lower() == lv]
    if ci:
        return ci[0]
    contained = [a for a in allowed if a not in ("unknown", "other", "none") and a.lower() in lv]
    if len(contained) == 1:
        print(f"  ! coerced enum {value!r} -> {contained[0]!r}")
        return contained[0]
    if v and lv not in ("unknown", ""):
        print(f"  ! coerced unrecognised enum {value!r} -> {default!r}")
    return default


def clean_incident_date(fields):
    """(incident_date, date_precision). A date is kept ONLY if it is a real
    YYYY-MM-DD *and* the model quoted its evidence in incident_date_source.

    The classifier fabricates plausible dates when the article gives none
    (observed: 2024-01-11 assigned to two unrelated incidents across two runs,
    plus a cluster of 2026-01-01 / 2026-01-09). A fabricated firm date is worse
    than a blank one -- it splits one real incident into several rows. Requiring
    a quote forces the model to show its work; no quote -> no date."""
    prec = coerce_enum(fields.get("date_precision"), DATE_PRECISIONS, "unknown")
    evidence = (fields.get("incident_date_source") or "").strip()
    raw = (fields.get("incident_date") or "").strip()
    m = re.match(r"^\d{4}-\d{2}-\d{2}", raw)
    if not m or not evidence:
        if raw and not evidence:
            print(f"  ! incident_date {raw!r} dropped -- no incident_date_source quote")
        return "", "unknown"
    iso = m.group(0)
    try:
        datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return "", "unknown"
    if prec == "unknown":
        prec = "day"
    return iso, prec

# Discovery — GDELT DOC 2.0 API queries (ANDs terms; quotes for phrases).
# `sourcecountry:US` is appended per query. The LLM is the real relevance gate.
#
# BEST-EFFORT ONLY. GDELT is unreliable from GitHub Actions runners: three CI
# runs on 2026-09-01 saw it connect-time-out and 429 on nearly every request
# (shared runner IP pool -> GDELT's per-IP rate limiter). generate_police_
# shooting_news.py hits the same wall. A GDELT failure does NOT fail the run;
# Google News carries discovery. If Google-News-only breadth proves too thin,
# the fix is a GDELT proxy on a non-Actions IP (Val.town / Cloudflare Worker),
# not more retries here.
#
# The list is kept SHORT and non-overlapping so the leg's wall-clock stays
# bounded when it is mostly failing. Measured yields, 2026-09-01, 14d window:
#   "shot the dog" police  39   |  "officer shot" dog  38   <- the two producers
#   "police shot" dog       5   |  "deputy shot" dog     5
#   "shot the dog" deputy   1   |  "shot a dog" police   3   |  everything else 0
# GDELT matches article *body* text, which is past tense, so the present-tense
# "shoots" phrasings (0 hits here) live only in GOOGLE_NEWS_PHRASINGS.
GDELT_QUERIES = [
    '"shot the dog" police',      # 39 — top producer
    '"officer shot" dog',         # 38 — top producer
    '"police shot" dog',          # 5  — distinct "police shot <X>" framing
    '"deputy shot" dog',          # 5  — sheriff/deputy coverage
    '"shot the family dog"',      # pet/home context, low volume but high precision
    '"opened fire" dog police',   # 13 in run #1 — a different verb entirely
    'puppycide',                  # term of art; GDELT corpus larger than GNews
]

# Google News RSS — one narrow feed per phrasing; `when:Nd` limits recency.
#
# Unquoted terms are AND-joined, which is far too loose: "police shot dog"
# matched a dog killed in a car crash, a man shot while walking a dog, and a
# story about apple picking. Quoting forces adjacency. Present tense matters
# too — headlines say "shoots", not "shot". Hit counts below are from a 21-day
# probe on 2026-09-01, with on-topic counts eyeballed from the titles.
#
# Deliberately dropped, all of them near-zero precision: bare "police shot dog"
# / "officer shot dog" / "deputy shot dog" (AND-joined, ~10%), "police killed
# dog" (69 hits, almost none relevant), "officer kills dog" and "police shot
# and killed" dog (returned an outlet's general feed), "shot by a police
# officer" dog (0 relevant), and "puppycide" (0 hits on Google News — it is
# kept in GDELT_QUERIES, where the corpus is larger).
# GDELT is unreliable from GitHub Actions (see GDELT_QUERIES note), so Google
# News is effectively the sole discovery source and this list has to carry the
# breadth GDELT used to add. The first block is the 2026-09-01 probe set (hit /
# on-topic counts from a 21-day window). The second block is unverified — added
# to widen agency coverage (state police, generic "police"), verbs ("opened fire
# on"), and the "family dog" pet-context signal — and should be pruned after the
# next real run against its own yield.
GOOGLE_NEWS_PHRASINGS = [
    # -- verified 2026-09-01 --
    '"deputy shoots dog"',       # 9 hits, nearly all on-topic
    '"officer shoots dog"',      # 5 hits, 4 on-topic
    '"deputies shoot dog"',      # 1 hit, on-topic
    '"deputy shoots pit bull"',  # 2 hits, both on-topic
    '"shoots dog during"',       # 4 hits, 3 on-topic
    '"deputy shot a dog"',       # 4 hits, all on-topic
    '"officer shot a dog"',      # 4 hits, all on-topic
    '"police shot a dog"',       # 2 hits, 1 on-topic
    '"deputy shot the dog"',     # 1 hit, on-topic
    '"dog shot by police"',      # 5 hits, ~3 on-topic
    # -- unverified, added 2026-09-01 to replace GDELT breadth --
    '"police shoot dog"',        # plural-verb headline form, "police" as agency
    '"police shoot a dog"',
    '"officer shoots a dog"',
    '"trooper shoots dog"',      # state police — no coverage in the verified set
    '"state trooper shoots dog"',
    '"cop shoots dog"',          # common tabloid headline verb
    '"shoots family dog"',       # "family dog" = strong pet/home-context signal
    '"shot the family dog"',
    '"dog shot by deputy"',      # mirrors the working "dog shot by police"
    '"dog shot by officer"',
    '"opened fire on the dog"',  # migrated from GDELT_QUERIES
    '"shoots dog while"',        # parallel to the working "shoots dog during"
]

# Country-code TLDs for the English-language markets whose police-and-dog
# coverage otherwise surfaces alongside US stories. See _non_us().
NON_US_TLDS = {
    "uk", "co.uk", "ca", "au", "com.au", "nz", "co.nz", "ie", "in", "za",
    "ph", "sg", "pk", "ng", "ke",
}

# Wire services, aggregators, and vendor/advocacy domains we don't want as a
# primary source (kept out of discovery entirely).
DOMAIN_BLOCKLIST = {
    "prnewswire.com", "businesswire.com", "globenewswire.com", "newswire.com",
    "einnews.com", "finance.yahoo.com", "msn.com", "news.google.com",
    "reddit.com", "facebook.com", "twitter.com", "x.com", "youtube.com",
    "tiktok.com", "change.org", "gofundme.com",
}

STATE_NAME_BY_ABBR = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}
VALID_STATES = set(STATE_NAME_BY_ABBR)

# Spoofed browser UA — GDELT rejects obvious bot agents.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"
)


# --------------------------------------------------------------------------- #
# 1. Discovery
# --------------------------------------------------------------------------- #

def _domain(url):
    m = re.match(r"https?://([^/]+)/?", url or "")
    if not m:
        return ""
    host = m.group(1).lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _blocked(url):
    host = _domain(url)
    return any(host == d or host.endswith("." + d) for d in DOMAIN_BLOCKLIST)


def _non_us(url):
    """True for obvious non-US publishers, by country-code TLD.

    GDELT gets `sourcecountry:US`; Google News has no working equivalent and
    leaked ctvnews.ca, aptnnews.ca and dailystar.co.uk into a 21-day probe.
    The classifier already scopes to sworn *U.S.* officers and would reject
    these, so this is purely to avoid paying for the call. It is deliberately
    TLD-only -- non-US outlets on .com (ndtv.com, say) still reach the LLM,
    which is the right place to catch them.
    """
    host = _domain(url)
    return any(host == t or host.endswith("." + t) for t in NON_US_TLDS)


def parse_gdelt_date(gdelt_date):
    try:
        return datetime.strptime(gdelt_date, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_gdelt(query, days_back):
    """One GDELT DOC 2.0 query -> list of {title, url, source, date}.

    Returns None -- NOT an empty list -- when every attempt fails. A query that
    genuinely matches nothing and a query that timed out every retry are very
    different facts for a tracker whose whole claim is completeness, and the
    caller has to be able to tell them apart to report honestly.
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f"{query} sourcecountry:US",
        "mode": "artlist",
        "maxrecords": GDELT_MAX_RECORDS,
        "format": "json",
        "timespan": f"{days_back}d",
    }
    for attempt in range(GDELT_RETRIES):
        try:
            resp = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT},
                timeout=GDELT_TIMEOUT,
            )
            if resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            return [
                {
                    "title": (a.get("title") or "").strip(),
                    "url": a.get("url", ""),
                    "source": a.get("domain", ""),
                    "date": parse_gdelt_date(a.get("seendate", "")),
                }
                for a in articles
                if a.get("url")
            ]
        except Exception as e:  # noqa: BLE001 - a single bad query shouldn't kill the run
            print(f"  ! GDELT error for {query!r}: {e}")
            time.sleep(3)
    return None


def fetch_google_news(phrasing, days_back):
    """One Google News RSS feed -> list of {title, url, source, date}."""
    try:
        import feedparser
    except ImportError:
        print("  ! feedparser not installed; skipping Google News")
        return []

    q = requests.utils.quote(f"{phrasing} when:{days_back}d")
    feed_url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    out = []
    try:
        parsed = feedparser.parse(feed_url, agent=USER_AGENT)
        for entry in parsed.entries:
            link = entry.get("link", "")
            src = ""
            if isinstance(entry.get("source"), dict):
                src = entry["source"].get("title", "")
            published = entry.get("published_parsed")
            date = (
                datetime(*published[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if published
                else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            out.append(
                {
                    "title": entry.get("title", "").strip(),
                    "url": link,
                    "source": src or _domain(link),
                    "date": date,
                    # Google wraps every link in a news.google.com redirect. We
                    # resolve it lazily (see resolve_url) because decoding costs
                    # ~4s per URL and only `--limit` of these are ever used.
                    "needs_decode": "news.google.com" in link,
                }
            )
    except Exception as e:  # noqa: BLE001
        print(f"  ! Google News error for {phrasing!r}: {e}")
    return out


def resolve_url(article):
    """Resolve a Google News redirect to the publisher URL, in place.

    Called only for candidates that survive sorting and `--limit`; decoding is
    ~4s per URL, so doing it for every discovered entry made a routine run take
    ~40 minutes. Returns True if `article["url"]` is usable afterwards.
    """
    if not article.get("needs_decode"):
        return True
    try:
        from googlenewsdecoder import gnewsdecoder
    except Exception:  # noqa: BLE001
        return False  # can't reach the publisher URL; skip rather than fetch google
    try:
        decoded = gnewsdecoder(article["url"], interval=1)
    except Exception:  # noqa: BLE001
        return False
    if not (decoded.get("status") and decoded.get("decoded_url")):
        return False
    article["url"] = decoded["decoded_url"]
    article["needs_decode"] = False
    if not article.get("source"):
        article["source"] = _domain(article["url"])
    return True


def discover(days_back, seen_urls):
    """Run every query, dedupe by URL, drop blocked domains and already-seen
    URLs. Returns (candidates, failed_queries) — failed_queries lists the GDELT
    queries whose every retry failed, which the caller must surface: a silent
    under-collection is the one failure mode this tracker cannot tolerate."""
    candidates = {}
    failed_queries = []

    print(f"GDELT ({len(GDELT_QUERIES)} queries, {days_back}d window)")
    for query in GDELT_QUERIES:
        articles = fetch_gdelt(query, days_back)
        if articles is None:
            failed_queries.append(query)
            print(f"  FAIL  {query}   (all retries failed -- NOT a real zero)")
            time.sleep(GDELT_PAUSE_SEC)
            continue
        print(f"  {len(articles):4d}  {query}")
        for a in articles:
            candidates.setdefault(a["url"], a)
        time.sleep(GDELT_PAUSE_SEC)

    print(f"Google News ({len(GOOGLE_NEWS_PHRASINGS)} feeds)")
    for phrasing in GOOGLE_NEWS_PHRASINGS:
        articles = fetch_google_news(phrasing, days_back)
        print(f"  {len(articles):4d}  {phrasing}")
        for a in articles:
            candidates.setdefault(a["url"], a)
        time.sleep(GNEWS_PAUSE_SEC)

    # news.google.com is itself blocklisted, so the blocklist check has to wait
    # until after resolve_url() — otherwise every Google News hit is dropped here.
    fresh = [
        a
        for url, a in candidates.items()
        if url not in seen_urls
        and (a.get("needs_decode") or (not _blocked(url) and not _non_us(url)))
        and len(a["title"]) >= 15
    ]
    fresh.sort(key=lambda a: a["date"], reverse=True)
    print(f"\n{len(candidates)} unique URLs -> {len(fresh)} new, unblocked candidates")
    if failed_queries:
        print(
            f"\n!! {len(failed_queries)}/{len(GDELT_QUERIES)} GDELT queries FAILED "
            f"(not empty results): {failed_queries}"
        )
    return fresh, failed_queries


# --------------------------------------------------------------------------- #
# 2. Article text extraction
# --------------------------------------------------------------------------- #

def extract_article_text(url):
    try:
        import trafilatura
    except ImportError:
        print("  ! trafilatura not installed", file=sys.stderr)
        return None
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded, include_comments=False, include_tables=False, favor_precision=True
        )
        if text and len(text) > 200:
            return text[:12000]
    except Exception as e:  # noqa: BLE001
        print(f"  ! extract failed for {url}: {e}")
    return None


# --------------------------------------------------------------------------- #
# 3. Classification (one Claude call per article)
# --------------------------------------------------------------------------- #

CLASSIFY_SYSTEM = f"""You extract structured data about ONE kind of event: a sworn U.S. law-enforcement officer discharging a firearm AT or TOWARD a dog.

INCLUDE an article only if it reports a specific, concrete incident (a real event on a real date/place) in which:
  - a SWORN law-enforcement officer (municipal police, county sheriff/deputy, state police/trooper, federal agent, tribal police, campus police), AND
  - fired a gun AT or TOWARD a dog (any outcome: killed, wounded, or missed).

EXCLUDE (set qualifies=false) if ANY of these apply:
  - the shooter was an animal-control officer, a civilian, a security guard, or a game warden acting in a wildlife capacity
  - no firearm was involved (baton, Taser, catch-pole, vehicle, or the dog was only impounded/euthanized by a vet)
  - the animal was not a dog (cat, livestock, or wildlife such as a deer, bear, or coyote — including an officer euthanizing an animal injured by a car)
  - the dog shot was the officer's own K-9 / police dog / a service dog
  - it is about policy, training, legislation, procurement, a lawsuit ruling with no described incident, an opinion/column, or aggregate statistics with no specific incident
  - it is a first-report of an unconfirmed claim with no identifiable agency or location

Report fields ONLY from what the article states. If the article does not state a field, use "unknown" for the enum fields and "" for the free-text fields (city, county, incident_date, officer_named, dog_breed_reported). Never infer from general knowledge or from the outlet's location.

officer_named: give an individual officer's name ONLY if the article attributes it to an official record (a charging document, a lawsuit, a department statement/press release, or a disciplinary record). Otherwise leave it "".

incident_date + incident_date_source: FIRST, copy into incident_date_source the exact words from the article that establish when the shooting happened — e.g. "Wednesday afternoon", "on Aug. 20", "earlier this month", "last summer". If the article contains no such words, incident_date_source MUST be "" AND incident_date MUST be "". Only if you quoted something do you fill incident_date: the date the shooting happened (NOT the publication date), ISO YYYY-MM-DD. You MAY resolve a weekday relative to the publication date ("on Tuesday"). If only the month is known, use the first of that month with date_precision=month; if only a season/year, estimate and set date_precision=approximate. NEVER invent a day, month, or year — a fabricated date is worse than a blank one because it silently splits one incident into several rows. Never output the literal word "unknown"; use "".

summary: 1-2 neutral sentences. Attribute claims about the dog's behavior to their source ("officers said the dog charged").

confidence: high if a named agency + date + outcome are all clearly stated; low if the incident is vague or single-sourced.

Prompt version: {PROMPT_VERSION}"""

CLASSIFY_TOOL = {
    "name": "record_incident",
    "description": "Record whether the article describes a qualifying incident and the extracted fields.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "qualifies": {"type": "boolean"},
            "reason": {"type": "string", "description": "one sentence: why it does or doesn't qualify"},
            "incident_date_source": {"type": "string", "description": "exact words from the article that state when the shooting happened; empty string if the article says nothing about timing"},
            "incident_date": {"type": "string", "description": "YYYY-MM-DD, filled ONLY when incident_date_source is non-empty; never guessed"},
            "date_precision": {"type": "string", "enum": DATE_PRECISIONS},
            "city": {"type": "string"},
            "county": {"type": "string"},
            "state": {"type": "string", "description": "2-letter USPS code or empty"},
            "agency_name": {"type": "string"},
            "agency_type": {"type": "string", "enum": AGENCY_TYPES},
            "on_duty": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "officer_named": {"type": "string"},
            "dogs_fired_at": {"type": "integer"},
            "dog_outcome": {"type": "string", "enum": DOG_OUTCOMES},
            "dog_breed_reported": {"type": "string"},
            "dog_restrained": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "circumstance": {"type": "string", "enum": CIRCUMSTANCES},
            "warrant_type": {
                "type": "string",
                "enum": ["search warrant", "arrest warrant", "no-knock", "none", "unknown"],
            },
            "human_injured_by_fire": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "dept_response": {"type": "string"},
            "litigation": {
                "type": "string",
                "enum": ["none", "claim/suit filed", "settled", "verdict", "unknown"],
            },
            "summary": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": [
            "qualifies", "reason", "incident_date_source", "incident_date",
            "date_precision", "city", "county",
            "state", "agency_name", "agency_type", "on_duty", "officer_named",
            "dogs_fired_at", "dog_outcome", "dog_breed_reported", "dog_restrained",
            "circumstance", "warrant_type", "human_injured_by_fire", "dept_response",
            "litigation", "summary", "confidence",
        ],
    },
}


HEADLINE_ONLY_NOTE = (
    "\n\nNOTE: the article body could not be retrieved (it is a video or "
    "script-only page). Classify from the HEADLINE and URL alone. Set "
    "qualifies=true ONLY if the headline itself unambiguously states that a "
    "sworn law-enforcement officer fired a gun at a dog (e.g. \"Sheriff's "
    "deputy shoots dog during arrest\"). If the headline is ambiguous about the "
    "shooter, the weapon, or the animal, set qualifies=false. Set confidence=low "
    "and leave every field you cannot determine from the headline as "
    "unknown/empty, including incident_date."
)


def classify_article(client, title, text, url):
    """Return the tool input dict, or None on a hard API error. text=None means
    body extraction failed -> classify from the headline under strict rules."""
    if text:
        user = f"Article URL: {url}\nHeadline: {title}\n\nArticle text:\n{text}"
    else:
        user = f"Article URL: {url}\nHeadline: {title}{HEADLINE_ONLY_NOTE}"
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=CLASSIFY_SYSTEM,
            tools=[CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "record_incident"},
            messages=[{"role": "user", "content": user}],
        )
    except Exception as e:  # noqa: BLE001
        print(f"  ! classify API error: {e}")
        return None
    for block in resp.content:
        if block.type == "tool_use" and block.name == "record_incident":
            return block.input
    return None


# --------------------------------------------------------------------------- #
# 4. Deduplication (fold a new article into an existing incident)
# --------------------------------------------------------------------------- #

DEDUPE_TOOL = {
    "name": "dedupe_decision",
    "description": "Decide whether the new incident is the same real-world event as one already in the list.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "is_duplicate": {"type": "boolean"},
            "matching_id": {"type": "integer", "description": "id of the matching row, or -1 if none"},
        },
        "required": ["is_duplicate", "matching_id"],
    },
}


def find_duplicate(client, new_row, existing_rows):
    """Block candidates by state, then ask the model. Returns the matching id or
    None.

    Blocking is by state ONLY -- no date window. Model-supplied dates are not
    trustworthy enough to gate on: a fabricated date on one copy of an incident
    would put it outside the window from the real-dated copy and split one event
    into several rows (observed exactly that with the Sunland Park incident).
    The LLM adjudicates every same-state pair; MAX_DEDUPE_CANDIDATES caps cost."""
    if not new_row.get("state"):
        return None
    candidates = [r for r in existing_rows if r.get("state") == new_row["state"]]
    if not candidates:
        return None
    candidates.sort(key=lambda r: r.get("incident_date", ""), reverse=True)
    candidates = candidates[:MAX_DEDUPE_CANDIDATES]

    def brief(r):
        return {
            "id": int(r["id"]),
            "incident_date": r.get("incident_date", "") or "(not stated)",
            "city": r.get("city", ""),
            "county": r.get("county", ""),
            "state": r.get("state", ""),
            "agency_name": r.get("agency_name", ""),
            "dog_outcome": r.get("dog_outcome", ""),
            "summary": r.get("summary", ""),
        }

    payload = {
        "new_incident": {
            "incident_date": new_row.get("incident_date", "") or "(not stated)",
            "city": new_row.get("city", ""),
            "county": new_row.get("county", ""),
            "state": new_row.get("state", ""),
            "agency_name": new_row.get("agency_name", ""),
            "dog_outcome": new_row.get("dog_outcome", ""),
            "summary": new_row.get("summary", ""),
        },
        "existing_incidents": [brief(r) for r in candidates],
    }
    system = (
        "You decide whether a new dog-shooting incident is the SAME real-world event as one "
        "already recorded. Same event = the same shooting: same agency, same place, same dog, "
        "and dates that agree (or one/both dates '(not stated)' -- a missing date is NOT evidence "
        "the events differ; judge on agency, location, and the summary). Many outlets cover one "
        "incident, so near-identical summaries from the same agency and city are the SAME event. "
        "Merely similar incidents -- different city, or clearly different dates -- are NOT "
        "duplicates. If genuinely unsure, it is NOT a duplicate."
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=system,
            tools=[DEDUPE_TOOL],
            tool_choice={"type": "tool", "name": "dedupe_decision"},
            messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
        )
    except Exception as e:  # noqa: BLE001
        print(f"  ! dedupe API error: {e}")
        return None
    for block in resp.content:
        if block.type == "tool_use" and block.name == "dedupe_decision":
            if block.input.get("is_duplicate") and int(block.input.get("matching_id", -1)) >= 0:
                mid = int(block.input["matching_id"])
                if any(int(r["id"]) == mid for r in candidates):
                    return mid
    return None


# --------------------------------------------------------------------------- #
# 5. Storage
# --------------------------------------------------------------------------- #

def load_incidents():
    if not os.path.exists(INCIDENTS_CSV):
        return []
    with open(INCIDENTS_CSV, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_incidents(rows):
    rows = sorted(rows, key=lambda r: int(r["id"]))
    os.makedirs(os.path.dirname(INCIDENTS_CSV), exist_ok=True)
    with open(INCIDENTS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})


def publish_csv_copy():
    if not os.path.exists(INCIDENTS_CSV):
        return
    os.makedirs(os.path.dirname(PUBLISHED_CSV), exist_ok=True)
    with open(INCIDENTS_CSV, "r", encoding="utf-8") as src, \
         open(PUBLISHED_CSV, "w", encoding="utf-8", newline="") as dst:
        dst.write(src.read())


def load_seen_urls():
    if not os.path.exists(SEEN_URLS_FILE):
        return set()
    try:
        with open(SEEN_URLS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen_urls(seen):
    os.makedirs(os.path.dirname(SEEN_URLS_FILE), exist_ok=True)
    with open(SEEN_URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=0)


def next_id(rows):
    return max((int(r["id"]) for r in rows), default=0) + 1


def make_row(fields, article, row_id):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    incident_date, date_precision = clean_incident_date(fields)
    enums = {
        f: coerce_enum(fields.get(f), allowed, default)
        for f, (allowed, default) in ENUM_FIELDS.items()
    }
    row = {k: "" for k in CSV_FIELDS}
    row.update(
        {
            "id": row_id,
            "date_added": today,
            "incident_date": incident_date,
            "date_precision": date_precision,
            "city": fields.get("city", "").strip(),
            "county": fields.get("county", "").strip(),
            "state": (fields.get("state") or "").strip().upper(),
            "agency_name": fields.get("agency_name", "").strip(),
            "agency_type": enums["agency_type"],
            "on_duty": enums["on_duty"],
            "officer_named": fields.get("officer_named", "").strip(),
            "dogs_fired_at": fields.get("dogs_fired_at", "") or "",
            "dog_outcome": enums["dog_outcome"],
            "dog_breed_reported": fields.get("dog_breed_reported", "").strip(),
            "dog_restrained": enums["dog_restrained"],
            "circumstance": enums["circumstance"],
            "warrant_type": enums["warrant_type"],
            "human_injured_by_fire": enums["human_injured_by_fire"],
            "dept_response": fields.get("dept_response", "").strip(),
            "litigation": enums["litigation"],
            "summary": fields.get("summary", "").strip(),
            "source_name": article.get("source", "") or _domain(article.get("url", "")),
            "source_url": article.get("url", ""),
            "additional_sources": "",
            "confidence": enums["confidence"],
            "prompt_version": PROMPT_VERSION,
        }
    )
    return row


# --------------------------------------------------------------------------- #
# 6. Dashboard aggregates
# --------------------------------------------------------------------------- #

RECENT_LIMIT = 30


def _year(iso):
    try:
        return int(iso[:4])
    except Exception:
        return None


def _count(labels):
    out = {}
    for lab in labels:
        if lab:
            out[lab] = out.get(lab, 0) + 1
    return [{"label": k, "count": v} for k, v in sorted(out.items(), key=lambda kv: -kv[1])]


def build_dashboard_json(rows):
    dated = [r for r in rows if _year(r.get("incident_date", ""))]
    years = sorted({_year(r["incident_date"]) for r in dated})
    now = datetime.now(timezone.utc)
    current_year = now.year
    doy = now.timetuple().tm_yday

    yearly = {y: 0 for y in years}
    for r in dated:
        yearly[_year(r["incident_date"])] += 1

    def in_ytd(r, yr):
        try:
            d = datetime.strptime(r["incident_date"][:10], "%Y-%m-%d")
            return d.year == yr and d.timetuple().tm_yday <= doy
        except Exception:
            return False

    ytd = sum(1 for r in dated if in_ytd(r, current_year))
    prior_ytd = sum(1 for r in dated if in_ytd(r, current_year - 1))

    state_counts = {}
    for r in rows:
        st = (r.get("state") or "").upper()
        if st in VALID_STATES:
            state_counts[st] = state_counts.get(st, 0) + 1

    recent = sorted(
        [r for r in rows if r.get("incident_date")],
        key=lambda r: r["incident_date"],
        reverse=True,
    )[:RECENT_LIMIT]

    incident_dates = [r["incident_date"][:10] for r in dated]
    total_sources = 0
    for r in rows:
        total_sources += 1 + len([u for u in (r.get("additional_sources") or "").split() if u])

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_incidents": len(rows),
        "total_sources": total_sources,
        "date_range": {
            "earliest": min(incident_dates) if incident_dates else None,
            "latest": max(incident_dates) if incident_dates else None,
        },
        "stats": {
            "current_year": current_year,
            "prior_year": current_year - 1,
            "current_year_to_date": ytd,
            "prior_year_same_point": prior_ytd,
            "as_of_day_of_year": doy,
        },
        "yearly_counts": [{"year": y, "count": yearly[y]} for y in years],
        "outcome_breakdown": _count([r.get("dog_outcome") for r in rows]),
        "circumstance_breakdown": _count([r.get("circumstance") for r in rows]),
        "agency_type_breakdown": _count([r.get("agency_type") for r in rows]),
        "state_counts": [
            {"state": s, "name": STATE_NAME_BY_ABBR[s], "count": c}
            for s, c in sorted(state_counts.items(), key=lambda kv: -kv[1])
        ],
        "human_injured_count": sum(1 for r in rows if r.get("human_injured_by_fire") == "yes"),
        "recent_incidents": [
            {
                "incident_date": r.get("incident_date", ""),
                "date_precision": r.get("date_precision", ""),
                "city": r.get("city", ""),
                "state": r.get("state", ""),
                "agency_name": r.get("agency_name", ""),
                "circumstance": r.get("circumstance", ""),
                "dog_outcome": r.get("dog_outcome", ""),
                "human_injured_by_fire": r.get("human_injured_by_fire", ""),
                "summary": r.get("summary", ""),
                "source_url": r.get("source_url", ""),
                "source_name": r.get("source_name", ""),
                "additional_sources": [
                    u for u in (r.get("additional_sources") or "").split() if u
                ],
                "confidence": r.get("confidence", ""),
            }
            for r in recent
        ],
    }


def write_dashboard_json(rows):
    data = build_dashboard_json(rows)
    os.makedirs(os.path.dirname(DASHBOARD_JSON), exist_ok=True)
    with open(DASHBOARD_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


# --------------------------------------------------------------------------- #
# 7. Validation
# --------------------------------------------------------------------------- #

def validate_rows(rows):
    """Return a list of problem strings (empty = clean)."""
    problems = []
    seen_ids = set()
    today = datetime.now(timezone.utc).date()
    for r in rows:
        rid = r.get("id", "")
        if rid in seen_ids:
            problems.append(f"duplicate id {rid}")
        seen_ids.add(rid)
        st = (r.get("state") or "").upper()
        if st and st not in VALID_STATES:
            problems.append(f"id {rid}: bad state {st!r}")
        if r.get("circumstance") and r["circumstance"] not in CIRCUMSTANCES:
            problems.append(f"id {rid}: bad circumstance {r['circumstance']!r}")
        if r.get("dog_outcome") and r["dog_outcome"] not in DOG_OUTCOMES:
            problems.append(f"id {rid}: bad dog_outcome {r['dog_outcome']!r}")
        idate = r.get("incident_date", "")
        if idate:
            try:
                if datetime.strptime(idate[:10], "%Y-%m-%d").date() > today + timedelta(days=2):
                    problems.append(f"id {rid}: future incident_date {idate}")
            except Exception:
                problems.append(f"id {rid}: unparseable incident_date {idate!r}")
        if _blocked(r.get("source_url", "")):
            problems.append(f"id {rid}: blocklisted source domain {r.get('source_url')}")
    return problems


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def get_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    try:
        import anthropic
    except ImportError:
        print("ERROR: the 'anthropic' package is not installed.", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS_BACK, help="discovery window in days")
    ap.add_argument("--limit", type=int, default=DEFAULT_ARTICLE_LIMIT, help="max new articles classified")
    ap.add_argument("--discover-only", action="store_true", help="list candidate URLs and exit (no LLM)")
    ap.add_argument("--dry-run", action="store_true", help="classify but do not write any files")
    ap.add_argument("--rebuild-json", action="store_true", help="rebuild dashboard JSON from the CSV and exit")
    args = ap.parse_args()

    if args.rebuild_json:
        rows = load_incidents()
        data = write_dashboard_json(rows)
        publish_csv_copy()
        print(f"Rebuilt {DASHBOARD_JSON} from {len(rows)} incidents.")
        return

    incidents = load_incidents()
    seen_urls = load_seen_urls()
    print(f"Loaded {len(incidents)} existing incidents, {len(seen_urls)} seen URLs.\n")

    candidates, failed_queries = discover(args.days, seen_urls)

    if args.discover_only:
        print("\n--- candidates ---")
        for a in candidates:
            # Google entries still hold the redirect URL here, so show the RSS
            # publisher name instead of a uniform "news.google.com".
            label = a.get("source") or _domain(a["url"])
            print(f"{a['date'][:10]}  {label[:28]:28s}  {a['title'][:90]}")
        print(f"\n{len(candidates)} candidates. (--discover-only: no classification, nothing written.)")
        return

    candidates = candidates[: args.limit]
    if not candidates:
        print("No new candidates. Rebuilding dashboard JSON from existing data.")
        if not args.dry_run:
            write_dashboard_json(incidents)
            publish_csv_copy()
        return

    client = get_client()

    processed = 0
    errors = 0
    added = 0
    merged = 0
    for a in candidates:
        discovered_url = a["url"]
        # Mark the as-discovered URL seen even if we skip it below, so we never
        # retry it -- and, for Google wrappers, never pay to decode it twice.
        seen_urls.add(discovered_url)
        if not resolve_url(a):
            print(f"  skip (unresolved)  {a['title'][:60]}")
            continue
        # Checks deferred out of discover() until the real publisher URL exists.
        if _blocked(a["url"]):
            print(f"  skip (blocked domain)  {_domain(a['url'])}")
            continue
        if _non_us(a["url"]):
            print(f"  skip (non-US)  {_domain(a['url'])}")
            continue
        if a["url"] != discovered_url:
            if a["url"] in seen_urls:
                continue  # same article, already reached via another feed
            seen_urls.add(a["url"])
        text = extract_article_text(a["url"])
        if not text:
            # Video / script-only pages (common for the most-covered incidents).
            # Fall back to a strict headline-only classification rather than
            # dropping the article -- otherwise an incident whose entire coverage
            # is video pages is lost.
            print(f"  (no body text; classifying from headline)  {a['title'][:60]}")
        processed += 1
        fields = classify_article(client, a["title"], text, a["url"])
        if fields is None:
            errors += 1
            continue
        if not fields.get("qualifies"):
            print(f"  no  — {fields.get('reason', '')[:80]}")
            continue
        if not any((fields.get(k) or "").strip() for k in ("state", "city", "agency_name")):
            print(f"  skip (too thin: no state/city/agency)  {a['title'][:60]}")
            continue

        row = make_row(fields, a, next_id(incidents))
        dup_id = find_duplicate(client, row, incidents)
        if dup_id is not None:
            for r in incidents:
                if int(r["id"]) == dup_id:
                    extra = [u for u in (r.get("additional_sources") or "").split() if u]
                    if a["url"] not in extra and a["url"] != r.get("source_url"):
                        extra.append(a["url"])
                        r["additional_sources"] = " ".join(extra)
                    merged += 1
                    print(f"  merge -> incident {dup_id}  ({a['title'][:60]})")
                    break
        else:
            incidents.append(row)
            added += 1
            print(f"  ADD  incident {row['id']}: {row['state']} {row['incident_date']} "
                  f"{row['agency_name'][:40]} — {row['dog_outcome']}")

    print(f"\nprocessed={processed} added={added} merged={merged} errors={errors}")

    if processed and errors / processed > 0.5:
        print("ERROR: >50% of processed articles errored — not writing.", file=sys.stderr)
        sys.exit(1)

    problems = validate_rows(incidents)
    if problems:
        print("VALIDATION PROBLEMS:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("--dry-run: nothing written.")
        return

    save_incidents(incidents)
    save_seen_urls(seen_urls)
    data = write_dashboard_json(incidents)
    publish_csv_copy()
    print(f"\nWrote {INCIDENTS_CSV} ({len(incidents)} incidents), {DASHBOARD_JSON}, {PUBLISHED_CSV}.")
    print(f"Dashboard: {data['total_incidents']} incidents, "
          f"{data['stats']['current_year_to_date']} YTD.")

    # GDELT failing is NOT a run failure. It is unreliable from GitHub Actions
    # runners (shared IP pool -> GDELT's per-IP rate limiter; confirmed failing
    # for generate_police_shooting_news.py too, with 429s). It is best-effort
    # additive recall on top of Google News, which is the dependable source.
    # The `!! N/M GDELT queries FAILED` line from discover() is the record.
    if failed_queries:
        print(
            f"\nnote: {len(failed_queries)}/{len(GDELT_QUERIES)} GDELT queries failed "
            f"this run (best-effort source; Google News carried discovery)."
        )


if __name__ == "__main__":
    main()
