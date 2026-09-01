#!/usr/bin/env python3
"""
Police Shootings of Dogs — Incident Tracker Generator

There is no national, systematic tracking of police shootings of dogs. This
script builds one from news coverage, using the same approach as Charles Fain
Lehman's flock-crime-tracker (flockstopscrime.com):

  1. discover  - GDELT DOC 2.0 API + Google News RSS, a fixed query list
  2. extract   - pull article body text with trafilatura
  3. classify  - one Claude (Haiku) call per article: does it describe a
                 sworn officer firing a gun at a dog? plus structured fields
  4. dedupe    - one Claude call to fold a new article into an existing
                 incident (blocked by state + incident date) rather than
                 creating a duplicate row
  5. store     - append qualifying incidents to data/dog-shootings.csv
                 (the durable dataset; git history is the audit log)
  6. emit      - aggregates JSON for the dashboard page + a published CSV copy

Outputs:
  - data/dog-shootings.csv               -- incident dataset (source of truth)
  - data/dog-shootings-seen-urls.json    -- URL-level dedup cache
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

INCIDENTS_CSV = "data/dog-shootings.csv"
SEEN_URLS_FILE = "data/dog-shootings-seen-urls.json"
DASHBOARD_JSON = "static/data/dog-shooting-tracker.json"
PUBLISHED_CSV = "static/data/dog-shootings.csv"

MODEL = "claude-haiku-4-5"
# Bump when the classification prompt / schema changes materially, so rows can
# be traced to the logic that produced them.
PROMPT_VERSION = "2026-09-01"

DEFAULT_DAYS_BACK = 3
DEFAULT_ARTICLE_LIMIT = 60  # max NEW articles classified in one run (cost guard)
DEDUPE_DATE_WINDOW_DAYS = 21
MAX_DEDUPE_CANDIDATES = 20
GDELT_PAUSE_SEC = 6
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

# Discovery — GDELT DOC 2.0 API queries (ANDs terms; OR inside parens; quotes
# for phrases). The LLM is the real relevance gate, so these are moderately
# broad. `sourcecountry:US` is appended per query.
GDELT_QUERIES = [
    '"shot the dog" (police OR deputy OR officer OR trooper)',
    '"shot a dog" (police OR deputy OR officer OR trooper)',
    '"shot my dog" (police OR deputy OR officer)',
    '"shot the family dog"',
    '"police shot" (dog OR puppy OR "pit bull")',
    '"deputy shot" (dog OR puppy OR "pit bull")',
    '"officer shot" (dog OR puppy OR "pit bull")',
    '"shot and killed" (dog OR puppy) (police OR deputy OR officer)',
    '"opened fire" dog (police OR deputy OR officer)',
    'puppycide',
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
GOOGLE_NEWS_PHRASINGS = [
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
    """One GDELT DOC 2.0 query -> list of {title, url, source, date}."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    params = {
        "query": f"{query} sourcecountry:US",
        "mode": "artlist",
        "maxrecords": 250,
        "format": "json",
        "timespan": f"{days_back}d",
    }
    for attempt in range(3):
        try:
            resp = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30
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
    return []


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
    URLs. Returns a list of candidate article dicts."""
    candidates = {}

    print(f"GDELT ({len(GDELT_QUERIES)} queries, {days_back}d window)")
    for query in GDELT_QUERIES:
        articles = fetch_gdelt(query, days_back)
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

Report fields ONLY from what the article states. If the article does not state a field, use "unknown" (or "" for officer_named / dog_breed_reported). Never infer from general knowledge or from the outlet's location.

officer_named: give an individual officer's name ONLY if the article attributes it to an official record (a charging document, a lawsuit, a department statement/press release, or a disciplinary record). Otherwise leave it "".

incident_date: the date the shooting happened (not the publication date), ISO YYYY-MM-DD. If only a month is known use the first of the month and set date_precision=month; if only approximate, estimate and set date_precision=approximate.

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
            "incident_date": {"type": "string", "description": "YYYY-MM-DD or empty"},
            "date_precision": {"type": "string", "enum": ["day", "month", "approximate", "unknown"]},
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
            "qualifies", "reason", "incident_date", "date_precision", "city", "county",
            "state", "agency_name", "agency_type", "on_duty", "officer_named",
            "dogs_fired_at", "dog_outcome", "dog_breed_reported", "dog_restrained",
            "circumstance", "warrant_type", "human_injured_by_fire", "dept_response",
            "litigation", "summary", "confidence",
        ],
    },
}


def classify_article(client, title, text, url):
    """Return the tool input dict, or None on a hard API error."""
    user = f"Article URL: {url}\nHeadline: {title}\n\nArticle text:\n{text}"
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


def _within_window(d1, d2, days):
    try:
        a = datetime.strptime(d1[:10], "%Y-%m-%d")
        b = datetime.strptime(d2[:10], "%Y-%m-%d")
        return abs((a - b).days) <= days
    except Exception:
        return False


def find_duplicate(client, new_row, existing_rows):
    """Block by state + incident-date window, then ask the model. Returns the
    matching id (int) or None."""
    if not new_row.get("state") or not new_row.get("incident_date"):
        return None
    candidates = [
        r
        for r in existing_rows
        if r.get("state") == new_row["state"]
        and _within_window(r.get("incident_date", ""), new_row["incident_date"], DEDUPE_DATE_WINDOW_DAYS)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: r.get("incident_date", ""), reverse=True)
    candidates = candidates[:MAX_DEDUPE_CANDIDATES]

    def brief(r):
        return {
            "id": int(r["id"]),
            "incident_date": r.get("incident_date", ""),
            "city": r.get("city", ""),
            "agency_name": r.get("agency_name", ""),
            "dog_outcome": r.get("dog_outcome", ""),
            "summary": r.get("summary", ""),
        }

    payload = {
        "new_incident": {
            "incident_date": new_row["incident_date"],
            "city": new_row.get("city", ""),
            "agency_name": new_row.get("agency_name", ""),
            "dog_outcome": new_row.get("dog_outcome", ""),
            "summary": new_row.get("summary", ""),
        },
        "existing_incidents": [brief(r) for r in candidates],
    }
    system = (
        "You decide whether a new dog-shooting incident is the SAME real-world event as one "
        "already recorded. Same event = same shooting (same agency, same date within a few days, "
        "same location, same dog). Merely similar incidents in the same area are NOT duplicates. "
        "If unsure, it is NOT a duplicate."
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
    row = {k: "" for k in CSV_FIELDS}
    row.update(
        {
            "id": row_id,
            "date_added": today,
            "incident_date": (fields.get("incident_date") or "").strip(),
            "date_precision": fields.get("date_precision", "unknown"),
            "city": fields.get("city", "").strip(),
            "county": fields.get("county", "").strip(),
            "state": (fields.get("state") or "").strip().upper(),
            "agency_name": fields.get("agency_name", "").strip(),
            "agency_type": fields.get("agency_type", "unknown"),
            "on_duty": fields.get("on_duty", "unknown"),
            "officer_named": fields.get("officer_named", "").strip(),
            "dogs_fired_at": fields.get("dogs_fired_at", "") or "",
            "dog_outcome": fields.get("dog_outcome", "unknown"),
            "dog_breed_reported": fields.get("dog_breed_reported", "").strip(),
            "dog_restrained": fields.get("dog_restrained", "unknown"),
            "circumstance": fields.get("circumstance", "unknown"),
            "warrant_type": fields.get("warrant_type", "unknown"),
            "human_injured_by_fire": fields.get("human_injured_by_fire", "unknown"),
            "dept_response": fields.get("dept_response", "").strip(),
            "litigation": fields.get("litigation", "unknown"),
            "summary": fields.get("summary", "").strip(),
            "source_name": article.get("source", "") or _domain(article.get("url", "")),
            "source_url": article.get("url", ""),
            "additional_sources": "",
            "confidence": fields.get("confidence", "low"),
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

    candidates = discover(args.days, seen_urls)

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
            print(f"  skip (no text)  {a['url']}")
            continue
        processed += 1
        fields = classify_article(client, a["title"], text, a["url"])
        if fields is None:
            errors += 1
            continue
        if not fields.get("qualifies"):
            print(f"  no  — {fields.get('reason', '')[:80]}")
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


if __name__ == "__main__":
    main()
