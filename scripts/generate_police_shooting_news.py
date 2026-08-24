#!/usr/bin/env python3
"""
Police Shooting News Feed Generator
Fetches recent news about police shootings and writes both an RSS feed
(static/data/police-shooting-news.xml) and a JSON sidecar
(static/data/police-shooting-news.json) consumed by the shared NewsFeed
front-end component (static/js/news-feed.js).
"""

import json
import os
import time
from datetime import datetime

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
RSS_OUTPUT_FILE = 'static/data/police-shooting-news.xml'
JSON_OUTPUT_FILE = 'static/data/police-shooting-news.json'
DAYS_BACK = 30

# The RSS feed is a short "what's new" subscription; the JSON file backs the
# on-page feed and keeps a longer rolling history so a single quiet/failed
# fetch never blanks the page (see MAX_JSON_ITEMS below).
MAX_RSS_ITEMS = 50
MAX_JSON_ITEMS = 200

# Simplified search queries - NewsAPI has query length limits
# Includes both local/state and federal law enforcement
SEARCH_QUERIES = [
    'police shooting',
    'officer-involved shooting',
    'police shot killed',
    'officer shot suspect',
    'federal agent shooting',      # federal law enforcement
    'ICE agent shot',               # Immigration and Customs Enforcement
    'Border Patrol shooting',       # Customs and Border Protection
]

# Categories for classification
CATEGORIES = {
    'incident': ['shooting', 'killed', 'fatal', 'death', 'shot', 'fired'],
    'investigation': ['investigation', 'probe', 'review', 'inquiry', 'examining', 'district attorney'],
    'accountability': ['reform', 'policy', 'training', 'accountability', 'discipline', 'fired', 'terminated'],
    'legal': ['lawsuit', 'charges', 'trial', 'court', 'verdict', 'indictment', 'arrested', 'charged'],
    'research': ['study', 'research', 'data', 'analysis', 'report', 'findings']
}


def fix_mojibake(text):
    """
    Repair text that was UTF-8 but got mis-decoded as Latin-1 upstream
    (shows up as sequences like 'â€™' for a right single quote). Falls back
    to the original text if it isn't actually mojibake.
    """
    if not text:
        return text
    try:
        return text.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def parse_gdelt_date(gdelt_date):
    """Convert GDELT date format (YYYYMMDDTHHMMSSZ) to ISO format (YYYY-MM-DDTHH:MM:SSZ)"""
    try:
        dt = datetime.strptime(gdelt_date, '%Y%m%dT%H%M%SZ')
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')


def fetch_gdelt(query, days_back=DAYS_BACK):
    """
    Fetch news from GDELT DOC 2.0 API — free, no API key, no server restrictions.
    Returns articles normalized to this script's canonical story shape:
    title, url, description, date, source (flat string).
    """
    url = 'https://api.gdeltproject.org/api/v2/doc/doc'

    params = {
        'query': f'{query} sourcecountry:US',
        'mode': 'artlist',
        'maxrecords': 250,
        'format': 'json',
        'timespan': f'{days_back}d',
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        raw_articles = response.json().get('articles', [])
        return [
            {
                'title': fix_mojibake(a.get('title', '')),
                'url': a.get('url', ''),
                # GDELT's artlist mode doesn't return a description/summary field.
                'description': '',
                'date': parse_gdelt_date(a.get('seendate', '')),
                'source': a.get('domain', 'News Source'),
            }
            for a in raw_articles
        ]
    except Exception as e:
        print(f"Error fetching from GDELT: {e}")
        return []


def is_relevant_story(title, description):
    """
    Filter to identify stories about police shooting civilians (not investigating shootings)
    Returns True if story appears to be about police shooting someone
    """
    if not title:
        return False

    text = (title + ' ' + (description or '')).lower()

    # Comprehensive positive indicators
    # Includes local/state AND federal law enforcement
    # Includes both passive ("shot by") and active ("shoots") voice
    positive_indicators = [
        'police shot',
        'officer shot',
        'police shooting',
        'officer-involved shooting',
        'police opened fire',
        'officer opened fire',
        'police killed',
        'officer killed',
        'shot by police',
        'shot by officer',
        'police fatally shot',
        'officer fatally shot',
        'deputy shot',
        'deputy killed',
        'deputies shot',
        'deputies killed',
        'trooper shot',
        'trooper killed',
        'state trooper shot',
        'shooting by police',
        'shooting by officer',
        'police fire',  # as in "police fire at"
        'officers fire',
        'deputy fatally shot',
        'trooper fatally shot',
        'police shoots',           # Active voice
        'officer shoots',          # Active voice
        'deputy shoots',           # Active voice
        'trooper shoots',          # Active voice
        # Federal law enforcement
        'agent shot',
        'agent killed',
        'agent fatally shot',
        'federal agent shot',
        'ice agent shot',              # Immigration and Customs Enforcement
        'ice agent killed',
        'ice agent shoots',            # Active voice
        'ice agent fatally shot',
        'ice officer shot',            # ICE uses "officer" too
        'ice officer killed',
        'ice officer shoots',          # Active voice
        'ice officer fatally shot',
        'ice officer fatally shoots',  # Active voice
        'fbi agent shot',
        'fbi agent shoots',
        'dea agent shot',
        'dea agent shoots',
        'atf agent shot',
        'atf agent shoots',
        'border patrol shot',
        'border patrol agent shot',
        'border patrol shoots',
        'marshal shot',
        'marshal shoots',
        'shot by agent',
        'shot by federal',
        'shot by ice',
        'killed by ice',
        'killed by agent',
        'killed by federal',
        'agent shoots',                # Active voice
        'agent kills',                 # Active voice
        'federal agent shoots',
        'federal agent kills',
    ]

    has_positive = any(phrase in text for phrase in positive_indicators)
    if not has_positive:
        return False

    # Exclude if officer is the victim
    # Includes local/state AND federal law enforcement as victims
    # IMPORTANT: These must be specific enough to not catch cases where officer/agent is the SHOOTER
    officer_victim_phrases = [
        'officer was shot',
        'officer shot and killed by',    # "by" indicates officer is victim
        'deputy was shot',
        'deputy shot and killed by',
        'trooper was shot',
        'trooper shot and killed by',
        'officer killed in ambush',
        'officer killed in attack',
        'deputy killed in ambush',
        'deputy killed in attack',
        'trooper killed in ambush',
        'trooper killed in attack',
        'shot and killed officer',       # officer is object (victim)
        'shot and killed deputy',
        'shot and killed trooper',
        'gunman killed officer',
        'shooter killed officer',
        'suspect killed officer',
        'killed the officer',
        'killed the deputy',
        'officer died from',             # "from" indicates victim
        'deputy died from',
        'officer dies after being',      # "after being" indicates victim
        'deputy dies after being',
        # Federal law enforcement as victims
        'agent was shot',
        'agent shot and killed by',      # "by" indicates agent is victim
        'agent killed in ambush',
        'agent killed in attack',
        'shot and killed agent',         # agent is object (victim)
        'ice agent was shot',
        'ice agent was killed',
        'fbi agent was shot',
        'fbi agent was killed',
        'dea agent was shot',
        'dea agent was killed',
        'atf agent was shot',
        'atf agent was killed',
        'border patrol agent was shot',
        'border patrol agent was killed',
        'marshal was shot',
        'marshal was killed',
        'agent died from',
        'agent dies after being',
        'suspect killed agent',
        'gunman killed agent',
        'shooter killed agent',
    ]

    if any(phrase in text for phrase in officer_victim_phrases):
        return False

    # Only exclude if it's CLEARLY just about investigating, not the incident itself
    investigation_only = [
        'police are investigating a shooting that',
        'investigating a shooting at',
        'arrived at scene of shooting',
        'officers responded to reports of a shooting',
    ]

    has_investigation_phrase = any(phrase in text for phrase in investigation_only)
    if has_investigation_phrase:
        incident_details = ['killed', 'fatal', 'death', 'died', 'wounded', 'injured', 'opened fire']
        if not any(detail in text for detail in incident_details):
            return False

    # Exclude international stories (check for specific location mentions)
    international_locations = [
        'london police', 'met police', 'uk police',
        'toronto police', 'rcmp', 'canadian police',
        'australian police', 'sydney police',
        'new zealand police',
        'in london', 'in toronto', 'in sydney', 'in melbourne',
        'in canada', 'in australia', 'in uk',
    ]

    if any(location in text for location in international_locations):
        return False

    # Additional quality filters
    if len(title) < 20:
        return False

    # Exclude if title is mostly capitalized (often wire service duplicates)
    if title.isupper():
        return False

    return True


def categorize_article(title, description):
    """Categorize article based on content"""
    text = (title + ' ' + (description or '')).lower()

    scores = {}
    for category, keywords in CATEGORIES.items():
        scores[category] = sum(1 for keyword in keywords if keyword in text)

    # Return category with highest score, or 'incident' if no matches
    max_category = max(scores, key=scores.get)
    return max_category if scores[max_category] > 0 else 'incident'


def normalize_title(title):
    """Normalize titles for deduplication across outlets"""
    if not title:
        return ''
    return (
        fix_mojibake(title)
        .lower()
        .replace(':', '')
        .replace(';', '')
        .replace('"', '')
        .replace("'", '')
        .strip()
    )


def load_previous_stories(json_path):
    """
    Load stories written by a previous run so a quiet/failed fetch never
    wipes the page — new results are merged on top of this history rather
    than replacing it outright.
    """
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('stories', [])
    except Exception as e:
        print(f"Warning: could not read previous {json_path} ({e}); starting fresh")
        return []


def merge_stories(previous, new_stories):
    """Combine previous and newly-fetched stories, deduplicated by URL
    (falling back to normalized title), newest first."""
    seen_urls = set()
    seen_titles = set()
    merged = []

    for story in list(new_stories) + list(previous):
        url = story.get('url', '')
        norm_title = normalize_title(story.get('title', ''))
        if url and url in seen_urls:
            continue
        if norm_title and norm_title in seen_titles:
            continue
        if url:
            seen_urls.add(url)
        if norm_title:
            seen_titles.add(norm_title)
        merged.append(story)

    merged.sort(key=lambda s: s.get('date', ''), reverse=True)
    return merged


def create_rss_feed(stories):
    """Create RSS 2.0 feed from a list of story dicts"""

    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = ET.SubElement(rss, 'channel')

    title = ET.SubElement(channel, 'title')
    title.text = 'U.S. Police Shooting News Tracker'

    link = ET.SubElement(channel, 'link')
    link.text = 'https://jnix.netlify.app/police-shooting-news/'

    description = ET.SubElement(channel, 'description')
    description.text = 'Automated news aggregation tracking police-involved shootings in the United States'

    language = ET.SubElement(channel, 'language')
    language.text = 'en-us'

    last_build = ET.SubElement(channel, 'lastBuildDate')
    last_build.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

    for story in stories:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        item_title.text = story['title']

        item_link = ET.SubElement(item, 'link')
        item_link.text = story['url']

        item_desc = ET.SubElement(item, 'description')
        item_desc.text = story.get('description', '')

        pub_date = ET.SubElement(item, 'pubDate')
        try:
            dt = datetime.strptime(story['date'], '%Y-%m-%dT%H:%M:%SZ')
            pub_date.text = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        except Exception:
            pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

        item_category = ET.SubElement(item, 'category')
        item_category.text = story.get('category', 'incident')

        item_source = ET.SubElement(item, 'source')
        item_source.text = story.get('source', 'News Source')

    return rss


def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')


def main():
    """Main execution function"""
    print("Fetching police shooting news...")
    print("=" * 60)

    all_articles = []

    for query in SEARCH_QUERIES:
        print(f"\nSearching for: {query}")
        articles = fetch_gdelt(query)
        print(f"  Raw results: {len(articles)} articles")
        all_articles.extend(articles)

    print(f"\n{'=' * 60}")
    print(f"Total articles before filtering: {len(all_articles)}")

    # Apply relevance filtering
    filtered_articles = [
        article for article in all_articles
        if is_relevant_story(article.get('title', ''), article.get('description', ''))
    ]

    print(f"Articles after relevance filtering: {len(filtered_articles)}")

    # Categorize and dedupe within this run
    new_stories = []
    seen_titles = set()
    for article in filtered_articles:
        norm_title = normalize_title(article.get('title'))
        if not norm_title or norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)
        article['category'] = categorize_article(article['title'], article.get('description', ''))
        new_stories.append(article)

    print(f"New stories this run: {len(new_stories)}")

    if len(new_stories) == 0:
        print("\nWARNING: No new articles found this run. This could mean:")
        print("  - No relevant stories in the past 30 days")
        print("  - Filtering is too strict")
        print("  - GDELT returned no results")
        print("Falling back to previously published stories so the page isn't wiped.")

    # Merge with history so a quiet/failed run never blanks the page
    previous_stories = load_previous_stories(JSON_OUTPUT_FILE)
    merged_stories = merge_stories(previous_stories, new_stories)

    print(f"\n{'=' * 60}")
    print(f"Total stories after merge with history: {len(merged_stories)}")

    if len(merged_stories) == 0:
        print("\nERROR: No stories available (first run with no fetch results). Nothing to write.")
        return

    json_stories = merged_stories[:MAX_JSON_ITEMS]
    rss_stories = merged_stories[:MAX_RSS_ITEMS]

    # Save JSON (backs the on-page NewsFeed component)
    os.makedirs(os.path.dirname(JSON_OUTPUT_FILE), exist_ok=True)
    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'stories': json_stories,
        }, f, indent=2, ensure_ascii=False)
    print(f"JSON feed saved to: {JSON_OUTPUT_FILE} ({len(json_stories)} stories)")

    # Save RSS (subscription feed)
    rss = create_rss_feed(rss_stories)
    os.makedirs(os.path.dirname(RSS_OUTPUT_FILE), exist_ok=True)
    with open(RSS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    print(f"RSS feed saved to: {RSS_OUTPUT_FILE} ({len(rss_stories)} items)")

    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n{'=' * 60}")
    print("Sample titles from feed (most recent):")
    for i, story in enumerate(json_stories[:10], 1):
        print(f"  {i}. [{story.get('date', 'Unknown date')[:10]}] {story['title']}")

    print(f"\n{'=' * 60}")


if __name__ == '__main__':
    main()
