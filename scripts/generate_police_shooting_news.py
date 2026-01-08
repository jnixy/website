#!/usr/bin/env python3
"""
Police Shooting News RSS Feed Generator
Fetches recent news about police shootings and generates an RSS feed
"""

import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# Configuration
NEWS_API_KEY = os.environ.get('NEWS_API_KEY', 'YOUR_API_KEY_HERE')
OUTPUT_FILE = 'static/data/police-shooting-news.xml'
DAYS_BACK = 30

# Simplified search queries - NewsAPI has query length limits
# Includes both local/state and federal law enforcement
SEARCH_QUERIES = [
    'police shooting',
    'officer-involved shooting',
    'police shot killed',
    'officer shot suspect',
    'federal agent shooting',      # NEW - federal law enforcement
    'ICE agent shot',               # NEW - Immigration and Customs Enforcement
    'Border Patrol shooting',       # NEW - Customs and Border Protection
]

# Categories for classification
CATEGORIES = {
    'incident': ['shooting', 'killed', 'fatal', 'death', 'shot', 'fired'],
    'investigation': ['investigation', 'probe', 'review', 'inquiry', 'examining', 'district attorney'],
    'accountability': ['reform', 'policy', 'training', 'accountability', 'discipline', 'fired', 'terminated'],
    'legal': ['lawsuit', 'charges', 'trial', 'court', 'verdict', 'indictment', 'arrested', 'charged'],
    'research': ['study', 'research', 'data', 'analysis', 'report', 'findings']
}

def fetch_news_api(query, days_back=DAYS_BACK):
    """
    Fetch news from NewsAPI.org
    Get a free API key at: https://newsapi.org/
    """
    url = 'https://newsapi.org/v2/everything'
    
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    params = {
        'q': query,
        'from': from_date,
        'to': datetime.now().strftime('%Y-%m-%d'),
        'sortBy': 'publishedAt',
        'language': 'en',
        'apiKey': NEWS_API_KEY,
        'pageSize': 100
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get('articles', [])
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
        return []

def is_relevant_story(title, description):
    """
    Filter to identify stories about police shooting civilians (not investigating shootings)
    Returns True if story appears to be about police shooting someone
    
    IMPROVED VERSION with more lenient filters
    """
    if not title:
        return False
        
    text = (title + ' ' + (description or '')).lower()
    
    # EXPANDED: More comprehensive positive indicators
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
        'ice officer shot',            # NEW - ICE uses "officer" too
        'ice officer killed',          # NEW
        'ice officer shoots',          # NEW - Active voice
        'ice officer fatally shot',    # NEW
        'ice officer fatally shoots',  # NEW - Active voice
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
        'shot by ice',                 # NEW - "shot by ICE"
        'killed by ice',               # NEW
        'killed by agent',             # NEW
        'killed by federal',           # NEW
        'agent shoots',                # NEW - Active voice
        'agent kills',                 # NEW - Active voice
        'federal agent shoots',        # NEW
        'federal agent kills',         # NEW
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
        'ice agent was shot',            # More specific
        'ice agent was killed',          # More specific
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
    
    # RELAXED: More precise investigation-only exclusions
    # Only exclude if it's CLEARLY just about investigating, not the incident itself
    investigation_only = [
        'police are investigating a shooting that',  # More specific
        'investigating a shooting at',  # More specific
        'arrived at scene of shooting',
        'officers responded to reports of a shooting',  # Clarified
    ]
    
    # Only exclude if investigation phrase is present AND no incident details
    has_investigation_phrase = any(phrase in text for phrase in investigation_only)
    if has_investigation_phrase:
        # But allow it if it also contains incident indicators
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
    # RELAXED: Reduced minimum title length from 30 to 20 characters
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

def create_rss_feed(articles):
    """Create RSS 2.0 feed from articles"""
    
    # Create root RSS element
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    
    channel = ET.SubElement(rss, 'channel')
    
    # Channel metadata
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
    
    # Add items
    for article in articles:
        item = ET.SubElement(channel, 'item')
        
        item_title = ET.SubElement(item, 'title')
        item_title.text = article['title']
        
        item_link = ET.SubElement(item, 'link')
        item_link.text = article['url']
        
        item_desc = ET.SubElement(item, 'description')
        item_desc.text = article.get('description', '')
        
        pub_date = ET.SubElement(item, 'pubDate')
        # Parse and format the date
        try:
            dt = datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            pub_date.text = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        except:
            pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Add category
        category = categorize_article(
            article['title'], 
            article.get('description', '')
        )
        item_category = ET.SubElement(item, 'category')
        item_category.text = category
        
        # Add source
        source_name = article.get('source', {}).get('name', 'News Source')
        item_source = ET.SubElement(item, 'source')
        item_source.text = source_name
    
    return rss

def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')

def normalize_title(title):
    """Normalize titles for deduplication across outlets"""
    if not title:
        return ''
    return (
        title.lower()
        .replace('â€"', '-')
        .replace('â€"', '-')
        .replace(':', '')
        .replace(';', '')
        .replace('"', '')
        .replace("'", '')
        .strip()
    )

def main():
    """Main execution function"""
    print("Fetching police shooting news...")
    print("=" * 60)
    
    all_articles = []
    
    # Fetch from each query
    for query in SEARCH_QUERIES:
        print(f"\nSearching for: {query}")
        articles = fetch_news_api(query)
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
    
    # Deduplicate by normalized title
    seen_titles = set()
    unique_articles = []
    
    for article in filtered_articles:
        norm_title = normalize_title(article.get('title'))
        if norm_title and norm_title not in seen_titles:
            seen_titles.add(norm_title)
            unique_articles.append(article)
    
    print(f"Articles after deduplication: {len(unique_articles)}")
    
    # Sort by date (newest first)
    unique_articles.sort(
        key=lambda x: x.get('publishedAt', ''),
        reverse=True
    )
    
    # Take top 50 most recent
    final_articles = unique_articles[:50]
    
    print(f"\n{'=' * 60}")
    print(f"Final article count: {len(final_articles)}")
    
    if len(final_articles) == 0:
        print("\n⚠️  WARNING: No articles found. Feed will not be generated.")
        print("This could mean:")
        print("  - No relevant stories in the past 30 days")
        print("  - Filtering is too strict")
        print("  - NewsAPI returned no results")
        return
    
    # Create RSS feed
    rss = create_rss_feed(final_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\nRSS feed saved to: {OUTPUT_FILE}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print sample titles for verification
    print(f"\n{'=' * 60}")
    print("Sample titles from feed (most recent):")
    for i, article in enumerate(final_articles[:10], 1):
        published = article.get('publishedAt', 'Unknown date')
        print(f"  {i}. [{published[:10]}] {article['title']}")
    
    print(f"\n{'=' * 60}")

if __name__ == '__main__':
    main()
