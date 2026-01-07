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

# Academic search queries - comprehensive coverage
SEARCH_QUERIES = [
    'police shooting',
    'police use of force',
    'police deadly force',
    'police violence',
    'officer-involved shooting',
    'police killings',
    'police accountability',
    'police misconduct',
    'racial disparities police',
]

# Journals/sources to prioritize (criminology, criminal justice, sociology, political science, public health)
PRIORITY_SOURCES = [
    'criminology',
    'criminology & public policy',
    'criminology and public policy',
    'justice quarterly',
    'journal of criminal justice',
    'police quarterly',
    'journal of research in crime and delinquency',
    'journal of quantitative criminology',
    'criminal justice and behavior',
    'crime & delinquency',
    'crime and delinquency',
    'justice evaluation journal',
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
    Filter to identify relevant research about police shootings and use of force
    Balanced approach: catches broader policing research while excluding noise
    """
    if not title:
        return False
        
    text = (title + ' ' + (abstract or '')).lower()
    
    # MUST contain explicit policing terms (core requirement)
    policing_terms = [
        'police', 'policing', 'law enforcement', 'cop', 'cops'
    ]
    
    has_policing = any(term in text for term in policing_terms)
    if not has_policing:
        # Special case: "officer" with clear policing context
        if 'officer' in text:
            policing_context = [
                'patrol', 'arrest', 'department', 'badge',
                'sheriff', 'deputy', 'trooper', 'detective'
            ]
            if any(context in text for context in policing_context):
                has_policing = True
        
        if not has_policing:
            return False
    
    # MUST relate to force/violence/encounters (but more permissive)
    # Split into tiers - need at least one from either tier
    
    # Tier 1: Explicit violence/force (strongest relevance)
    explicit_force = [
        'shooting', 'shot', 'deadly force', 'lethal force',
        'use of force', 'excessive force', 'violence', 'fatality',
        'killing', 'killed', 'death', 'homicide', 'fatal',
        'shoot', 'fired weapon', 'discharged weapon'
    ]
    
    # Tier 2: Related concepts (still relevant but broader)
    related_force = [
        'firearm', 'gun', 'weapon', 'armed',
        'force continuum', 'de-escalation', 'use-of-force',
        'encounter', 'incident', 'confrontation',
        'accountability', 'misconduct', 'brutality',
        'racial disparity', 'disparate impact'
    ]
    
    has_force_terms = (
        any(term in text for term in explicit_force) or
        any(term in text for term in related_force)
    )
    
    if not has_force_terms:
        return False
    
    # Exclude clearly irrelevant topics (even if they mention "force" or "officer")
    exclude_terms = [
        # Physical science
        'atomic force microscopy', 'electrostatic force', 'magnetic force',
        # Engineering
        'reliability engineering', 'system safety', 'structural force',
        # Military (not police)
        'armed forces', 'military officer', 'marine corps', 'army officer',
        'air force', 'naval officer', 'combat officer', 'military training',
        # Healthcare
        'nursing', 'nurse education', 'medical officer', 'health officer',
        # Other occupations
        'warehouse', 'correctional officer', 'probation officer',
        'fishing', 'wildlife officer', 'park ranger', 'forest officer',
        # Non-policing contexts
        'coal riot', 'romantic poetry', 'maritime police 18', 'river police 18'
    ]
    
    if any(term in text for term in exclude_terms):
        return False
    
    # Exclude historical studies older than 1950s (unless comparative)
    very_old_historical = [
        '18th century', '19th century', '1800s', '1700s',
        'victorian', 'colonial police', 'historical marine police'
    ]
    
    if any(term in text for term in very_old_historical):
        contemporary_terms = ['modern', 'contemporary', 'compared to', 'evolution']
        if not any(term in text for term in contemporary_terms):
            return False
    
    # Exclude purely international studies (non-U.S.) unless explicitly comparative
    international_only_terms = [
        'german police', 'uk police', 'british police', 'canadian police',
        'australian police', 'european police', 'asian police',
        'french police', 'italian police', 'spanish police'
    ]
    
    if any(term in text for term in international_only_terms):
        # Allow if comparative (mentions U.S./American or is comparative study)
        us_terms = ['united states', 'u.s.', 'us ', 'american', 'cross-national', 'comparative', 'international comparison']
        if not any(term in text for term in us_terms):
            return False
    
    # Exclude fitness/training studies unless they relate to use of force
    if any(term in text for term in ['physical fitness', 'strength training', 'conditioning', 'tactical fitness']):
        # Must also mention force/violence context
        if not any(term in text for term in explicit_force):
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
    print(f"Searching back {DAYS_BACK} days")
    
    all_articles = []
    raw_count = 0
    
    # Fetch from Crossref
    print("\n=== Searching Crossref ===")
    for query in SEARCH_QUERIES:
        print(f"Query: {query}")
        items = fetch_crossref(query)
        raw_count += len(items)
        print(f"  Found {len(items)} raw results")
        
        for item in items:
            article = parse_crossref_article(item)
            all_articles.append(article)
        
        time.sleep(1)  # Be nice to API
    
    print(f"\n=== Filtering Results ===")
    print(f"Total raw articles from Crossref: {raw_count}")
    print(f"Total articles before filtering: {len(all_articles)}")
    
    # Apply relevance filtering
    filtered_articles = []
    for article in all_articles:
        if is_relevant_article(article['title'], article.get('abstract', '')):
            filtered_articles.append(article)
    
    print(f"Articles after relevance filtering: {len(filtered_articles)}")
    
    # Show some examples of what was filtered out (for debugging)
    filtered_out = [a for a in all_articles if a not in filtered_articles]
    if filtered_out and len(filtered_out) > 0:
        print(f"\nExample of filtered OUT articles (first 3):")
        for article in filtered_out[:3]:
            print(f"  - {article['title'][:80]}...")
    
    # Show some examples of what passed
    if filtered_articles and len(filtered_articles) > 0:
        print(f"\nExample of articles that PASSED filter (first 3):")
        for article in filtered_articles[:3]:
            print(f"  - {article['title'][:80]}...")
    
    # Deduplicate by title
    seen_titles = set()
    unique_articles = []
    
    for article in filtered_articles:
        title_lower = article['title'].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)
    
    print(f"Articles after deduplication: {len(unique_articles)}")
    
    # Sort by date (newest first), with priority sources first
    unique_articles.sort(
        key=lambda x: (not x.get('is_priority', False), x['pub_date']),
        reverse=True
    )
    
    # Take top 30 most recent
    final_articles = unique_articles[:30]
    
    print(f"\nFinal article count: {len(final_articles)}")
    print(f"  - From priority journals: {sum(1 for a in final_articles if a.get('is_priority'))}")
    print(f"  - From other journals: {sum(1 for a in final_articles if not a.get('is_priority'))}")
    
    if len(final_articles) == 0:
        print("\n⚠️  WARNING: No articles found. Feed will not be generated.")
        print("Consider:")
        print("  - Increasing DAYS_BACK (currently {})".format(DAYS_BACK))
        print("  - Relaxing filters in is_relevant_article()")
        print("  - Adding more search queries")
        return
    
    # Create RSS feed
    rss = create_rss_feed(final_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\n✓ RSS feed saved to: {OUTPUT_FILE}")
    print(f"✓ Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print sample titles
    print("\n=== Sample Articles in Feed ===")
    for i, article in enumerate(final_articles[:5], 1):
        priority = "⭐ " if article.get('is_priority') else "   "
        print(f"{i}. {priority}{article['authors']}")
        print(f"    {article['title'][:75]}...")
        print(f"    {article['journal']} ({article['pub_date'].year})\n")

if __name__ == '__main__':
    main()
