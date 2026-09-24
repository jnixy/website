"""
Agency-record sources for the dog-shooting tracker.

Some departments publish their own incident-level lists of officer-involved
shootings, and a few include shootings at dogs. Media discovery misses many of
these (on 2026-09-24: LAPD 4 of 4 dog shootings were media-covered, Philadelphia
PD 0 of 4), so they are cross-checked here.

This module only FETCHES and PARSES. It makes no LLM calls and does not touch
the CSV; generate_dog_shooting_tracker.py classifies each record with the same
classifier as a news article and matches it against existing incidents.

Each parser returns a list of records:
    {
      "official_ref": "LAPD NRF035-26",   # stable key -- never re-added once in the CSV
      "incident_date": "2026-08-27",      # from the agency record, "" if unparseable
      "location": "11000 block of Towne Avenue",
      "url": "https://...",               # the agency's own page for this incident
      "text": "..." or None,              # narrative; None -> caller fetches `url`
    }

Adding an agency = one parser + one OFFICIAL_SOURCES entry. Parsers are
deliberately strict: if a page layout changes, they return [] and the caller
prints a loud warning rather than guessing.

Annual PDF reports (e.g. Milwaukee FPC's use-of-force report) are not scraped;
see datasets/dog-shootings-official-staging.csv and the README.
"""

import html as _html
import re
from datetime import datetime

# Only incidents on/after this date are in scope (the tracker is 2026-only;
# the Philadelphia index also lists earlier years).
TRACKING_START = "2026-01-01"

DOG_WORDS = re.compile(r"\b(dogs?|pit ?bulls?|pitbulls?|german shep[a-z]+|canine|rottweilers?|huskies|husky)\b", re.I)


def _text(fragment):
    """Strip tags + collapse whitespace."""
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def _cells(row_html):
    return re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S | re.I)


def _mdy(s):
    """'8/27/26' or '8/27/2026' -> '2026-08-27'; '' if unparseable."""
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def _narrative_date(text):
    """First 'Month D, YYYY' (optionally 'Month Dth YYYY') in a narrative."""
    m = re.search(r"\b([A-Z][a-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", text or "")
    if not m:
        return ""
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


# --------------------------------------------------------------------------- #
# Los Angeles Police Department
# --------------------------------------------------------------------------- #
# One table row per categorical use of force. Animal shootings have Type
# "O.I.A.S." (or an O.I.S. code) and the literal Name "Dog", linking to a
# newsroom release that carries the narrative. Columns:
#   # | Date | Type | Division | Location | Name | CI Number | Video

def parse_lapd(page_html):
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, flags=re.S | re.I):
        cells = _cells(row)
        if len(cells) < 7:
            continue
        name = _text(cells[5])
        typ = _text(cells[2])
        if name.lower() != "dog" and "O.I.A.S" not in typ:
            continue
        link = re.search(r'href="([^"]+)"', cells[5])
        ci = _text(cells[6])
        out.append({
            "official_ref": f"LAPD {ci}",
            "incident_date": _mdy(_text(cells[1])),
            "location": f"{_text(cells[4])} ({_text(cells[3])} Division)",
            "url": link.group(1) if link else "",
            "text": None,  # the newsroom release is fetched by the caller
        })
    return out


# --------------------------------------------------------------------------- #
# Philadelphia Police Department
# --------------------------------------------------------------------------- #
# /ois/ is one big table: case link | location | year | ... | narrative (last
# cell). The page says animal shootings are excluded, but on-duty dog
# shootings are in fact listed with full narratives. Wild/injured-animal
# euthanasia is not listed, and the classifier screens out off-duty cases.

def parse_philly(page_html):
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, flags=re.S | re.I):
        cells = _cells(row)
        if len(cells) < 5:
            continue
        link = re.search(r'href="([^"]*/ois/(\d\d-\d+)/?)"', cells[0])
        if not link:
            continue
        narrative = _text(cells[-1])
        if not DOG_WORDS.search(narrative):
            continue
        out.append({
            "official_ref": f"PPD {link.group(2)}",
            "incident_date": _narrative_date(narrative),
            "location": _text(cells[1]),
            "url": link.group(1),
            "text": narrative,
        })
    return out


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

OFFICIAL_SOURCES = [
    {
        "key": "lapd",
        "agency_name": "Los Angeles Police Department",
        "city": "Los Angeles",
        "state": "CA",
        # The slug is per year; update it each January.
        "url": "https://www.lapdonline.org/office-of-the-chief-of-police/professional-standards-bureau/critical-incident-videos/2026-o-i-s-shootings-and-critical-incidents/",
        "parser": parse_lapd,
    },
    {
        "key": "philly",
        "agency_name": "Philadelphia Police Department",
        "city": "Philadelphia",
        "state": "PA",
        "url": "https://www.phillypolice.com/ois/",
        "parser": parse_philly,
    },
]


def in_scope(record):
    """Keep dated records on/after TRACKING_START; keep undated ones for the
    classifier (it may find the date in the narrative)."""
    d = record.get("incident_date", "")
    return not d or d >= TRACKING_START
