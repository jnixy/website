#!/usr/bin/env python3
"""
Police Shooting Research RSS Feed Generator
Fetches recent academic publications about police shootings
"""

import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import time

# Configuration
OUTPUT_FILE = 'static/data/police-shooting-research.xml'
DAYS_BACK = 90  # Check last 3 months (academic publishing is slower)

# Academic search queries
SEARCH_QUERIES = [
    'police shooting',
    'officer-involved shooting',
    'police use of force',
    'police deadly force',
    'police violence',
    'officer-involved fatality',
]

# Journals/sources to prioritize (criminology, criminal justice, sociology, political science, public health)
PRIORITY_SOURCES = [
    'criminology',
    'criminology & public policy',
    'criminology and public policy',
    'justice quarterly',
    'journal of criminal justice',
    'police quarterly',
    'journal of research in crime',
    'journal of quantitative criminology',
    'criminal justice and behavior',
    'crime & delinquency',
    'crime and delinquency',
    'justice evaluation',
    'policing and society',
    'police practice & research',
    'police practice and research',
    'american journal of sociology',
    'american sociological review',
    'american political science review',
    'american journal of political science',
    'american journal of public health',
    'injury prevention',
    'jama',
    'new england journal of medicine',
    'plos one',
    'social science',
    'law and society',
]

def fetch_crossref(query, days_back=DAYS_BACK):
    """
    Fetch articles from Crossref API (free, no key required)
    Docs: https://api.crossref.org
    """
    url = 'https://api.crossref.org/works'
    
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    params = {
        'query': query,
        'filter': f'from-pub-date:{from_date}',
        'select': 'title,DOI,URL,published,author,container-title,abstract,type',
        'rows': 100,
        'sort': 'published',
        'order': 'desc'
    }
    
    headers = {
        'User-Agent': 'PoliceShootingTracker/1.0 (https://jnix.netlify.app; mailto:jnix@unomaha.edu)'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get('message', {}).get('items', [])
    except Exception as e:
        print(f"Error fetching from Crossref: {e}")
        return []

def fetch_pubmed(query, days_back=DAYS_BACK):
    """
    Fetch articles from PubMed (free, no key required for basic searches)
    Good for public health and medical journals
    """
    # PubMed requires two steps: search for IDs, then fetch details
    search_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    to_date = datetime.now().strftime('%Y/%m/%d')
    
    search_params = {
        'db': 'pubmed',
        'term': query,
        'mindate': from_date,
        'maxdate': to_date,
        'retmax': 50,
        'retmode': 'json',
        'sort': 'pub_date'
    }
    
    try:
        # Get article IDs
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()
        
        id_list = search_data.get('esearchresult', {}).get('idlist', [])
        
        if not id_list:
            return []
        
        # Fetch article details
        fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'json'
        }
        
        time.sleep(0.5)  # Be nice to NCBI servers
        
        fetch_response = requests.get(fetch_url, params=fetch_params)
        fetch_response.raise_for_status()
        fetch_data = fetch_response.json()
        
        articles = []
        for uid in id_list:
            if uid in fetch_data.get('result', {}):
                articles.append(fetch_data['result'][uid])
        
        return articles
    except Exception as e:
        print(f"Error fetching from PubMed: {e}")
        return []

def is_relevant_article(title, abstract):
    """
    Filter to identify relevant research about police shootings
    """
    text = (title + ' ' + (abstract or '')).lower()
    
    # Must contain core topics
    required_terms = [
        'police', 'officer', 'law enforcement', 'policing'
    ]
    
    if not any(term in text for term in required_terms):
        return False
    
    # Must relate to shootings/force/violence
    force_terms = [
        'shooting', 'shot', 'deadly force', 'lethal force',
        'use of force', 'excessive force', 'violence', 'fatality',
        'killing', 'death', 'homicide'
    ]
    
    if not any(term in text for term in force_terms):
        return False
    
    # Exclude if it's about officer victimization (unless comparative)
    officer_victim_only = [
        'officer safety',
        'officer victimization',
        'violence against police',
        'attacks on officers'
    ]
    
    # Allow if it mentions both officer and civilian outcomes
    if any(term in text for term in officer_victim_only):
        civilian_terms = ['civilian', 'suspect', 'citizen', 'community', 'public']
        if not any(term in text for term in civilian_terms):
            return False
    
    return True

def is_priority_source(source_name):
    """Check if article is from a priority journal"""
    if not source_name:
        return False
    source_lower = source_name.lower()
    return any(priority in source_lower for priority in PRIORITY_SOURCES)

def format_authors(authors):
    """Format author list for display"""
    if not authors or len(authors) == 0:
        return "Unknown Authors"
    
    if len(authors) == 1:
        author = authors[0]
        return f"{author.get('family', 'Unknown')}, {author.get('given', '')}"
    
    elif len(authors) == 2:
        return f"{authors[0].get('family', 'Unknown')} & {authors[1].get('family', 'Unknown')}"
    
    else:
        return f"{authors[0].get('family', 'Unknown')} et al."

def parse_crossref_article(item):
    """Parse Crossref article into standard format"""
    title = item.get('title', ['Untitled'])[0] if item.get('title') else 'Untitled'
    
    # Get DOI and construct URL
    doi = item.get('DOI', '')
    url = f"https://doi.org/{doi}" if doi else item.get('URL', '')
    
    # Get publication date
    pub_date_parts = item.get('published', {}).get('date-parts', [[]])[0]
    if pub_date_parts:
        pub_date = datetime(pub_date_parts[0], 
                           pub_date_parts[1] if len(pub_date_parts) > 1 else 1,
                           pub_date_parts[2] if len(pub_date_parts) > 2 else 1)
    else:
        pub_date = datetime.now()
    
    # Get journal name
    journal = item.get('container-title', ['Unknown Journal'])[0] if item.get('container-title') else 'Unknown Journal'
    
    # Get authors
    authors = format_authors(item.get('author', []))
    
    # Get abstract
    abstract = item.get('abstract', '')
    
    # Get article type
    article_type = item.get('type', 'journal-article')
    
    return {
        'title': title,
        'url': url,
        'pub_date': pub_date,
        'journal': journal,
        'authors': authors,
        'abstract': abstract,
        'type': article_type,
        'doi': doi,
        'is_priority': is_priority_source(journal)
    }

def parse_pubmed_article(item):
    """Parse PubMed article into standard format"""
    title = item.get('title', 'Untitled')
    
    # Get PubMed URL
    pmid = item.get('uid', '')
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ''
    
    # Get publication date
    pub_date_str = item.get('pubdate', '')
    try:
        pub_date = datetime.strptime(pub_date_str, '%Y %b %d')
    except:
        pub_date = datetime.now()
    
    # Get journal name
    journal = item.get('source', 'Unknown Journal')
    
    # Get authors
    authors = ', '.join(item.get('authors', [])[:3])
    if len(item.get('authors', [])) > 3:
        authors += ' et al.'
    
    return {
        'title': title,
        'url': url,
        'pub_date': pub_date,
        'journal': journal,
        'authors': authors,
        'abstract': '',  # PubMed basic API doesn't include abstracts
        'type': 'journal-article',
        'doi': '',
        'is_priority': is_priority_source(journal)
    }

def create_rss_feed(articles):
    """Create RSS 2.0 feed from articles"""
    
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    
    channel = ET.SubElement(rss, 'channel')
    
    # Channel metadata
    title = ET.SubElement(channel, 'title')
    title.text = 'U.S. Police Shooting Research Tracker'
    
    link = ET.SubElement(channel, 'link')
    link.text = 'https://jnix.netlify.app/police-shooting-research/'
    
    description = ET.SubElement(channel, 'description')
    description.text = 'Recent academic research on police shootings and use of deadly force'
    
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
        
        # Create description with authors and journal
        desc_parts = []
        if article['authors']:
            desc_parts.append(f"<strong>Authors:</strong> {article['authors']}")
        if article['journal']:
            desc_parts.append(f"<strong>Journal:</strong> {article['journal']}")
        if article['abstract']:
            desc_parts.append(f"<p>{article['abstract'][:500]}...</p>")
        
        item_desc = ET.SubElement(item, 'description')
        item_desc.text = '<br>'.join(desc_parts)
        
        pub_date = ET.SubElement(item, 'pubDate')
        pub_date.text = article['pub_date'].strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        # Add category
        item_category = ET.SubElement(item, 'category')
        item_category.text = 'research'
        
        # Add source (journal name)
        item_source = ET.SubElement(item, 'source')
        item_source.text = article['journal']
        
        # Add priority flag
        if article.get('is_priority'):
            item_priority = ET.SubElement(item, 'priority')
            item_priority.text = 'true'
    
    return rss

def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')

def main():
    """Main execution function"""
    print("Fetching police shooting research...")
    
    all_articles = []
    
    # Fetch from Crossref
    print("\n=== Searching Crossref ===")
    for query in SEARCH_QUERIES:
        print(f"Query: {query}")
        items = fetch_crossref(query)
        print(f"  Found {len(items)} results")
        
        for item in items:
            article = parse_crossref_article(item)
            if is_relevant_article(article['title'], article.get('abstract', '')):
                all_articles.append(article)
        
        time.sleep(1)  # Be nice to API
    
    # Optionally fetch from PubMed (uncomment if desired)
    # print("\n=== Searching PubMed ===")
    # for query in ['police shooting', 'officer-involved shooting']:
      #  print(f"Query: {query}")
      #  items = fetch_pubmed(query)
      #  print(f"  Found {len(items)} results")
       
      #  for item in items:
      #      article = parse_pubmed_article(item)
      #      if is_relevant_article(article['title'], ''):
      #          all_articles.append(article)
       
      #  time.sleep(1)
    
    print(f"\nTotal articles before deduplication: {len(all_articles)}")
    
    # Deduplicate by title
    seen_titles = set()
    unique_articles = []
    
    for article in all_articles:
        title_lower = article['title'].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)
    
    print(f"Articles after deduplication: {len(unique_articles)}")
    
    # Sort by date (newest first), with priority sources first
    unique_articles.sort(
        key=lambda x: (x.get('is_priority', False), x['pub_date']),
        reverse=True
    )
    
    # Take top 30 most recent
    final_articles = unique_articles[:30]
    
    print(f"\nFinal article count: {len(final_articles)}")
    
    if len(final_articles) == 0:
        print("\n⚠️  WARNING: No articles found. Feed will not be generated.")
        return
    
    # Create RSS feed
    rss = create_rss_feed(final_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\nRSS feed saved to: {OUTPUT_FILE}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print sample titles
    print("\nSample articles:")
    for i, article in enumerate(final_articles[:5], 1):
        priority = "⭐ " if article.get('is_priority') else ""
        print(f"  {i}. {priority}{article['authors']} ({article['pub_date'].year})")
        print(f"     {article['title'][:80]}...")
        print(f"     {article['journal']}\n")

if __name__ == '__main__':
    main()
