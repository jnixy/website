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

# Search terms - focused on police shooting civilians (not investigating shootings)
SEARCH_QUERIES = [
    '"police shot" AND ("killed" OR "fatally wounded" OR "died")',
    '"officer-involved shooting" AND ("fatal" OR "killed" OR "death")',
    '"police opened fire" AND ("killed" OR "wounded" OR "struck")',
    '"officer shot" AND ("suspect" OR "man" OR "woman" OR "person") AND ("killed" OR "died")',
]

# Strong exclusions to filter out irrelevant stories
EXCLUSIONS = [
    'NOT "police investigating"',
    'NOT "investigating a shooting"',
    'NOT "after a shooting"',
    'NOT "scene of a shooting"',
    'NOT "responded to a shooting"',
    'NOT "police arrived"',
    'NOT "police were called"',
    'NOT "mass shooting"',
    'NOT "school shooting"',
    'NOT "officer shot and killed"',  # Officer as victim
    'NOT "officer was shot"',  # Officer as victim
    'NOT "deputy shot"',  # Deputy as victim
    'NOT "trooper shot"',  # Trooper as victim
]

# Countries/cities to exclude (international stories)
LOCATION_EXCLUSIONS = [
    'NOT "UK"',
    'NOT "Britain"',
    'NOT "London"',
    'NOT "Canada"',
    'NOT "Toronto"',
    'NOT "Montreal"',
    'NOT "Australia"',
    'NOT "Sydney"',
    'NOT "Melbourne"',
    'NOT "New Zealand"',
    'NOT "India"',
    'NOT "Pakistan"',
    'NOT "Philippines"',
    'NOT "Mexico"',
]

# Categories for classification
CATEGORIES = {
    'incident': ['shooting', 'killed', 'fatal', 'death', 'shot', 'fired'],
    'investigation': ['investigation', 'probe', 'review', 'inquiry', 'examining', 'district attorney'],
    'accountability': ['reform', 'policy', 'training', 'accountability', 'discipline', 'fired', 'terminated'],
    'legal': ['lawsuit', 'charges', 'trial', 'court', 'verdict', 'indictment', 'arrested', 'charged'],
    'research': ['study', 'research', 'data', 'analysis', 'report', 'findings']
}

# Additional filtering - words that MUST appear for incident stories
INCIDENT_REQUIRED_WORDS = [
    'shot by police',
    'police shot',
    'officer shot',
    'police shooting',
    'officer-involved shooting',
    'police opened fire',
    'officer opened fire',
    'police killed',
    'officer killed',
]

def fetch_news_api(query, days_back=DAYS_BACK):
    """
    Fetch news from NewsAPI.org
    Get a free API key at: https://newsapi.org/
    """
    url = 'https://newsapi.org/v2/everything'
    
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    # Combine all exclusions
    all_exclusions = ' '.join(EXCLUSIONS + LOCATION_EXCLUSIONS)
    
    params = {
        'q': f'({query}) {all_exclusions}',
        'from': from_date,
        'to': datetime.now().strftime('%Y-%m-%d'),
        'sortBy': 'publishedAt',
        'language': 'en',
        'searchIn': 'title,description',
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
    Additional filtering to catch false positives
    Returns True if story appears to be about police shooting someone
    """
    text = (title + ' ' + (description or '')).lower()
    
    # Must contain at least one incident indicator
    has_incident_word = any(phrase in text for phrase in INCIDENT_REQUIRED_WORDS)
    if not has_incident_word:
        return False
    
    # Exclude stories where police are victims
    officer_victim_phrases = [
        'officer shot and killed',
        'officer was shot',
        'deputy shot and',
        'trooper shot and',
        'officer killed in',
        'officers killed',
        'police officer killed',
        'gunman killed officer',
        'shot and killed an officer',
        'shot a police officer',
        'shot an officer',
    ]
    if any(phrase in text for phrase in officer_victim_phrases):
        return False
    
    # Exclude stories about police investigating shootings
    investigation_phrases = [
        'police are investigating',
        'police investigating',
        'investigation into shooting',
        'responded to reports of',
        'arrived at the scene',
        'called to the scene',
    ]
    if any(phrase in text for phrase in investigation_phrases):
        return False
    
    # Exclude international locations mentioned in text
    international_indicators = [
        'london', 'uk police', 'british police', 'met police',
        'toronto', 'rcmp', 'canadian police',
        'sydney', 'melbourne', 'australian',
        'new zealand', 'auckland',
    ]
    if any(indicator in text for indicator in international_indicators):
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
        .replace('—', '-')
        .replace('–', '-')
        .replace(':', '')
        .replace(';', '')
        .strip()
    )

def main():
    """Main execution function"""
    print("Fetching police shooting news...")
    
    all_articles = []
    
    # Fetch from each query
    for query in SEARCH_QUERIES:
        print(f"Searching for: {query}")
        articles = fetch_news_api(query)
        all_articles.extend(articles)
        print(f"  Found {len(articles)} articles")
    
    print(f"\nTotal articles before filtering: {len(all_articles)}")
    
    # Apply additional relevance filtering
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
    
    print(f"\nFinal article count: {len(final_articles)}")
    
    # Create RSS feed
    rss = create_rss_feed(final_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\nRSS feed saved to: {OUTPUT_FILE}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print sample titles for verification
    if final_articles:
        print("\nSample titles:")
        for article in final_articles[:5]:
            print(f"  - {article['title']}")

if __name__ == '__main__':
    main()
