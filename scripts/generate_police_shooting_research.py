#!/usr/bin/env python3
"""
Police Shooting Research Feed Generator
Fetches recent academic publications about police shootings and writes both
an RSS feed (static/data/police-shooting-research.xml) and a JSON sidecar
(static/data/police-shooting-research.json) consumed by the shared NewsFeed
front-end component (static/js/news-feed.js).

Discovery sources:
  - OpenAlex (primary) -- title/abstract search, reconstructable abstracts,
    reliable publication dates. Free, no key; polite pool via mailto.
  - PubMed E-utilities (backup) -- esearch + efetch for medical/public-health
    coverage. efetch (not esummary) so abstracts come back populated.

Crossref was removed: its `sort=published` query floated fake-future-dated
books/chapters (e.g. [2050,4,21]) to the top of every result page, so real
journal articles never survived to the filter stage. OpenAlex ingests the
same Crossref metadata anyway.

Usage:
  python scripts/generate_police_shooting_research.py               # 180-day window
  python scripts/generate_police_shooting_research.py --days-back 365
  python scripts/generate_police_shooting_research.py --backfill     # ~3-year window (one-off)
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta

import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
RSS_OUTPUT_FILE = 'static/data/police-shooting-research.xml'
JSON_OUTPUT_FILE = 'static/data/police-shooting-research.json'
DAYS_BACK = 180  # Check last 6 months (whitelisted journals publish less frequently on this topic)
BACKFILL_DAYS = 1095  # ~3 years, used only for the one-off --backfill history seed
REQUEST_TIMEOUT = 30
OPENALEX_MAX_PAGES = 3  # per-query safety cap on cursor pagination (200 records/page)
CONTACT_EMAIL = 'jnix@unomaha.edu'  # OpenAlex/Crossref polite-pool identity

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
# One canonical spelling per journal: no leading "the", write "and" or "&"
# however you like, punctuation optional -- normalize_journal_name() folds all
# of those so incoming names from any source match regardless of house style.
_WHITELISTED_JOURNALS_BASE = [
    # === CRIMINOLOGY / CRIMINAL JUSTICE ===
    'criminology',
    'criminology & public policy',
    'justice quarterly',
    'journal of criminal justice',
    'police quarterly',
    'journal of research in crime and delinquency',
    'journal of quantitative criminology',
    'criminal justice and behavior',
    'crime & delinquency',
    'justice evaluation journal',
    'policing and society',
    'police practice & research',
    'law and society review',
    'policing: an international journal',
    'policing: a journal of policy and practice',
    'journal of experimental criminology',
    'british journal of criminology',
    'journal of criminal law and criminology',
    'journal of police and criminal psychology',
    'criminal justice policy review',
    'international journal of police science and management',
    'law and human behavior',
    'theoretical criminology',
    'journal of crime and justice',
    'british journal of sociology',
    'criminology and criminal justice',
    'journal of criminal justice education',
    'race and justice',
    'critical criminology',
    'homicide studies',
    'journal of criminology',
    'deviant behavior',
    'aggression and violent behavior',
    'journal of ethnicity in criminal justice',

    # === PUBLIC POLICY ===
    'journal of policy analysis and management',
    'public administration review',
    'journal of public administration research and theory',
    'journal of politics',
    'political research quarterly',
    'policy studies journal',
    'perspectives on politics',
    'annual review of criminology',
    'health affairs',

    # === SOCIOLOGY / POLITICAL SCIENCE ===
    'american journal of sociology',
    'american sociological review',
    'american political science review',
    'american journal of political science',
    'social science & medicine',
    'social science research',
    'social science quarterly',
    'social forces',
    'social problems',
    'social currents',
    'du bois review: social science research on race',
    'city & community',

    # === PUBLIC HEALTH / MEDICAL ===
    'american journal of public health',
    'american journal of preventive medicine',
    'injury prevention',
    'injury epidemiology',
    'jama',
    'jama network open',
    'jama internal medicine',
    'jama pediatrics',
    'jama surgery',
    'new england journal of medicine',
    'the lancet',
    'the lancet public health',
    'the lancet regional health - americas',
    'bmj',
    'bmj open',
    'preventive medicine',
    'preventive medicine reports',
    'epidemiology',
    'journal of urban health',
    'annals of internal medicine',
    'american journal of epidemiology',
    'annals of epidemiology',
    'journal of trauma and acute care surgery',
    'journal of interpersonal violence',
    'journal of racial and ethnic health disparities',
    'ssm - population health',
    'plos global public health',
    'journal of public health',

    # === INTERDISCIPLINARY / GENERAL SCIENCE ===
    'plos one',
    'proceedings of the national academy of sciences',
    'nature',
    'nature human behaviour',
    'science advances',
]

# Flagship subset of the whitelist -- articles from these get a "KEY JOURNAL"
# priority badge on the front end (matches this project's own target journals).
_PRIORITY_JOURNALS_BASE = [
    'criminology',
    'criminology & public policy',
    'justice quarterly',
    'journal of criminal justice',
    'police quarterly',
    'justice evaluation journal',
]

JATS_TAG_RE = re.compile(r'<[^>]+>')

# PubMed publication types that mark an item as non-research (reviews included,
# per the topical-tightening decision) -- any hit drops the record.
PUBMED_EXCLUDE_TYPES = {
    'Review', 'Systematic Review', 'Meta-Analysis', 'Editorial', 'Comment',
    'News', 'Letter', 'Published Erratum', 'Retraction of Publication',
    'Biography', 'Historical Article', 'Newspaper Article', 'Interview',
}


def normalize_journal_name(name):
    """
    Normalize a journal name for whitelist matching. Folds the cosmetic
    differences between how OpenAlex, PubMed and Crossref render the same
    title: case, a leading "The", "and" vs "&", punctuation, dash style,
    and whitespace.
    """
    if not name:
        return ''
    name = name.lower().strip()
    name = name.replace('&amp;', '&')
    name = name.replace('–', '-').replace('—', '-')  # en/em dash -> hyphen
    name = re.sub(r'\s*-\s*', ' - ', name)           # consistent spacing around hyphens
    name = re.sub(r'\band\b', '&', name)             # "and" -> "&"
    name = re.sub(r'[:.,]', '', name)                # drop separating punctuation
    name = ' '.join(name.split())
    if name.startswith('the '):
        name = name[4:]
    return name


WHITELISTED_JOURNALS = {normalize_journal_name(j) for j in _WHITELISTED_JOURNALS_BASE}
PRIORITY_JOURNALS = {normalize_journal_name(j) for j in _PRIORITY_JOURNALS_BASE}


def strip_jats_markup(text):
    """
    Crossref/OpenAlex abstracts are often wrapped in JATS XML (<jats:p>,
    <jats:title>, etc). Strip tags so raw markup doesn't leak into the RSS
    description / get injected via innerHTML on the front end.
    """
    if not text:
        return ''
    stripped = JATS_TAG_RE.sub('', text)
    return ' '.join(stripped.split())


def reconstruct_abstract(inv_index):
    """
    OpenAlex returns abstracts as an inverted index ({word: [positions...]})
    rather than plain text. Rebuild the running text from it. Returns '' when
    the index is missing -- some publishers (e.g. Elsevier) forbid abstract
    redistribution, so a minority of records legitimately have none.
    """
    if not inv_index:
        return ''
    positions = []
    for word, idxs in inv_index.items():
        for i in idxs:
            positions.append((i, word))
    text = ' '.join(word for _, word in sorted(positions))
    return strip_jats_markup(html.unescape(text))


RETRY_MAX_WAIT = 60  # seconds -- a longer Retry-After means a real quota/outage; fail loud instead


def get_with_retry(url, params=None, headers=None, max_attempts=4):
    """
    GET with exponential backoff on transient failures (429 rate-limit, 5xx,
    connection errors). Honors a Retry-After header up to RETRY_MAX_WAIT; a
    request to wait longer than that is a genuine quota exhaustion / outage, so
    we re-raise immediately rather than sleep for hours. Re-raises the last
    error after max_attempts so the caller can still fail loud.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            retry_after = 0
            resp = getattr(e, 'response', None)
            if resp is not None:
                try:
                    retry_after = int(resp.headers.get('Retry-After', 0))
                except (TypeError, ValueError):
                    retry_after = 0
            if attempt == max_attempts or retry_after > RETRY_MAX_WAIT:
                raise
            wait = min(max(retry_after, 2 ** attempt), RETRY_MAX_WAIT)
            print(f"         transient fetch error ({e}); retry {attempt}/{max_attempts - 1} in {wait}s")
            time.sleep(wait)


def fetch_openalex(query, days_back=DAYS_BACK):
    """
    Fetch articles from OpenAlex (free, no key required; polite pool via mailto).
    Docs: https://docs.openalex.org

    Uses the title_and_abstract.search filter (topical match) plus a bounded
    publication-date window. to_publication_date pins the upper bound so
    fake-future-dated records can't slip in.
    """
    url = 'https://api.openalex.org/works'

    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')

    filters = ','.join([
        f'from_publication_date:{from_date}',
        f'to_publication_date:{to_date}',
        'type:article',        # research articles only -- no reviews/editorials/paratext
        'is_paratext:false',
        f'title_and_abstract.search:{query}',
    ])

    params = {
        'filter': filters,
        'select': 'id,doi,title,display_name,publication_date,authorships,primary_location,abstract_inverted_index,type',
        'per_page': 200,
        'mailto': CONTACT_EMAIL,
        'cursor': '*',
    }

    results = []
    for _ in range(OPENALEX_MAX_PAGES):
        response = get_with_retry(url, params=params)
        data = response.json()

        results.extend(data.get('results', []))

        next_cursor = data.get('meta', {}).get('next_cursor')
        if not next_cursor or not data.get('results'):
            break
        params['cursor'] = next_cursor
        time.sleep(1)  # Be nice to the API between pages

    return results


def fetch_pubmed(query, days_back=DAYS_BACK):
    """
    Fetch articles from PubMed (free, no key required for basic searches).
    Good for public health and medical journals.

    esearch returns the PMID list; efetch (rettype=abstract, retmode=xml)
    returns the full records *including abstracts* -- esummary does not, which
    used to leave every PubMed article with a blank abstract and get it
    silently dropped by is_relevant_article.
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

    search_response = get_with_retry(search_url, params=search_params)
    id_list = search_response.json().get('esearchresult', {}).get('idlist', [])

    if not id_list:
        return []

    fetch_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    fetch_params = {
        'db': 'pubmed',
        'id': ','.join(id_list),
        'rettype': 'abstract',
        'retmode': 'xml',
    }

    time.sleep(0.5)  # Be nice to NCBI servers

    fetch_response = get_with_retry(fetch_url, params=fetch_params)

    root = ET.fromstring(fetch_response.content)
    articles = []
    for art in root.findall('.//PubmedArticle'):
        parsed = _parse_pubmed_xml(art)
        if PUBMED_EXCLUDE_TYPES.intersection(parsed.pop('pub_types', ())):
            continue
        articles.append(parsed)
    return articles


def _parse_pubmed_xml(art):
    """Flatten one <PubmedArticle> element into a plain dict for parse_pubmed_article()."""
    def text_of(el):
        return ''.join(el.itertext()).strip() if el is not None else ''

    pmid = text_of(art.find('.//MedlineCitation/PMID'))
    title = text_of(art.find('.//Article/ArticleTitle'))

    abstract_parts = [text_of(node) for node in art.findall('.//Abstract/AbstractText')]
    abstract = ' '.join(part for part in abstract_parts if part)

    journal = text_of(art.find('.//Article/Journal/Title'))

    pub_date_el = art.find('.//Article/Journal/JournalIssue/PubDate')
    pubdate = ''
    if pub_date_el is not None:
        year = text_of(pub_date_el.find('Year'))
        month = text_of(pub_date_el.find('Month'))
        day = text_of(pub_date_el.find('Day'))
        if year:
            pubdate = ' '.join(p for p in (year, month, day) if p)
        else:
            pubdate = text_of(pub_date_el.find('MedlineDate'))

    authors = []
    for author in art.findall('.//Article/AuthorList/Author'):
        collective = text_of(author.find('CollectiveName'))
        if collective:
            authors.append(collective)
            continue
        last = text_of(author.find('LastName'))
        fore = text_of(author.find('ForeName'))
        name = ' '.join(p for p in (fore, last) if p)
        if name:
            authors.append(name)

    doi = ''
    for el in art.findall('.//ELocationID[@EIdType="doi"]') + art.findall('.//ArticleId[@IdType="doi"]'):
        if el.text:
            doi = el.text.strip().lower()
            break

    pub_types = [text_of(pt) for pt in art.findall('.//PublicationTypeList/PublicationType')]

    return {
        'pmid': pmid,
        'title': title,
        'abstract': abstract,
        'journal': journal,
        'pubdate': pubdate,
        'authors': authors,
        'doi': doi,
        'pub_types': pub_types,
    }


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

    # Topical gate: the article must be *about* police force/violence/oversight,
    # not merely mention police and violence in separate breaths. Drops
    # burden-of-disease reviews, victimization studies that only use police
    # records as a data source, media-portrayal essays, etc.
    core_topic_terms = [
        'police shooting', 'police-involved shooting', 'police involved shooting',
        'officer-involved shooting', 'officer involved shooting',
        'shooting by police', 'shootings by police', 'shot by police',
        'shot by an officer', 'shot by officers', 'police shot', 'police opened fire',
        'police use of force', 'police uses of force', 'use of force by police',
        'police use-of-force', 'use-of-force by police', 'officer use of force',
        'police violence', 'police brutality', 'police aggression',
        'police misconduct', 'officer misconduct', 'police wrongdoing',
        'police accountability', 'police oversight', 'police discipline',
        'disciplinary', 'civilian complaint', 'citizen complaint',
        'early intervention system', 'early warning system',
        'police killing', 'killed by police', 'killing by police', 'killings by police',
        'police-caused', 'police caused', 'police homicide', 'police-related death',
        'police related death', 'police-related fatalit', 'police-involved death',
        'police involved death', 'died after police', 'death after police contact',
        'fatal police', 'fatal encounter', 'fatal force', 'fatal shooting',
        'fatal officer', 'fatally shot',
        'deadly force', 'lethal force', 'terminal force', 'excessive force',
        'unreasonable force', 'unjustified force', 'use of deadly force',
        'use of lethal force',
        'police pursuit', 'police chase', 'vehicular pursuit', 'vehicle pursuit',
        'high-speed pursuit', 'high speed pursuit',
        'police custody', 'in-custody death', 'in custody death',
        'arrest-related death', 'arrest related death', 'deaths in custody',
        'legal intervention',  # ICD / NVDRS cause-of-death term
        'law enforcement homicide', 'law enforcement-related death',
        'law enforcement related death', 'officer-involved',
        'body-worn camera', 'body worn camera', 'body-cam', 'bodycam',
        'less-lethal', 'less lethal', 'conducted energy', 'taser',
        'chemical agent', 'police dog bite', 'canine bite',
        'police firearm', 'firearm discharge by', 'discharge of a firearm by',
        'shots fired by', 'weapon discharge by',
        'assault on police', 'assaults on police', 'assaulted officer',
        'attacks on police', 'attack on police', 'officers assaulted',
        'officers feloniously', 'feloniously killed', 'line-of-duty death',
        'line of duty death', 'officer fatalit', 'killing of police officer',
        'killing of law enforcement', 'ambush of police',
        'suicide by cop', 'suicide-by-cop',
        'stop and frisk', 'stop-and-frisk', 'investigative stop', 'pedestrian stop',
        'traffic stop',
    ]

    if not any(term in text for term in core_topic_terms):
        return False

    non_research_prefixes = (
        'correction to', 'corrigendum', 'erratum', 'retraction',
        'editorial:', 'editorial ', 'commentary on', 'comment on',
        'reply to', 'response to', 'author response', 'in this issue',
        'book review', 'review of the book', 'in memoriam', 'obituary',
        'introduction to the special issue', 'guest editorial',
    )
    if title.lower().strip().startswith(non_research_prefixes):
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


def is_whitelisted_journal(source_name):
    """Check if article is from a whitelisted journal (normalized matching)."""
    return normalize_journal_name(source_name) in WHITELISTED_JOURNALS


def is_priority_journal(source_name):
    """Check if article is from a flagship journal (gets the KEY JOURNAL badge)."""
    return normalize_journal_name(source_name) in PRIORITY_JOURNALS


def format_name_list(names):
    """Format a list of already-rendered author name strings (OpenAlex/PubMed)."""
    names = [n for n in names if n]
    if not names:
        return "Unknown Authors"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{names[0]} et al."


def format_openalex_authors(authorships):
    """Pull display names out of an OpenAlex authorships list and format them."""
    names = []
    for a in authorships:
        author = a.get('author') or {}
        name = author.get('display_name')
        if name:
            names.append(name)
    return format_name_list(names)


def parse_openalex_article(work):
    """Parse an OpenAlex work into this script's canonical story shape."""
    title = work.get('title') or work.get('display_name') or 'Untitled'
    title = html.unescape(strip_jats_markup(title)) or 'Untitled'

    doi = (work.get('doi') or '').replace('https://doi.org/', '').lower()
    url = f"https://doi.org/{doi}" if doi else work.get('id', '')

    try:
        pub_date = datetime.strptime(work.get('publication_date', ''), '%Y-%m-%d')
    except (ValueError, TypeError):
        pub_date = datetime.now()

    source = ((work.get('primary_location') or {}).get('source')) or {}
    journal = html.unescape(source.get('display_name') or 'Unknown Journal')

    return {
        'title': title,
        'url': url,
        'date': pub_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'journal': journal,
        'authors': format_openalex_authors(work.get('authorships', [])),
        'abstract': reconstruct_abstract(work.get('abstract_inverted_index')),
        'type': work.get('type', 'journal-article'),
        'doi': doi,
        'priority': is_priority_journal(journal),
    }


def parse_pubmed_article(item):
    """Parse the flattened PubMed dict from _parse_pubmed_xml into the canonical shape."""
    title = html.unescape(strip_jats_markup(item.get('title', ''))) or 'Untitled'

    doi = item.get('doi', '')
    pmid = item.get('pmid', '')
    if doi:
        url = f"https://doi.org/{doi}"
    elif pmid:
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    else:
        url = ''

    raw_pubdate = (item.get('pubdate') or '').strip()
    # PubMed PubDate comes in many shapes: "2026 Aug 15", "2026 Aug", "2026",
    # "2026 08 15", or a MedlineDate like "2026 Jul-Aug". Take the year at least.
    pub_date = None
    for fmt in ('%Y %b %d', '%Y %b', '%Y %m %d', '%Y %m', '%Y'):
        try:
            pub_date = datetime.strptime(raw_pubdate, fmt)
            break
        except ValueError:
            continue
    if pub_date is None:
        year_match = re.match(r'\s*(\d{4})', raw_pubdate)
        pub_date = datetime(int(year_match.group(1)), 1, 1) if year_match else datetime.now()

    journal = html.unescape(item.get('journal') or 'Unknown Journal')

    return {
        'title': title,
        'url': url,
        'date': pub_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'journal': journal,
        'authors': format_name_list(item.get('authors', [])),
        'abstract': html.unescape(strip_jats_markup(item.get('abstract', ''))),
        'type': 'journal-article',
        'doi': doi,
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


def _title_key(title):
    """Loose title key for dedup: lowercase, strip accents of punctuation and
    trailing periods so the same paper matches across OpenAlex/PubMed even when
    one source keeps a trailing '.' or renders a subtitle colon differently."""
    return re.sub(r'[^a-z0-9]+', ' ', (title or '').lower()).strip()


def merge_stories(previous, new_stories):
    """Combine previous and newly-fetched stories, deduplicated by DOI/URL
    (falling back to a normalized title key), newest first. New stories are
    considered first, so a fresher source (OpenAlex) wins over a stale
    duplicate (e.g. a PubMed record with an entry-date masquerading as the
    publication date)."""
    seen_keys = set()
    seen_titles = set()
    merged = []

    for story in list(new_stories) + list(previous):
        key = story.get('doi') or story.get('url', '')
        title_key = _title_key(story.get('title'))
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
    title.text = 'Police Shooting Research Tracker'

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


def collect_articles(days_back):
    """Run every source against every query and return parsed (uncanonicalized-
    filter) story dicts. Raises on any HTTP/parse failure so main() can fail loud."""
    all_articles = []
    source_counts = {}

    print("\n=== Searching OpenAlex ===")
    openalex_raw = 0
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_openalex(query, days_back)
        openalex_raw += len(items)
        print(f"         Found {len(items)} raw results")
        for item in items:
            all_articles.append(parse_openalex_article(item))
        time.sleep(1)  # Be nice to the API
    source_counts['OpenAlex'] = openalex_raw

    print("\n=== Searching PubMed ===")
    pubmed_raw = 0
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"[{i}/{len(SEARCH_QUERIES)}] Query: {query}")
        items = fetch_pubmed(query, days_back)
        pubmed_raw += len(items)
        print(f"         Found {len(items)} raw results")
        for item in items:
            all_articles.append(parse_pubmed_article(item))
        time.sleep(1)  # Be nice to the API
    source_counts['PubMed'] = pubmed_raw

    return all_articles, source_counts


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days-back', type=int, default=DAYS_BACK,
                        help=f'Publication-date window in days (default: {DAYS_BACK})')
    parser.add_argument('--backfill', action='store_true',
                        help=f'One-off wide window ({BACKFILL_DAYS} days) to seed history')
    args = parser.parse_args()

    days_back = BACKFILL_DAYS if args.backfill else args.days_back

    print("=" * 70)
    print("Fetching police shooting research...")
    print(f"Searching back {days_back} days" + (" [BACKFILL]" if args.backfill else ""))
    print("=" * 70)

    # Fail loud: a network/parse error must stop the run *before* any file
    # write, so a transient outage can't overwrite the last good feed.
    try:
        all_articles, source_counts = collect_articles(days_back)
    except (requests.RequestException, ET.ParseError) as e:
        print(f"\nERROR: source fetch failed ({e}). Aborting without touching the feed files.")
        sys.exit(1)

    print(f"\n{'=' * 70}")
    print("=== Filtering Results ===")
    for source, count in source_counts.items():
        print(f"Total raw articles from {source}: {count}")
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

    # Dedupe within this run by DOI then normalized title (a paper can arrive
    # from both OpenAlex and PubMed in the same run).
    seen_dois = set()
    seen_titles = set()
    new_stories = []
    for article in whitelisted_articles:
        doi = article.get('doi', '')
        title_key = _title_key(article['title'])
        if doi and doi in seen_dois:
            continue
        if title_key and title_key in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        seen_titles.add(title_key)
        new_stories.append(article)

    print(f"New stories this run (deduped): {len(new_stories)}")

    if len(new_stories) == 0:
        print("\nWARNING: No new articles found this run. Consider:")
        print(f"  - Increasing the search window (currently {days_back} days)")
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
