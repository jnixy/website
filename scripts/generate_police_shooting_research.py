#!/usr/bin/env python3
"""
Police Shooting Research RSS Feed Generator
Fetches recent academic publications about police shootings
IMPROVED VERSION - More comprehensive filtering
"""

import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import time

# Configuration
OUTPUT_FILE = 'static/data/police-shooting-research.xml'
DAYS_BACK = 180  # Check last 6 months (whitelisted journals publish less frequently on this topic)

# EXPANDED: Added more search query variations
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
    'law enforcement deadly force',  # NEW
    'police-involved fatalities',     # NEW
    'officer shootings',              # NEW
]

# Journal whitelist - only articles from these journals are included in the feed.
# Entries are matched case-insensitively with normalization (see is_whitelisted_journal).
WHITELISTED_JOURNALS = [
    # === CRIMINOLOGY / CRIMINAL JUSTICE ===
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
    'law and society review',
    'law & society review',
    'policing: an international journal',
    'policing: a journal of policy and practice',
    'journal of experimental criminology',
    'british journal of criminology',
    'the british journal of criminology',
    'journal of criminal law and criminology',
    'journal of criminal law & criminology',
    'journal of police and criminal psychology',
    'journal of police & criminal psychology',
    'criminal justice policy review',
    'international journal of police science and management',
    'international journal of police science & management',
    'law and human behavior',
    'law & human behavior',
    'theoretical criminology',
    'journal of crime and justice',
    'journal of crime & justice',
    'british journal of sociology',
    'the british journal of sociology',
    'criminology and criminal justice',
    'criminology & criminal justice',
    'journal of criminal justice education',
    'race and justice',
    'race & justice',

    # === PUBLIC POLICY ===
    'journal of policy analysis and management',
    'journal of policy analysis & management',
    'public administration review',
    'journal of public administration research and theory',
    'journal of public administration research & theory',
    'journal of politics',
    'the journal of politics',
    'political research quarterly',
    'policy studies journal',
    'perspectives on politics',
    'annual review of criminology',

    # === SOCIOLOGY / POLITICAL SCIENCE ===
    'american journal of sociology',
    'american sociological review',
    'american political science review',
    'american journal of political science',
    'social science & medicine',
    'social science and medicine',
    'social science research',
    'social science quarterly',
    'social forces',
    'social problems',

    # === PUBLIC HEALTH / MEDICAL ===
    'american journal of public health',
    'injury prevention',
    'jama',
    'the journal of the american medical association',
    'new england journal of medicine',
    'the new england journal of medicine',
    'the lancet',
    'lancet',
    'bmj',
    'the bmj',
    'british medical journal',
    'preventive medicine',
    'epidemiology',
    'journal of urban health',
    'annals of internal medicine',
    'american journal of epidemiology',
    'journal of trauma and acute care surgery',
    'journal of trauma & acute care surgery',
    'the lancet public health',
    'lancet public health',
    'bmj open',
    'annals of epidemiology',
    'journal of interpersonal violence',

    # === INTERDISCIPLINARY / GENERAL SCIENCE ===
    'plos one',
    'proceedings of the national academy of sciences',
    'proceedings of the national academy of sciences of the united states of america',
    'pnas',
    'nature human behaviour',
    'science advances',
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
    IMPROVED VERSION with more comprehensive term matching
    """
    if not title:
        return False
        
    text = (title + ' ' + (abstract or '')).lower()
    
    # EXPANDED: More comprehensive policing terms
    policing_terms = [
        'police', 'policing', 'law enforcement', 'cop', 'cops',
        'officer', 'officers',  # More permissive - no longer requires context
        'deputy', 'deputies',   # NEW
        'sheriff', 'sheriffs',  # NEW
        'trooper', 'troopers',  # NEW
    ]
    
    has_policing = any(term in text for term in policing_terms)
    
    # Special case: if no basic policing terms, check for law enforcement context
    if not has_policing:
        # Allow if clearly law enforcement context
        le_context = [
            'law enforcement agency', 'police department', 'police force',
            'patrol officer', 'sworn officer', 'peace officer'
        ]
        if any(context in text for context in le_context):
            has_policing = True
    
    if not has_policing:
        return False
    
    # MUST relate to force/violence/encounters
    # Split into tiers - need at least one from either tier
    
    # Tier 1: Explicit violence/force (strongest relevance)
    explicit_force = [
        'shooting', 'shot', 'deadly force', 'lethal force',
        'use of force', 'excessive force', 'violence', 'fatality',
        'killing', 'killed', 'death', 'homicide', 'fatal',
        'shoot', 'fired weapon', 'discharged weapon',
        'use-of-force',  # hyphenated variant
        'terminal force',  # NEW - academic term
        'civilian casualties',  # NEW
        'police-involved fatalities',  # NEW
    ]
    
    # Tier 2: Related concepts (still relevant but broader)
    # EXPANDED with more academic terminology
    related_force = [
        'firearm', 'gun', 'weapon', 'armed',
        'force continuum', 'de-escalation', 
        'encounter', 'incident', 'confrontation',
        'accountability', 'misconduct', 'brutality',
        'racial disparity', 'disparate impact',
        'coercive', 'coercion',  # NEW
        'use of physical force',  # NEW
        'force option',  # NEW
        'reasonable force',  # NEW
        'threat response',  # NEW
        'critical incident',  # NEW
        'officer-involved',  # NEW
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
        contemporary_terms = ['modern', 'contemporary', 'compared to', 'evolution', 'historical analysis']
        if not any(term in text for term in contemporary_terms):
            return False
    
    # RELAXED: More flexible international studies filter
    # Only exclude if clearly focused on a single non-U.S. country
    international_only_terms = [
        'german police', 'uk police', 'british police', 'canadian police',
        'australian police', 'european police', 'asian police',
        'french police', 'italian police', 'spanish police',
        'in germany', 'in britain', 'in canada', 'in australia',
        'in france', 'in italy', 'in spain'
    ]
    
    if any(term in text for term in international_only_terms):
        # EXPANDED: More flexible comparative indicators
        us_terms = [
            'united states', 'u.s.', 'us ', 'american', 'u.s. police',
            'cross-national', 'comparative', 'international comparison',
            'compared to', 'comparison of', 'across countries',  # NEW
            'multi-country', 'transnational',  # NEW
            'vs.', 'versus',  # NEW - catches "UK vs. US" style comparisons
        ]
        if not any(term in text for term in us_terms):
            return False
    
    # RELAXED: Only exclude fitness studies if they have NO force context
    if any(term in text for term in ['physical fitness', 'strength training', 'conditioning', 'tactical fitness']):
        # Must also mention force/violence context OR decision-making/training
        force_or_decision = explicit_force + ['training', 'decision', 'scenario', 'simulation']
        if not any(term in text for term in force_or_decision):
            return False
    
    return True

def normalize_journal_name(name):
    """Normalize a journal name for matching: lowercase, strip 'the', normalize ampersands."""
    if not name:
        return ''
    name = name.lower().strip()
    # Normalize HTML entities
    name = name.replace('&amp;', '&')
    # Collapse multiple spaces
    name = ' '.join(name.split())
    return name

def is_whitelisted_journal(source_name):
    """Check if article is from a whitelisted journal (normalized matching)."""
    if not source_name:
        return False
    normalized = normalize_journal_name(source_name)
    # Try exact match first
    if normalized in WHITELISTED_JOURNALS:
        return True
    # Try stripping leading "the "
    if normalized.startswith('the ') and normalized[4:] in WHITELISTED_JOURNALS:
        return True
    return False

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
    
    # Get authors (PubMed returns authors as dicts with 'name' key or as strings)
    raw_authors = item.get('authors', [])
    author_names = []
    for a in raw_authors[:3]:
        if isinstance(a, dict):
            author_names.append(a.get('name', 'Unknown'))
        else:
            author_names.append(str(a))
    authors = ', '.join(author_names)
    if len(raw_authors) > 3:
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
        
    return rss

def prettify_xml(elem):
    """Return a pretty-printed XML string"""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')

def main():
    """Main execution function"""
    print("=" * 70)
    print("Fetching police shooting research...")
    print(f"Searching back {DAYS_BACK} days")
    print("=" * 70)
    
    all_articles = []
    raw_count = 0

    # Fetch from Crossref
    print("\n=== Searching Crossref ===")
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_crossref(query)
        raw_count += len(items)
        print(f"         Found {len(items)} raw results")

        for item in items:
            article = parse_crossref_article(item)
            all_articles.append(article)

        time.sleep(1)  # Be nice to API

    crossref_count = raw_count

    # Fetch from PubMed (good for public health and medical journals)
    print("\n=== Searching PubMed ===")
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_pubmed(query)
        raw_count += len(items)
        print(f"         Found {len(items)} raw results")

        for item in items:
            article = parse_pubmed_article(item)
            all_articles.append(article)

        time.sleep(1)  # Be nice to API

    pubmed_count = raw_count - crossref_count

    print(f"\n{'=' * 70}")
    print(f"=== Filtering Results ===")
    print(f"Total raw articles from Crossref: {crossref_count}")
    print(f"Total raw articles from PubMed: {pubmed_count}")
    print(f"Total articles before filtering: {len(all_articles)}")
    
    # Apply relevance filtering
    filtered_articles = []
    for article in all_articles:
        if is_relevant_article(article['title'], article.get('abstract', '')):
            filtered_articles.append(article)

    print(f"Articles after relevance filtering: {len(filtered_articles)}")

    # Apply journal whitelist filter
    whitelisted_articles = [a for a in filtered_articles if is_whitelisted_journal(a['journal'])]
    excluded_by_whitelist = [a for a in filtered_articles if not is_whitelisted_journal(a['journal'])]

    print(f"Articles from whitelisted journals: {len(whitelisted_articles)}")
    print(f"Articles excluded by journal whitelist: {len(excluded_by_whitelist)}")

    # Show journals that were excluded (useful for identifying journals to add)
    if excluded_by_whitelist:
        excluded_journals = sorted(set(a['journal'] for a in excluded_by_whitelist))
        print(f"\nExcluded journals ({len(excluded_journals)} unique):")
        for j in excluded_journals[:10]:
            count = sum(1 for a in excluded_by_whitelist if a['journal'] == j)
            print(f"  - {j} ({count} article{'s' if count > 1 else ''})")
        if len(excluded_journals) > 10:
            print(f"  ... and {len(excluded_journals) - 10} more")

    # Show some examples of what passed
    if whitelisted_articles:
        print(f"\nExample of articles that PASSED filters (first 3):")
        for article in whitelisted_articles[:3]:
            print(f"  + {article['title'][:75]}...")
            print(f"    [{article['journal']}]")

    # Deduplicate by title
    seen_titles = set()
    unique_articles = []

    for article in whitelisted_articles:
        title_lower = article['title'].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_articles.append(article)

    print(f"Articles after deduplication: {len(unique_articles)}")

    # Sort by date (newest first)
    unique_articles.sort(key=lambda x: x['pub_date'], reverse=True)

    # Take top 30 most recent
    final_articles = unique_articles[:30]

    print(f"\n{'=' * 70}")
    print(f"Final article count: {len(final_articles)}")

    if len(final_articles) == 0:
        print("\nWARNING: No articles found. Feed will not be generated.")
        print("Consider:")
        print("  - Increasing DAYS_BACK (currently {})".format(DAYS_BACK))
        print("  - Adding more journals to WHITELISTED_JOURNALS")
        print("  - Adding more search queries")
        return
    
    # Create RSS feed
    rss = create_rss_feed(final_articles)
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    
    print(f"\n{'=' * 70}")
    print(f"RSS feed saved to: {OUTPUT_FILE}")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print sample titles
    print(f"\n{'=' * 70}")
    print("=== Sample Articles in Feed ===")
    for i, article in enumerate(final_articles[:8], 1):
        print(f"\n{i}. {article['authors']}")
        print(f"   {article['title']}")
        print(f"   {article['journal']} ({article['pub_date'].year})")
    
    print(f"\n{'=' * 70}")

if __name__ == '__main__':
    main()
