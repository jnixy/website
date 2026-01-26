#!/usr/bin/env python3
"""
Fetch Google Scholar metrics for Justin Nix
Saves h-index, i10-index, and total citations to a JSON file
Uses proxy rotation to avoid Google Scholar blocking
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from scholarly import scholarly, ProxyGenerator
except ImportError:
    print("Error: scholarly package not installed")
    print("Install with: pip install scholarly")
    exit(1)

SCHOLAR_ID = "_Jr8r8UAAAAJ"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_PATH = SCRIPT_DIR.parent / "data" / "scholar_metrics.json"
MAX_RETRIES = 3


def setup_proxy():
    """Set up proxy rotation using FreeProxy."""
    try:
        pg = ProxyGenerator()
        # Use FreeProxy for free proxy rotation
        success = pg.FreeProxies()
        if success:
            scholarly.use_proxy(pg)
            print("Proxy configured successfully")
            return True
    except Exception as e:
        print(f"Warning: Could not set up proxy: {e}")
    return False


def fetch_metrics():
    """Fetch metrics from Google Scholar."""
    author = scholarly.search_author_id(SCHOLAR_ID)
    author = scholarly.fill(author, sections=['basics', 'indices'])

    return {
        "name": author.get("name", "Justin Nix"),
        "affiliation": author.get("affiliation", "University of Nebraska Omaha"),
        "h_index": author.get("hindex", None),
        "i10_index": author.get("i10index", None),
        "citations": author.get("citedby", None),
        "updated": datetime.now(timezone.utc).isoformat(),
        "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}"
    }


def load_existing_metrics():
    """Load existing metrics from file if available."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_metrics(metrics):
    """Save metrics to JSON file."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)


def main():
    print(f"Fetching Google Scholar data for ID: {SCHOLAR_ID}")

    # Try with proxy first
    setup_proxy()

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"Attempt {attempt}/{MAX_RETRIES}...")
            metrics = fetch_metrics()

            # Validate we got actual data
            if metrics["citations"] is not None:
                save_metrics(metrics)
                print(f"Success! Saved to {OUTPUT_PATH}")
                print(f"Citations: {metrics['citations']}")
                print(f"h-index: {metrics['h_index']}")
                print(f"i10-index: {metrics['i10_index']}")
                return
            else:
                print("Warning: Received empty metrics, retrying...")

        except Exception as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                wait_time = attempt * 5
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

    # All retries failed - keep existing data if valid
    print(f"All {MAX_RETRIES} attempts failed")
    existing = load_existing_metrics()

    if existing and existing.get("citations") is not None and "error" not in existing:
        print("Keeping existing valid metrics (fetch failed but existing data is good)")
        # Update timestamp to show we tried
        existing["last_fetch_attempt"] = datetime.now(timezone.utc).isoformat()
        existing["last_fetch_error"] = str(last_error)
        save_metrics(existing)
    else:
        # No valid existing data, write error state
        fallback = {
            "name": "Justin Nix",
            "affiliation": "University of Nebraska Omaha",
            "h_index": None,
            "i10_index": None,
            "citations": None,
            "updated": datetime.now(timezone.utc).isoformat(),
            "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}",
            "error": str(last_error)
        }
        save_metrics(fallback)
        print(f"Wrote fallback data to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
