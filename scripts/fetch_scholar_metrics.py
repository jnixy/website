#!/usr/bin/env python3
"""
Fetch Google Scholar metrics for Justin Nix
Saves h-index, i10-index, and total citations to a JSON file
"""

import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from scholarly import scholarly
except ImportError:
    print("Error: scholarly package not installed")
    print("Install with: pip install scholarly")
    exit(1)

SCHOLAR_ID = "_Jr8r8UAAAAJ"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_PATH = SCRIPT_DIR.parent / "data" / "scholar_metrics.json"


def main():
    print(f"Fetching Google Scholar data for ID: {SCHOLAR_ID}")

    try:
        # Fetch author data
        author = scholarly.search_author_id(SCHOLAR_ID)
        author = scholarly.fill(author, sections=['basics', 'indices'])

        # Extract metrics
        metrics = {
            "name": author.get("name", "Justin Nix"),
            "affiliation": author.get("affiliation", "University of Nebraska Omaha"),
            "h_index": author.get("hindex", None),
            "i10_index": author.get("i10index", None),
            "citations": author.get("citedby", None),
            "updated": datetime.now(timezone.utc).isoformat(),
            "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}"
        }

        # Ensure output directory exists
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

        print(f"Saved to {OUTPUT_PATH}")
        print(f"Citations: {metrics['citations']}")
        print(f"h-index: {metrics['h_index']}")
        print(f"i10-index: {metrics['i10_index']}")

    except Exception as e:
        print(f"Error fetching data: {e}")
        # Write fallback data so the site doesn't break
        fallback = {
            "name": "Justin Nix",
            "affiliation": "University of Nebraska Omaha",
            "h_index": None,
            "i10_index": None,
            "citations": None,
            "updated": datetime.now(timezone.utc).isoformat(),
            "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}",
            "error": str(e)
        }

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(fallback, f, indent=2)

        print(f"Wrote fallback data to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
