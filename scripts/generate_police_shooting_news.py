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

# Search terms for police shooting news
SEARCH_QUERIES = [
    '"shot by police" OR "killed by police"',
    '"police officer shot" AND (suspect OR man OR woman OR person OR dog OR animal)',
    '"officer-involved shooting" AND (killed OR wounded OR fatally)',
    '"police shot and killed"'
]

EXCLUSIONS = (
    'NOT "police investigating" '
    'NOT "investigating a shooting" '
    'NOT "after a shooting" '
    'NOT "scene of a shooting" '
    'NOT "mass shooting investigation"'
)

# Categories for classification
CATEGORIES = {
    'incident': ['shooting', 'killed', 'fatal', 'death', 'incident'],
    'investigation': ['investigation', 'probe', 'review', 'inquiry', 'examining'],
    'accountability': ['reform', 'policy', 'training', 'accountability', 'discipline'],
    'legal': ['lawsuit', 'charges', 'trial', 'court', 'verdict', 'indictment'],
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
        'q': f'({query}) {EXCLUSIONS}',
        'from': from_date,
        'sortBy': 'publishedAt',
        'language': 'en',
        'sources': (
        'ap-news,reuters,cnn,abc-news,cbs-news,nbc-news,'
        'fox-news,usa-today'
    ),
        'qInTitle': '"shot by police" OR "police shot"',
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

def categorize_article(title, description):
    """Categorize article based on content"""
    text = (title + ' ' + description).lower()
    
    scores = {}
    for category, keywords in CATEGORIES.items():
        scores[category] = sum(1 for keyword in keywords if keyword in text)
    
    # Return category with highest score, or 'general' if no matches
    max_category = max(scores, key=scores.get)
    return max_category if scores[max_category] > 0 else 'general'

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
        .replace('–', '-')
        .replace('—', '-')
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
    
    # Deduplicate by normalized title (collapse wire duplicates)
    seen_titles = set()
    unique_articles = []
    
    for article in all_articles:
        norm_title = normalize_title(article.get('title'))
        if norm_title and norm_title not in seen_titles:
            seen_titles.add(norm_title)
            unique_articles.append(article)
    
    # Sort by date (newest first)
    unique_articles.sort(
        key=lambda x: x.get('publishedAt', ''),
        reverse=True
    )
    
    # Take top 50 most recent
    all_articles = unique_articles[:50]

    print(f"\nTotal articles after deduplication: {len(all_articles)}")
    
    # Create RSS feed
    rss = create_rss_feed(all_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\nRSS feed saved to: {OUTPUT_FILE}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
