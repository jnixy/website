#!/usr/bin/env python3
"""
Police Shootings of Dogs — Incident Tracker Generator

There is no national, systematic tracking of police shootings of dogs. This
script builds one from news coverage, using the same approach as Charles Fain
Lehman's flock-crime-tracker (flockstopscrime.com):

  1. discover  - Google News RSS, one narrow query per headline phrasing
  2. extract   - pull article body text with trafilatura
  3. classify  - one Claude (Haiku) call per article: does it describe a
                 sworn officer firing a gun at a dog? plus structured fields
  4. dedupe    - one Claude call to fold a new article into an existing
                 incident (candidates blocked by state; the model adjudicates)
                 rather than creating a duplicate row
  5. store     - append qualifying incidents to datasets/dog-shootings.csv
                 (the durable dataset; git history is the audit log)
  6. emit      - aggregates JSON for the dashboard page + a published CSV copy

Agency records (--official): some departments publish incident-level OIS lists
that include dog shootings (scripts/dog_tracker_official.py). Each record goes
through the same classifier, then is matched to an existing incident (marked
discovery=both) or added as a new one (discovery=official). This cross-check
shows how much media discovery misses.

Outputs:
  - datasets/dog-shootings.csv            -- incident dataset (source of truth)
  - datasets/dog-shootings-seen-urls.json -- URL-level dedup cache
  - datasets/dog-shootings-excluded.json  -- URLs a human judged NOT a qualifying incident
  - static/data/dog-shooting-tracker.json -- aggregates for the dashboard
  - static/data/dog-shootings.csv         -- published copy (download)

Consumed by:
  - content/dog-shooting-tracker/_index.md
  - static/js/dog-shooting-tracker.js

Human review: edit datasets/dog-shootings.csv directly (fix a field, set
`reviewed` to yes, or delete a false-positive row), then run --rebuild-json.
An automated run never overwrites an existing row's fields -- it only appends
new rows and appends URLs to `additional_sources` on a dedupe match -- so hand
edits are safe. For a deleted false positive, also run --exclude <url ...> with
its source URLs so the article (and the incident) cannot come back.

Requires ANTHROPIC_API_KEY in the environment (a GitHub Actions secret in CI),
except in --discover-only mode which only tests the news queries.

Usage:
  python scripts/generate_dog_shooting_tracker.py                 # daily run (last 3 days)
  python scripts/generate_dog_shooting_tracker.py --days 30       # wider window
  python scripts/generate_dog_shooting_tracker.py --discover-only # list candidate URLs, no LLM
  python scripts/generate_dog_shooting_tracker.py --limit 25      # cap articles classified this run
  python scripts/generate_dog_shooting_tracker.py --dry-run       # classify but don't write files
  python scripts/generate_dog_shooting_tracker.py --rebuild-json  # rebuild dashboard JSON from the CSV only
  python scripts/generate_dog_shooting_tracker.py --exclude URL   # blocklist a false-positive article, then exit
  python scripts/generate_dog_shooting_tracker.py --official      # cross-check agency OIS pages only (add --dry-run to preview)
  python scripts/generate_dog_shooting_tracker.py --official-staging  # ingest hand-entered annual-report rows
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

import dog_tracker_official as official

# --------------------------------------------------------------------------- #
# 0. Configuration
# --------------------------------------------------------------------------- #

# NOT under data/ -- that is Hugo's reserved data directory, and Hugo tries to
# parse every file in it as site data. A CSV there fails the build outright:
# "unexpected data type [][]string in file dog-shootings.csv".
INCIDENTS_CSV = "datasets/dog-shootings.csv"
SEEN_URLS_FILE = "datasets/dog-shootings-seen-urls.json"
EXCLUDED_FILE = "datasets/dog-shootings-excluded.json"  # URLs a human has judged NOT a qualifying incident
OFFICIAL_STAGING_CSV = "datasets/dog-shootings-official-staging.csv"  # hand-entered annual-report rows
DASHBOARD_JSON = "static/data/dog-shooting-tracker.json"
PUBLISHED_CSV = "static/data/dog-shootings.csv"

MODEL = "claude-haiku-4-5"
# Bump when the classification prompt / schema changes materially, so rows can
# be traced to the logic that produced them.
PROMPT_VERSION = "2026-09-24"

DEFAULT_DAYS_BACK = 3
DEFAULT_ARTICLE_LIMIT = 60  # max NEW articles classified in one run (cost guard)
MAX_DEDUPE_CANDIDATES = 20   # cap on same-state rows sent to the dedupe model
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
    "discovery",              # media | official | both -- where the incident was found
    "official_ref",           # agency case id, e.g. "LAPD NRF035-26" / "PPD 26-03"; "" if none
    "official_url",           # the agency's own record for the incident; "" if none
    "confidence",             # high | medium | low (model's self-rating)
    "prompt_version",         # PROMPT_VERSION that produced/updated the row
    "reviewed",               # yes | no -- has a person checked this row against the sources?
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


def clean_incident_date(fields, published=""):
    """(incident_date, date_precision). A date is kept ONLY if it is a real
    YYYY-MM-DD, the model quoted its evidence in incident_date_source, AND (when
    a publication date is known and litigation is 'none') the year is within a
    year of publication.

    The classifier fabricates plausible dates when the article gives none, and
    even mis-resolves relative references badly (observed: "on Thursday" in an
    Aug 2026 story -> 2024-11-14). News tracks recent events, so a date well
    before the article's own publication -- with no litigation hook that would
    explain covering an old case -- is almost always that kind of error."""
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
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return "", "unknown"
    pub_year = None
    if len(published) >= 4 and published[:4].isdigit():
        pub_year = int(published[:4])
    litigating = coerce_enum(fields.get("litigation"), ENUM_FIELDS["litigation"][0], "unknown") not in ("none", "unknown")
    if pub_year is not None and not litigating and d.year < pub_year - 1:
        print(f"  ! incident_date {iso!r} dropped -- {d.year} predates publication {pub_year} with no litigation")
        return "", "unknown"
    if prec == "unknown":
        prec = "day"
    return iso, prec

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
# officer" dog (0 relevant), and "puppycide" (0 hits on Google News).
# Google News is the sole discovery source (GDELT was dropped 2026-09-21: it
# timed out or 429'd on nearly every request, from CI and from a local IP
# alike), so this list has to carry all of the breadth. The first block is
# the 2026-09-01 probe set (hit / on-topic counts from a 21-day window). The
# second block is unverified — added
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
    # -- unverified, added 2026-09-01 to widen breadth --
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
    '"opened fire on the dog"',  # a different verb entirely
    '"shoots dog while"',        # parallel to the working "shoots dog during"
    # -- added 2026-09-02, recall gaps found against a parallel OIAS tracker --
    # Three confirmed in-scope incidents in the Aug 2026 window were absent from
    # our candidates entirely (not rejected by the classifier -- never discovered):
    #   * Graham, WA   -- headlines read "deputies shoot/kill AGGRESSIVE dog";
    #                     the adjective breaks every quoted "<verb> dog" bigram above.
    #   * Waterloo, IA -- "officer KILLS dog", "shoots, kills attacking pit bull".
    #                     "kills" verbs were pruned earlier for returning outlet
    #                     general-feeds; re-added -- the classifier is the real gate.
    #   * Palm Beach, FL (Mar-a-Lago) -- discovered every run but only via an
    #                     unextractable headline; that path is fixed in HEADLINE_ONLY_NOTE.
    # Prune against yield after the next real run, like the block above.
    '"shoot aggressive dog"',
    '"shot aggressive dog"',
    '"shoots aggressive dog"',
    '"kill aggressive dog"',
    '"officer shoots pit bull"',
    '"officers shoot pit bull"',
    '"deputies shoot pit bull"',
    '"officer kills dog"',       # re-added (was dropped 2026-09-01 for feed noise)
    '"deputy kills dog"',
    '"deputies kill dog"',
    '"police kill dog"',
    '"shot and killed the dog"',
    '"shot and killed a dog"',
    '"shoots and kills dog"',
    '"shoots dog after"',        # parallel to "shoots dog during" / "...while"
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

# Browser-like UA — some publishers reject obvious bot agents.
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

    Google News has no working US-only filter and
    leaked ctvnews.ca, aptnnews.ca and dailystar.co.uk into a 21-day probe.
    The classifier already scopes to sworn *U.S.* officers and would reject
    these, so this is purely to avoid paying for the call. It is deliberately
    TLD-only -- non-US outlets on .com (ndtv.com, say) still reach the LLM,
    which is the right place to catch them.
    """
    host = _domain(url)
    return any(host == t or host.endswith("." + t) for t in NON_US_TLDS)


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


def discover(days_back, seen_urls, excluded=None):
    """Run every query, dedupe by URL, drop blocked domains, already-seen URLs,
    and human-excluded URLs. Returns the fresh candidates, newest first."""
    excluded = excluded or set()
    candidates = {}

    print(f"Google News ({len(GOOGLE_NEWS_PHRASINGS)} feeds)")
    for phrasing in GOOGLE_NEWS_PHRASINGS:
        articles = fetch_google_news(phrasing, days_back)
        print(f"  {len(articles):4d}  {phrasing}")
        for a in articles:
            candidates.setdefault(a["url"], a)
        time.sleep(GNEWS_PAUSE_SEC)

    # Zero raw entries across every feed is a fetch failure, not a quiet news
    # week: the count is taken before the already-seen filter, so even a slow
    # window still returns the last few days' coverage. feedparser swallows
    # network errors, so without this a Google News outage (now the only source)
    # looks like "no new incidents". Exit non-zero so the Actions run goes red
    # and emails, instead of a log line nobody reads.
    if not candidates:
        print(
            f"!! all {len(GOOGLE_NEWS_PHRASINGS)} Google News feeds returned 0 entries; "
            "treating as a fetch failure, not an empty news window.",
            file=sys.stderr,
        )
        sys.exit(1)

    # news.google.com is itself blocklisted, so the blocklist check has to wait
    # until after resolve_url() — otherwise every Google News hit is dropped here.
    fresh = [
        a
        for url, a in candidates.items()
        if url not in seen_urls
        and url not in excluded
        and (a.get("needs_decode") or (not _blocked(url) and not _non_us(url)))
        and len(a["title"]) >= 15
    ]
    fresh.sort(key=lambda a: a["date"], reverse=True)
    print(f"\n{len(candidates)} unique URLs -> {len(fresh)} new, unblocked candidates")
    return fresh


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

CLASSIFY_SYSTEM = f"""You extract structured data about ONE kind of event: a currently-serving sworn U.S. law-enforcement officer discharging a firearm AT or TOWARD a dog WHILE ACTING IN A LAW-ENFORCEMENT CAPACITY.

INCLUDE an article only if it reports a specific, concrete incident (a real event on a real date/place) in which:
  - a SWORN, currently-employed law-enforcement officer (municipal police, county sheriff/deputy, state police/trooper, federal agent, tribal police, campus police), acting as police — on a call, a stop, an arrest, a patrol, a warrant, or otherwise handling a police matter (an OFF-duty officer who intervenes as police counts), AND
  - fired a gun AT or TOWARD a dog (any outcome: killed, wounded, or missed).

EXCLUDE (set qualifies=false) if ANY of these apply:
  - the shooter was an animal-control officer, a civilian, a security guard, or a game warden acting in a wildlife capacity
  - the shooter was a RETIRED or FORMER officer, or an off-duty officer acting as a private citizen in a personal dispute (e.g. defending their own pet, a neighbor conflict) rather than as police
  - no firearm was involved (baton, Taser, catch-pole, vehicle, or the dog was only impounded/euthanized by a vet)
  - the animal was not a dog (cat, livestock, or wildlife such as a deer, bear, or coyote — including an officer euthanizing an animal injured by a car)
  - the dog shot was the officer's own K-9 / police dog / a service dog
  - it is about policy, training, legislation, procurement, a lawsuit ruling with no described incident, an opinion/column, or aggregate statistics with no specific incident
  - it is a first-report of an unconfirmed claim with no identifiable agency or location
  - it is a multi-topic news roundup that mentions the shooting only in passing, with no dedicated account of it

The test is whether the shooter was a sworn officer acting as police WHEN THEY FIRED. What happens afterward does not change that: an officer being CHARGED with a crime, disciplined, fired, sued, or cleared AFTER the shooting still qualifies — those are exactly the cases to record, the same way an officer-involved shooting of a person is tracked whether or not charges follow. Put any such charge, discipline, resignation, or DA decision in dept_response.

Report fields ONLY from what the article states. If the article does not state a field, use "unknown" for the enum fields and "" for the free-text fields (city, county, incident_date, officer_named, dog_breed_reported). Never infer from general knowledge or from the outlet's location.

officer_named: give an individual officer's name ONLY if the article attributes it to an official record (a charging document, a lawsuit, a department statement/press release, or a disciplinary record). Otherwise leave it "".

incident_date + incident_date_source: FIRST, copy into incident_date_source the exact words from the article that establish when the shooting happened — e.g. "Wednesday afternoon", "on Aug. 20", "earlier this month", "last summer". If the article contains no such words, incident_date_source MUST be "" AND incident_date MUST be "". Then fill incident_date (ISO YYYY-MM-DD, the shooting date, NOT the publication date):
  - A relative reference ("Thursday", "yesterday", "earlier this week") is resolved ONLY against the "Article published:" date given above — the most recent such day on or before publication — with date_precision=day. If no publication date was given, leave incident_date empty.
  - An explicit "Month Day" with no year takes the year from the publication date; date_precision=day.
  - Only the month named → first of that month, date_precision=month.
  - Only a season or year → estimate, date_precision=approximate.
NEVER invent a day, month, or year, and NEVER output a year that isn't either stated in the article or taken from the publication date — a fabricated date is worse than a blank one because it silently splits one incident into several rows. Never output the literal word "unknown"; use "".

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
    "script-only page). Classify from the HEADLINE and URL alone.\n"
    "Set qualifies=true when the headline states -- ACTIVELY or PASSIVELY -- "
    "that an ON-DUTY officer or a named law-enforcement agency fired a gun at a "
    "dog. All of these count: \"Deputy shoots dog during arrest\", \"Police kill "
    "dog after attack\", \"Dog shot by officers near Mar-a-Lago\", \"...fleeing "
    "with her dog, who was shot by police\", \"<named agency> shoots dog\". The "
    "shooter must be law enforcement (police, deputy, sheriff, trooper, officer, "
    "agent, or a named LE agency) and the weapon a firearm (\"shot\", \"opened "
    "fire\", \"gunfire\").\n"
    "The law-enforcement actor must be NAMED IN THE HEADLINE ITSELF. Do NOT "
    "infer police involvement from the URL, the town, a local-news byline, or "
    "the fact that a dog shooting is newsworthy. \"Community reacts to shooting "
    "death of a dog\", \"Memorial held for dog\", \"Dog found shot\" name no "
    "shooter -> qualifies=false.\n"
    "Set qualifies=false if the headline: names or implies a NON-police shooter "
    "(\"man\", \"gunman\", \"resident\", \"neighbor\", \"owner\", \"homeowner\", "
    "a security guard, an animal-control officer); says the officer was "
    "OFF-DUTY, RETIRED, or FORMER, or was acting in a personal dispute; is "
    "about an animal that is not a dog (a coyote, deer, bear, livestock -- even "
    "if a dog is also mentioned); indicates no firearm (Tasered, caught, hit by "
    "a car); or is silent on who shot. A headline saying the officer was "
    "CHARGED, disciplined, resigned, or is under investigation FOR THE SHOOTING "
    "does NOT disqualify it -- if an on-duty officer acting as police fired the "
    "gun, still qualify. If in doubt about a detail OTHER than the shooter, the "
    "weapon, the animal, or whether the shooter was acting as police, still "
    "qualify it.\n"
    "When it qualifies, set confidence=low and leave every field you cannot "
    "determine as unknown/empty, including incident_date. EXCEPTION: if the "
    "headline or URL names a city, neighbourhood, or region, set `state` to that "
    "place's USPS state code (this is geography, not a claim about the incident) "
    "-- e.g. \"Charlotte\" -> NC, \"Sunland Park\" / \"Green Meadows\" (Los "
    "Angeles) -> CA, \"Mar-a-Lago\" / \"Palm Beach\" -> FL, \"Graham\" "
    "(Pierce County) -> WA."
)


def classify_article(client, title, text, url, published=""):
    """Return the tool input dict, or None on a hard API error. text=None means
    body extraction failed -> classify from the headline under strict rules.
    `published` is the article's publication date (ISO) -- the anchor for
    resolving relative references like "Thursday" or "earlier this week"."""
    pub = f"Article published: {published[:10]}\n" if published else ""
    if text:
        user = f"{pub}Article URL: {url}\nHeadline: {title}\n\nArticle text:\n{text}"
    else:
        user = f"{pub}Article URL: {url}\nHeadline: {title}{HEADLINE_ONLY_NOTE}"
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

    Blocking is by state (falling back to city when the row has no state -- a
    headline-only row often does not) -- no date window. Model-supplied dates
    are not trustworthy enough to gate on: a fabricated date on one copy of an
    incident would put it outside the window from the real-dated copy and split
    one event into several rows (observed with the Sunland Park incident). The
    LLM adjudicates every blocked pair; MAX_DEDUPE_CANDIDATES caps cost."""
    st = (new_row.get("state") or "").strip()
    city = (new_row.get("city") or "").strip().lower()
    if st:
        candidates = [r for r in existing_rows if r.get("state") == st]
    elif city:
        candidates = [r for r in existing_rows if (r.get("city") or "").strip().lower() == city]
    else:
        return None
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
        "already recorded. The incident_date in these records is frequently WRONG, so never "
        "treat a date GAP as evidence of separate events. But the reverse does not hold: an "
        "IDENTICAL incident_date plus the same agency is strong evidence of the SAME event -- "
        "two separate dog shootings by one department on one day are rare. Outlets also label "
        "the same block with different neighborhood names (e.g. 'Humboldt Park' vs 'East "
        "Garfield Park' for one Chicago address), so a different neighborhood name within one "
        "city is NOT evidence of a different event. "
        "Decide from the SUMMARY: is it the same agency (or one unstated), in the same place or "
        "a nearby area of the same metro, describing the same specific event -- the same "
        "officer/deputy action, the same dog, the same sequence of events (e.g. 'Tased the dog "
        "first, then fired'), the same named officials or quotes? A shared specific detail -- a "
        "named commander quoted, an unusual fact, a specific named location -- means SAME "
        "incident even when dates, outcomes, breeds, or city labels differ between outlets. "
        "It is a DIFFERENT event only if it is a different metro area, or clearly different "
        "circumstances (different call type, different dog, different officers)."
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
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in CSV_FIELDS:
            r.setdefault(k, "")
        # `reviewed` was added later; a blank (or anything not "yes") means
        # "not yet reviewed". Normalise case so the on-disk value is stable.
        r["reviewed"] = "yes" if (r.get("reviewed") or "").strip().lower() == "yes" else "no"
        # `discovery` was added 2026-09-24; every earlier row came from news.
        if r["discovery"] not in ("media", "official", "both"):
            r["discovery"] = "media"
    return rows


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


def load_excluded():
    """URLs a person has judged NOT a qualifying incident (a deleted false
    positive, a wrong-species story, a civilian shooter, ...). Treated like
    seen_urls in discovery, so the article -- and, via dedupe, the incident --
    never comes back. Accepts a bare JSON array of URL strings, or an array of
    {"url": ..., "note": ...} objects."""
    if not os.path.exists(EXCLUDED_FILE):
        return set()
    try:
        with open(EXCLUDED_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return set()
    out = set()
    for item in raw:
        if isinstance(item, str):
            out.add(item)
        elif isinstance(item, dict) and item.get("url"):
            out.add(item["url"])
    return out


def add_excluded(urls):
    """Append URLs to the exclusion file, preserving any existing notes."""
    existing = []
    if os.path.exists(EXCLUDED_FILE):
        try:
            with open(EXCLUDED_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    have = {i if isinstance(i, str) else i.get("url") for i in existing}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    added = 0
    for u in urls:
        if u and u not in have:
            existing.append({"url": u, "note": f"excluded by hand {today}"})
            have.add(u)
            added += 1
    os.makedirs(os.path.dirname(EXCLUDED_FILE), exist_ok=True)
    with open(EXCLUDED_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    return added


def next_id(rows):
    return max((int(r["id"]) for r in rows), default=0) + 1


def _freetext(value):
    """Free-text field, with the model's placeholder strings scrubbed to "".
    The model sometimes writes 'unknown', 'n/a', '<UNKNOWN>' etc. into city /
    county / agency_name where the schema wants a blank."""
    v = (value or "").strip()
    if v.lower().strip("<>[]() ") in ("", "unknown", "n/a", "na", "none", "not stated", "not specified", "not available"):
        return ""
    return v


def make_row(fields, article, row_id):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    incident_date, date_precision = clean_incident_date(fields, article.get("date", ""))
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
            "city": _freetext(fields.get("city")),
            "county": _freetext(fields.get("county")),
            "state": (fields.get("state") or "").strip().upper(),
            "agency_name": _freetext(fields.get("agency_name")),
            "agency_type": enums["agency_type"],
            "on_duty": enums["on_duty"],
            "officer_named": _freetext(fields.get("officer_named")),
            "dogs_fired_at": str(fields["dogs_fired_at"]) if str(fields.get("dogs_fired_at", "")).strip().isdigit() else "",
            "dog_outcome": enums["dog_outcome"],
            "dog_breed_reported": _freetext(fields.get("dog_breed_reported")),
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
            "discovery": "media",
            "official_ref": "",
            "official_url": "",
            "confidence": enums["confidence"],
            "prompt_version": PROMPT_VERSION,
            "reviewed": "no",  # a person sets this to "yes" after checking the row
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

    # Agency cross-check: for each department whose own records we ingest, how
    # many of its recorded dog shootings did news discovery also find? Grouped
    # by the official_ref prefix ("LAPD", "PPD", ...).
    coverage = {}
    for r in rows:
        ref = (r.get("official_ref") or "").strip()
        if not ref:
            continue
        c = coverage.setdefault(ref.split()[0], {"agency_name": r.get("agency_name", ""),
                                                 "official": 0, "media_covered": 0})
        c["official"] += 1
        if r.get("discovery") == "both":
            c["media_covered"] += 1

    incident_dates = [r["incident_date"][:10] for r in dated]
    total_sources = 0
    for r in rows:
        total_sources += 1 + len([u for u in (r.get("additional_sources") or "").split() if u])

    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_incidents": len(rows),
        "reviewed_count": sum(1 for r in rows if (r.get("reviewed") or "").strip().lower() == "yes"),
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
        "discovery_counts": {
            k: sum(1 for r in rows if r.get("discovery") == k) for k in ("media", "official", "both")
        },
        "official_coverage": [
            {"ref_prefix": k, **v} for k, v in sorted(coverage.items(), key=lambda kv: -kv[1]["official"])
        ],
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
                "discovery": r.get("discovery", "media"),
                "official_url": r.get("official_url", ""),
                "confidence": r.get("confidence", ""),
                "reviewed": (r.get("reviewed") or "no").strip().lower() == "yes",
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
        if r.get("discovery") not in ("media", "official", "both"):
            problems.append(f"id {rid}: bad discovery {r.get('discovery')!r}")
    return problems


# --------------------------------------------------------------------------- #
# 8. Agency records (see scripts/dog_tracker_official.py)
# --------------------------------------------------------------------------- #

def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def _agency_matches(row_agency, source):
    """Case-insensitive match of a row's agency against the source's name or
    its abbreviation (hand-entered rows say "LAPD" as often as the full name)."""
    a = _norm(row_agency)
    full = _norm(source["agency_name"])
    abbr = "".join(w[0] for w in full.split() if w not in ("of", "the"))
    return a == full or a == abbr or (a and (a in full or full in a))


def _date_gap(a, b):
    try:
        return abs((datetime.strptime(a[:10], "%Y-%m-%d") - datetime.strptime(b[:10], "%Y-%m-%d")).days)
    except ValueError:
        return None


def match_official(client, row, source, incidents):
    """Id of the existing incident this agency record describes, or None.

    Agency records carry an exact date, so try a deterministic match first:
    same state + same agency + incident_date within a day. Only if that finds
    nothing (or more than one) does the LLM adjudicate -- it catches rows whose
    date is missing or off, or whose agency was written differently."""
    def close(r):
        gap = _date_gap(r.get("incident_date", ""), row["incident_date"]) if row["incident_date"] else None
        return gap is not None and gap <= 1

    near = [
        r for r in incidents
        if r.get("state") == source["state"]
        and _agency_matches(r.get("agency_name"), source)
        and close(r)
    ]
    if len(near) == 1:
        return int(near[0]["id"])
    return find_duplicate(client, row, near or incidents)


def ingest_official_records(client, source, records, incidents, seen_urls, excluded):
    """Classify each agency record and fold it into `incidents` in place.
    Returns (added, matched, rejected, errors)."""
    have_refs = {r.get("official_ref") for r in incidents if r.get("official_ref")}
    added = matched = rejected = errors = 0
    for rec in records:
        ref, url = rec["official_ref"], rec["url"]
        if ref in have_refs:
            continue  # already folded in on an earlier run
        if not official.in_scope(rec):
            continue
        if url in excluded:
            print(f"  skip (excluded by review)  {ref}")
            continue
        # Keyed by case ref, not URL: an agency press release may already be in
        # seen_urls from news discovery, which says nothing about this record.
        seen_key = f"official:{ref}"
        if seen_key in seen_urls:
            continue  # classified before and rejected
        seen_urls.add(seen_key)
        text = rec.get("text") or extract_article_text(url)
        if not text:
            # No narrative (release page unreachable): give the classifier the
            # bare table facts; it will set most fields to unknown.
            text = (f"{source['agency_name']} lists this incident in its officer-involved "
                    f"shooting records as an officer-involved shooting of a dog. "
                    f"Date: {rec['incident_date']}. Location: {rec['location']}. Case: {ref}.")
        title = f"{source['agency_name']} officer-involved shooting record {ref}: {rec['location']}"
        fields = classify_article(client, title, text, url, rec.get("incident_date", ""))
        if fields is None:
            seen_urls.discard(seen_key)  # API error -- retry next run
            errors += 1
            continue
        if not fields.get("qualifies"):
            rejected += 1
            print(f"  no   {ref} -- {fields.get('reason', '')[:80]}")
            continue

        row = make_row(fields, {"url": url, "source": source["agency_name"],
                                "date": rec.get("incident_date", "")}, next_id(incidents))
        # The agency record is authoritative for who, where and when.
        row["agency_name"] = source["agency_name"]
        row["state"] = source["state"]
        row["city"] = row["city"] or source["city"]
        if rec.get("incident_date"):
            row["incident_date"], row["date_precision"] = rec["incident_date"], "day"
        row.update({"discovery": "official", "official_ref": ref, "official_url": url})

        dup_id = match_official(client, row, source, incidents)
        if dup_id is not None:
            r = next(r for r in incidents if int(r["id"]) == dup_id)
            # Never overwrite a reviewed row's fields -- only record provenance.
            if r.get("discovery") == "media":
                r["discovery"] = "both"
            if not r.get("official_ref"):
                r["official_ref"], r["official_url"] = ref, url
            matched += 1
            print(f"  match {ref} -> incident {dup_id}")
        else:
            incidents.append(row)
            added += 1
            print(f"  ADD  incident {row['id']}: {ref} {row['incident_date']} {row['city']} -- {row['dog_outcome']}")
        have_refs.add(ref)
    return added, matched, rejected, errors


def fetch_official_page(url):
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
        resp.raise_for_status()
        return resp.text
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not fetch {url}: {e}")
        return None


def load_staging():
    """Hand-entered annual-report rows, grouped into (source, records) pairs."""
    if not os.path.exists(OFFICIAL_STAGING_CSV):
        return []
    with open(OFFICIAL_STAGING_CSV, "r", encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("official_ref") or "").strip()]
    groups = {}
    for r in rows:
        key = (r["agency_name"].strip(), r["state"].strip().upper())
        src = groups.setdefault(key, ({"key": "staging", "agency_name": key[0], "state": key[1],
                                       "city": r.get("city", "").strip()}, []))
        src[1].append({
            "official_ref": r["official_ref"].strip(),
            "incident_date": r.get("incident_date", "").strip(),
            "location": r.get("location", "").strip(),
            "url": r.get("url", "").strip() or f"staging:{r['official_ref'].strip()}",
            "text": r.get("text", "").strip() or None,
        })
    return list(groups.values())


def run_official(staging=False):
    """Cross-check agency records against the dataset. Returns the updated
    incidents + seen URLs, or None when nothing could be fetched. A fetch or
    parse failure is a warning, never a failed run -- these pages are a
    secondary source and change layout without notice."""
    incidents = load_incidents()
    seen_urls = load_seen_urls()
    excluded = load_excluded()
    if staging:
        batches = load_staging()
        print(f"Staging file: {sum(len(recs) for _, recs in batches)} record(s)")
    else:
        batches = []
        for src in official.OFFICIAL_SOURCES:
            page = fetch_official_page(src["url"])
            if page is None:
                continue
            recs = src["parser"](page)
            if not recs and len(page) > 20000:
                print(f"  !! {src['key']}: 0 dog records parsed from a {len(page)}-byte page -- "
                      "layout changed? Check the parser in scripts/dog_tracker_official.py.")
            print(f"{src['key']}: {len(recs)} dog record(s), "
                  f"{sum(official.in_scope(r) for r in recs)} in scope")
            batches.append((src, recs))
    if not any(recs for _, recs in batches):
        return None

    client = get_client()
    totals = [0, 0, 0, 0]
    for src, recs in batches:
        for i, n in enumerate(ingest_official_records(client, src, recs, incidents, seen_urls, excluded)):
            totals[i] += n
    added, matched, rejected, errors = totals
    print(f"\nofficial: added={added} matched={matched} rejected={rejected} errors={errors}")
    # Same breaker as the news path: a bad key or an API outage must turn the
    # run red, not pass as "nothing new".
    attempted = added + matched + rejected + errors
    if attempted and errors / attempted > 0.5:
        print("ERROR: >50% of agency records errored -- not writing.", file=sys.stderr)
        sys.exit(1)
    return incidents, seen_urls


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
    ap.add_argument("--exclude", nargs="+", metavar="URL",
                    help="add URL(s) to the exclusion list (a deleted false positive) and exit")
    ap.add_argument("--official", action="store_true",
                    help="cross-check agency OIS pages (no news discovery); honours --dry-run")
    ap.add_argument("--official-staging", action="store_true",
                    help=f"ingest hand-entered rows from {OFFICIAL_STAGING_CSV}; honours --dry-run")
    args = ap.parse_args()

    if args.official or args.official_staging:
        result = run_official(staging=args.official_staging)
        if result is None:
            print("No agency records to process.")
            return
        incidents, seen_urls = result
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
        write_dashboard_json(incidents)
        publish_csv_copy()
        print(f"Wrote {INCIDENTS_CSV} ({len(incidents)} incidents).")
        return

    if args.exclude:
        n = add_excluded(args.exclude)
        print(f"Added {n} URL(s) to {EXCLUDED_FILE} ({len(load_excluded())} total).")
        return

    if args.rebuild_json:
        rows = load_incidents()
        data = write_dashboard_json(rows)
        publish_csv_copy()
        print(f"Rebuilt {DASHBOARD_JSON} from {len(rows)} incidents "
              f"({data['reviewed_count']} human-reviewed).")
        return

    incidents = load_incidents()
    seen_urls = load_seen_urls()
    excluded = load_excluded()
    print(f"Loaded {len(incidents)} existing incidents, {len(seen_urls)} seen URLs, "
          f"{len(excluded)} excluded URLs.\n")

    candidates = discover(args.days, seen_urls, excluded)

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
        if a["url"] in excluded:
            print(f"  skip (excluded by review)  {_domain(a['url'])}")
            continue
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
        fields = classify_article(client, a["title"], text, a["url"], a.get("date", ""))
        if fields is None:
            errors += 1
            continue
        if not fields.get("qualifies"):
            print(f"  no  — {fields.get('reason', '')[:80]}")
            continue
        st = (fields.get("state") or "").strip().upper()
        if not st:
            print(f"  skip (no state -- unplaceable)  {a['title'][:60]}")
            continue
        # The classifier is scoped to sworn U.S. officers, but the headline-only
        # path sets `state` from geography without re-checking the country, so a
        # Canadian story lands as 'MB'/'ON'. Drop it here rather than let one bad
        # row fail validate_rows() and block the whole batch (cron included).
        if st not in VALID_STATES:
            print(f"  skip (non-US state {st!r})  {a['title'][:60]}")
            continue

        row = make_row(fields, a, next_id(incidents))
        # The tracker counts 2026 onward. Lawsuit coverage of an older shooting
        # passes clean_incident_date() (litigation explains the old date) but
        # is still out of scope -- observed: a 2024 Walton County FL case.
        if row["incident_date"] and row["incident_date"] < official.TRACKING_START:
            print(f"  skip (incident {row['incident_date']} predates {official.TRACKING_START})  {a['title'][:60]}")
            continue
        dup_id = find_duplicate(client, row, incidents)
        if dup_id is not None:
            for r in incidents:
                if int(r["id"]) == dup_id:
                    extra = [u for u in (r.get("additional_sources") or "").split() if u]
                    if a["url"] not in extra and a["url"] != r.get("source_url"):
                        extra.append(a["url"])
                        r["additional_sources"] = " ".join(extra)
                    if r.get("discovery") == "official":
                        r["discovery"] = "both"  # news has now covered an agency-only incident
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


if __name__ == "__main__":
    main()
