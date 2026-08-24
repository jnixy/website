#!/usr/bin/env python3
"""
Police Shooting Research Feed Generator
Fetches recent academic publications about police shootings and writes both
an RSS feed (static/data/police-shooting-research.xml) and a JSON sidecar
(static/data/police-shooting-research.json) consumed by the shared NewsFeed
front-end component (static/js/news-feed.js).
"""

import html
import json
import os
import re
import time
from datetime import datetime, timedelta

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
RSS_OUTPUT_FILE = 'static/data/police-shooting-research.xml'
JSON_OUTPUT_FILE = 'static/data/police-shooting-research.json'
DAYS_BACK = 180  # Check last 6 months (whitelisted journals publish less frequently on this topic)
REQUEST_TIMEOUT = 30

# The RSS feed is a short "what's new" subscription; the JSON file backs the
# on-page feed and keeps a longer rolling history so a single quiet/failed
# fetch never blanks the page (see MAX_JSON_ITEMS below).
MAX_RSS_ITEMS = 30
MAX_JSON_ITEMS = 100

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
    'law enforcement deadly force',
    'police-involved fatalities',
    'officer shootings',
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

# Flagship subset of the whitelist — articles from these get a "KEY JOURNAL"
# priority badge on the front end (matches this project's own target journals).
PRIORITY_JOURNALS = [
    'criminology',
    'criminology & public policy',
    'criminology and public policy',
    'justice quarterly',
    'journal of criminal justice',
    'police quarterly',
    'justice evaluation journal',
]

JATS_TAG_RE = re.compile(r'<[^>]+>')


def strip_jats_markup(text):
    """
    Crossref abstracts are often wrapped in JATS XML (<jats:p>, <jats:title>,
    etc). Strip tags so raw markup doesn't leak into the RSS description /
    get injected via innerHTML on the front end.
    """
    if not text:
        return ''
    stripped = JATS_TAG_RE.sub('', text)
    return ' '.join(stripped.split())


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
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
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
        search_response = requests.get(search_url, params=search_params, timeout=REQUEST_TIMEOUT)
        search_response.raise_for_status()
        search_data = search_response.json()

        id_list = search_data.get('esearchresult', {}).get('idlist', [])

        if not id_list:
            return []

        fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'json'
        }

        time.sleep(0.5)  # Be nice to NCBI servers

        fetch_response = requests.get(fetch_url, params=fetch_params, timeout=REQUEST_TIMEOUT)
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
    """
    if not title:
        return False

    text = (title + ' ' + (abstract or '')).lower()

    policing_terms = [
        'police', 'policing', 'law enforcement', 'cop', 'cops',
        'officer', 'officers',
        'deputy', 'deputies',
        'sheriff', 'sheriffs',
        'trooper', 'troopers',
    ]

    has_policing = any(term in text for term in policing_terms)

    if not has_policing:
        le_context = [
            'law enforcement agency', 'police department', 'police force',
            'patrol officer', 'sworn officer', 'peace officer'
        ]
        if any(context in text for context in le_context):
            has_policing = True

    if not has_policing:
        return False

    # Tier 1: Explicit violence/force (strongest relevance)
    explicit_force = [
        'shooting', 'shot', 'deadly force', 'lethal force',
        'use of force', 'excessive force', 'violence', 'fatality',
        'killing', 'killed', 'death', 'homicide', 'fatal',
        'shoot', 'fired weapon', 'discharged weapon',
        'use-of-force',
        'terminal force',
        'civilian casualties',
        'police-involved fatalities',
    ]

    # Tier 2: Related concepts (still relevant but broader)
    related_force = [
        'firearm', 'gun', 'weapon', 'armed',
        'force continuum', 'de-escalation',
        'encounter', 'incident', 'confrontation',
        'accountability', 'misconduct', 'brutality',
        'racial disparity', 'disparate impact',
        'coercive', 'coercion',
        'use of physical force',
        'force option',
        'reasonable force',
        'threat response',
        'critical incident',
        'officer-involved',
    ]

    has_force_terms = (
        any(term in text for term in explicit_force) or
        any(term in text for term in related_force)
    )

    if not has_force_terms:
        return False

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

    very_old_historical = [
        '18th century', '19th century', '1800s', '1700s',
        'victorian', 'colonial police', 'historical marine police'
    ]

    if any(term in text for term in very_old_historical):
        contemporary_terms = ['modern', 'contemporary', 'compared to', 'evolution', 'historical analysis']
        if not any(term in text for term in contemporary_terms):
            return False

    international_only_terms = [
        'german police', 'uk police', 'british police', 'canadian police',
        'australian police', 'european police', 'asian police',
        'french police', 'italian police', 'spanish police',
        'in germany', 'in britain', 'in canada', 'in australia',
        'in france', 'in italy', 'in spain'
    ]

    if any(term in text for term in international_only_terms):
        us_terms = [
            'united states', 'u.s.', 'us ', 'american', 'u.s. police',
            'cross-national', 'comparative', 'international comparison',
            'compared to', 'comparison of', 'across countries',
            'multi-country', 'transnational',
            'vs.', 'versus',
        ]
        if not any(term in text for term in us_terms):
            return False

    if any(term in text for term in ['physical fitness', 'strength training', 'conditioning', 'tactical fitness']):
        force_or_decision = explicit_force + ['training', 'decision', 'scenario', 'simulation']
        if not any(term in text for term in force_or_decision):
            return False

    return True


def normalize_journal_name(name):
    """Normalize a journal name for matching: lowercase, strip 'the', normalize ampersands."""
    if not name:
        return ''
    name = name.lower().strip()
    name = name.replace('&amp;', '&')
    name = ' '.join(name.split())
    return name


def is_whitelisted_journal(source_name):
    """Check if article is from a whitelisted journal (normalized matching)."""
    normalized = normalize_journal_name(source_name)
    if not normalized:
        return False
    if normalized in WHITELISTED_JOURNALS:
        return True
    if normalized.startswith('the ') and normalized[4:] in WHITELISTED_JOURNALS:
        return True
    return False


def is_priority_journal(source_name):
    """Check if article is from a flagship journal (gets the KEY JOURNAL badge)."""
    normalized = normalize_journal_name(source_name)
    if not normalized:
        return False
    if normalized in PRIORITY_JOURNALS:
        return True
    if normalized.startswith('the ') and normalized[4:] in PRIORITY_JOURNALS:
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
    """Parse Crossref article into this script's canonical story shape"""
    # Crossref titles occasionally carry inline markup (e.g. <i> around a
    # media title) plus stray whitespace/newlines — strip_jats_markup both
    # strips tags and collapses whitespace, so it doubles as a title cleaner.
    title = item.get('title', ['Untitled'])[0] if item.get('title') else 'Untitled'
    title = strip_jats_markup(title) or 'Untitled'

    doi = item.get('DOI', '')
    url = f"https://doi.org/{doi}" if doi else item.get('URL', '')

    pub_date_parts = item.get('published', {}).get('date-parts', [[]])[0]
    if pub_date_parts:
        pub_date = datetime(pub_date_parts[0],
                             pub_date_parts[1] if len(pub_date_parts) > 1 else 1,
                             pub_date_parts[2] if len(pub_date_parts) > 2 else 1)
    else:
        pub_date = datetime.now()

    journal = item.get('container-title', ['Unknown Journal'])[0] if item.get('container-title') else 'Unknown Journal'
    authors = format_authors(item.get('author', []))
    abstract = strip_jats_markup(item.get('abstract', ''))
    article_type = item.get('type', 'journal-article')

    # Crossref sometimes returns literal HTML entities (e.g. "&amp;") baked
    # into title/journal text rather than the actual character. Unescape
    # once here so the front end's HTML-escaping doesn't double-escape it.
    title = html.unescape(title)
    journal = html.unescape(journal)
    authors = html.unescape(authors)
    abstract = html.unescape(abstract)

    return {
        'title': title,
        'url': url,
        'date': pub_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'journal': journal,
        'authors': authors,
        'abstract': abstract,
        'type': article_type,
        'doi': doi,
        'priority': is_priority_journal(journal),
    }


def parse_pubmed_article(item):
    """Parse PubMed article into this script's canonical story shape"""
    title = html.unescape(item.get('title', 'Untitled'))

    pmid = item.get('uid', '')
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ''

    pub_date_str = item.get('pubdate', '')
    try:
        pub_date = datetime.strptime(pub_date_str, '%Y %b %d')
    except Exception:
        pub_date = datetime.now()

    journal = html.unescape(item.get('source', 'Unknown Journal'))

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
        'date': pub_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'journal': journal,
        'authors': authors,
        # PubMed's esummary endpoint doesn't return abstracts (would need
        # efetch for that) — left blank, a known source limitation.
        'abstract': '',
        'type': 'journal-article',
        'doi': '',
        'priority': is_priority_journal(journal),
    }


def load_previous_stories(json_path):
    """Load stories written by a previous run so a quiet/failed fetch never
    wipes the page — new results are merged on top of this history."""
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
    """Combine previous and newly-fetched stories, deduplicated by DOI/URL
    (falling back to lowercase title), newest first."""
    seen_keys = set()
    seen_titles = set()
    merged = []

    for story in list(new_stories) + list(previous):
        key = story.get('doi') or story.get('url', '')
        title_key = (story.get('title') or '').lower()
        if key and key in seen_keys:
            continue
        if title_key and title_key in seen_titles:
            continue
        if key:
            seen_keys.add(key)
        if title_key:
            seen_titles.add(title_key)
        merged.append(story)

    merged.sort(key=lambda s: s.get('date', ''), reverse=True)
    return merged


def create_rss_feed(stories):
    """Create RSS 2.0 feed from a list of story dicts"""

    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = ET.SubElement(rss, 'channel')

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

    for story in stories:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        item_title.text = story['title']

        item_link = ET.SubElement(item, 'link')
        item_link.text = story['url']

        desc_parts = []
        if story.get('authors'):
            desc_parts.append(f"<strong>Authors:</strong> {story['authors']}")
        if story.get('journal'):
            desc_parts.append(f"<strong>Journal:</strong> {story['journal']}")
        if story.get('abstract'):
            desc_parts.append(f"<p>{story['abstract'][:500]}...</p>")

        item_desc = ET.SubElement(item, 'description')
        item_desc.text = '<br>'.join(desc_parts)

        pub_date = ET.SubElement(item, 'pubDate')
        try:
            dt = datetime.strptime(story['date'], '%Y-%m-%dT%H:%M:%SZ')
            pub_date.text = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        except Exception:
            pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

        item_category = ET.SubElement(item, 'category')
        item_category.text = 'research'

        item_source = ET.SubElement(item, 'source')
        item_source.text = story.get('journal', 'Academic Journal')

        item_priority = ET.SubElement(item, 'priority')
        item_priority.text = 'true' if story.get('priority') else 'false'

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

    print("\n=== Searching Crossref ===")
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_crossref(query)
        raw_count += len(items)
        print(f"         Found {len(items)} raw results")

        for item in items:
            all_articles.append(parse_crossref_article(item))

        time.sleep(1)  # Be nice to API

    crossref_count = raw_count

    print("\n=== Searching PubMed ===")
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_pubmed(query)
        raw_count += len(items)
        print(f"         Found {len(items)} raw results")

        for item in items:
            all_articles.append(parse_pubmed_article(item))

        time.sleep(1)  # Be nice to API

    pubmed_count = raw_count - crossref_count

    print(f"\n{'=' * 70}")
    print("=== Filtering Results ===")
    print(f"Total raw articles from Crossref: {crossref_count}")
    print(f"Total raw articles from PubMed: {pubmed_count}")
    print(f"Total articles before filtering: {len(all_articles)}")

    filtered_articles = [
        a for a in all_articles
        if is_relevant_article(a['title'], a.get('abstract', ''))
    ]

    print(f"Articles after relevance filtering: {len(filtered_articles)}")

    whitelisted_articles = [a for a in filtered_articles if is_whitelisted_journal(a['journal'])]
    excluded_by_whitelist = [a for a in filtered_articles if not is_whitelisted_journal(a['journal'])]

    print(f"Articles from whitelisted journals: {len(whitelisted_articles)}")
    print(f"Articles excluded by journal whitelist: {len(excluded_by_whitelist)}")

    if excluded_by_whitelist:
        excluded_journals = sorted(set(a['journal'] for a in excluded_by_whitelist))
        print(f"\nExcluded journals ({len(excluded_journals)} unique):")
        for j in excluded_journals[:10]:
            count = sum(1 for a in excluded_by_whitelist if a['journal'] == j)
            print(f"  - {j} ({count} article{'s' if count > 1 else ''})")
        if len(excluded_journals) > 10:
            print(f"  ... and {len(excluded_journals) - 10} more")

    if whitelisted_articles:
        print("\nExample of articles that PASSED filters (first 3):")
        for article in whitelisted_articles[:3]:
            print(f"  + {article['title'][:75]}...")
            print(f"    [{article['journal']}]")

    # Dedupe within this run by title
    seen_titles = set()
    new_stories = []
    for article in whitelisted_articles:
        title_lower = article['title'].lower()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            new_stories.append(article)

    print(f"New stories this run (deduped): {len(new_stories)}")

    if len(new_stories) == 0:
        print("\nWARNING: No new articles found this run. Consider:")
        print(f"  - Increasing DAYS_BACK (currently {DAYS_BACK})")
        print("  - Adding more journals to WHITELISTED_JOURNALS")
        print("  - Adding more search queries")
        print("Falling back to previously published stories so the page isn't wiped.")

    # Merge with history so a quiet/failed run never blanks the page
    previous_stories = load_previous_stories(JSON_OUTPUT_FILE)
    merged_stories = merge_stories(previous_stories, new_stories)

    print(f"\n{'=' * 70}")
    print(f"Total stories after merge with history: {len(merged_stories)}")

    if len(merged_stories) == 0:
        print("\nERROR: No stories available (first run with no fetch results). Nothing to write.")
        return

    json_stories = merged_stories[:MAX_JSON_ITEMS]
    rss_stories = merged_stories[:MAX_RSS_ITEMS]

    os.makedirs(os.path.dirname(JSON_OUTPUT_FILE), exist_ok=True)
    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'stories': json_stories,
        }, f, indent=2, ensure_ascii=False)
    print(f"JSON feed saved to: {JSON_OUTPUT_FILE} ({len(json_stories)} stories)")

    rss = create_rss_feed(rss_stories)
    os.makedirs(os.path.dirname(RSS_OUTPUT_FILE), exist_ok=True)
    with open(RSS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(prettify_xml(rss))
    print(f"RSS feed saved to: {RSS_OUTPUT_FILE} ({len(rss_stories)} items)")

    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n{'=' * 70}")
    print("=== Sample Articles in Feed ===")
    for i, story in enumerate(json_stories[:8], 1):
        print(f"\n{i}. {story['authors']}")
        print(f"   {story['title']}")
        print(f"   {story['journal']} ({story['date'][:4]})")

    print(f"\n{'=' * 70}")


if __name__ == '__main__':
    main()
