#!/usr/bin/env python3
"""
Mapping Police Violence Dashboard Data Generator

Downloads the public Mapping Police Violence (MPV) dataset and writes the
aggregates JSON that powers a client-side charts dashboard
(content/police-shooting-dashboard/_index.md + static/js/mpv-dashboard.js):

- static/data/mpv-dashboard.json   -- aggregates only (small, page-load-friendly)

Visitors who want the full incident-level dataset are linked directly to
mappingpoliceviolence.us rather than us re-publishing a raw-data mirror here.

Source: https://mappingpoliceviolence.us (methodology: /aboutthedata)
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import requests

MPV_URL = 'https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx'
MPV_SHEET = '2013-2026 Police Killings'
MPV_STATE_SHEET = '2013-2026 Killings by State'
REQUEST_TIMEOUT = 60

DASHBOARD_OUTPUT_FILE = 'static/data/mpv-dashboard.json'

# Column names in the source workbook, kept as constants so a schema change
# upstream is a one-line fix instead of a search-and-replace.
COL_DATE = 'Date of Incident (month/day/year)'
COL_STATE = 'State'
COL_RACE = "Victim's race"
COL_ARMED = 'Armed/Unarmed Status'
COL_AGENCY = 'Agency responsible for death'
COL_CAUSE = 'Cause of death'
COL_ENCOUNTER = 'Encounter Type'
COL_WEAPON = 'Alleged Weapon (Source: WaPo and Review of Cases Not Included in WaPo Database)'

REQUIRED_COLUMNS = [
    COL_DATE, COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY, COL_CAUSE,
    COL_ENCOUNTER, COL_WEAPON,
]

# Population-by-race columns on the "Killings by State" sheet. We only use
# these (population context, cause-agnostic) -- never that sheet's own
# Rate/Disparity columns, which are computed over MPV's all-cause killings
# total and would silently break this dashboard's shooting-only scope.
STATE_RACE_POPULATION_COLS = {
    'White': 'White Population',
    'Black': 'Black Population',
    'Hispanic': 'Hispanic Population',
    'Asian': 'Asian Population',
    'Native American': 'Native American Population',
    'Pacific Islander': 'Pacific Islander Population',
}
STATE_SHEET_REQUIRED_COLUMNS = ['State', 'Total Population'] + list(STATE_RACE_POPULATION_COLS.values())

# Full state names for hover-text readability on the per-state choropleth
# map -- the map itself keys entirely off the 2-letter codes both MPV
# sheets already use (COL_STATE and the "Killings by State" sheet's own
# 'State' column agree exactly, confirmed against a live pull), which is
# also exactly what Plotly's built-in `locationmode: 'USA-states'` wants,
# so no geojson/FIPS lookup is needed anywhere in this pipeline.
STATE_NAME_BY_ABBR = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
    'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine',
    'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
    'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island',
    'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
    'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}

# National arrest totals by race, by year, for the "shootings per 100k
# arrests" trend chart. Hand-maintained (no live API access -- see
# build_arrest_rate_trend()'s docstring for why) -- refresh when FBI
# publishes a new year's figures.
#
# Source (all years, single consistent methodology): FBI Crime Data
# Explorer, Arrestee Race tool (cde.ucr.cjis.gov/LATEST/webapp/#/pages/
# explorer/crime/arrest), user-exported CSV covering 2013-2025, pulled
# 2026-08-25. This replaces an earlier version of this dict that blended
# three different FBI source products across the span (Crime in the
# United States Table 43A, an earlier round of hand-copied CDE numbers,
# and the Reported Crimes in the Nation Quick Stats) -- that patchwork
# is why 2021 was missing and why 2020's "Other" figure was off by
# roughly 3x (782,587 vs. the correct 265,347 below); a single source
# for the whole series avoids both problems.
#
# The CDE export breaks arrestees into: White; Black or African
# American; Unknown; American Indian or Alaska Native (AIAN); Asian;
# Native Hawaiian or Other Pacific Islander (NHOPI); Multiple; Not
# Specified; plus a grand total. Fields here:
#   'white'   -- White row, as-is
#   'black'   -- Black or African American row, as-is
#   'other'   -- AIAN + Asian + NHOPI (matches ARREST_RATE_RACE_GROUPS's
#                'Other' below and the shooting-count numerator it's
#                divided into a rate against), since FBI arrest reporting
#                treats race and Hispanic ethnicity as separate,
#                non-overlapping dimensions -- race totals already sum to
#                100%, so Hispanic arrestees are already counted inside a
#                race category (mostly "White") and can't be cleanly
#                split back out. Hispanic is intentionally excluded
#                rather than guessed; the Council on Criminal Justice's
#                own arrest-trends methodology handles this the same way.
#                See build_arrest_rate_trend()'s docstring for the
#                consequence this has on the "White" comparison.
#   'unknown' -- Unknown + Not Specified + Multiple combined, kept only
#                for transparency/bookkeeping (white+black+other+unknown
#                == total for every year) -- not used in the rate calc.
#   'total'   -- the CDE tool's own reported grand total for that year.
ARRESTS_BY_RACE_BY_YEAR = {
    2013: {'white': 4_063_963, 'black': 1_986_782, 'other': 253_194, 'unknown': 142_006, 'total': 6_445_945},
    2014: {'white': 6_336_228, 'black': 2_531_146, 'other': 266_991, 'unknown': 0, 'total': 9_134_365},
    2015: {'white': 6_168_945, 'black': 2_411_425, 'other': 354_102, 'unknown': 0, 'total': 8_934_472},
    2016: {'white': 6_138_384, 'black': 2_376_576, 'other': 346_549, 'unknown': 0, 'total': 8_861_509},
    2017: {'white': 6_115_879, 'black': 2_413_087, 'other': 349_174, 'unknown': 644_387, 'total': 9_522_527},
    2018: {'white': 5_914_026, 'black': 2_372_409, 'other': 334_531, 'unknown': 119_753, 'total': 8_740_719},
    2019: {'white': 5_545_854, 'black': 2_214_545, 'other': 322_252, 'unknown': 671_916, 'total': 8_754_567},
    2020: {'white': 4_278_932, 'black': 1_665_912, 'other': 265_347, 'unknown': 526_106, 'total': 6_736_297},
    2021: {'white': 3_459_300, 'black': 1_434_174, 'other': 211_246, 'unknown': 109_160, 'total': 5_213_880},
    2022: {'white': 4_338_280, 'black': 1_805_123, 'other': 261_617, 'unknown': 129_654, 'total': 6_534_674},
    2023: {'white': 4_541_256, 'black': 2_039_648, 'other': 281_814, 'unknown': 212_635, 'total': 7_075_353},
    2024: {'white': 4_474_451, 'black': 2_085_721, 'other': 291_950, 'unknown': 178_875, 'total': 7_030_997},
    2025: {'white': 4_491_706, 'black': 2_176_004, 'other': 300_709, 'unknown': 157_956, 'total': 7_126_375},
}

# No years currently excluded -- the single-source CDE export above
# covers every year 2013-2025, including 2021 (previously omitted; see
# git history). Kept as a mechanism/empty list rather than removed
# outright, in case a future year's data is unavailable when this dict
# is next refreshed.
ARREST_DATA_EXCLUDED_YEARS = []

# "Other" in the FBI figures above is a single combined category (AIAN +
# Asian + Native Hawaiian/Pacific Islander), so the shooting-count
# numerator for it has to sum three of bucket_race()'s categories rather
# than match one-to-one like White/Black do.
ARREST_RATE_RACE_GROUPS = {
    'White': ['White'],
    'Black': ['Black'],
    'Other': ['Asian', 'Native American', 'Pacific Islander'],
}

# This dashboard lives next to the site's shooting-specific news/research
# trackers, but MPV's own dataset covers every cause of death in police
# custody (Taser, vehicle, restraint, etc.), not just gunshots — so every
# chart here is scoped to incidents where a firearm was involved.
SCOPE_DESCRIPTION = "NOTE: Incidents involving a firearm (MPV 'Cause of death' contains Gunshot)"

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# How many of the most recent years to include in the year-over-year
# cumulative trajectory comparison.
TRAJECTORY_YEARS = 6
TOP_N = 15

# MPV incidents get added/verified over time, so the most recent stretch of
# "current year" data is undercounted relative to a fully-caught-up prior
# year. Shift year-to-date comparisons back this many days so they compare
# like-for-like rather than making the current year look artificially low.
YTD_LAG_DAYS = 14


def download_mpv_workbook(url=MPV_URL):
    """Download the MPV .xlsx into memory. Raises on any failure — a bad
    download should fail the workflow loudly rather than silently produce
    an empty/stale dashboard."""
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    if len(response.content) < 1_000_000:
        raise ValueError(
            f"Downloaded MPV file is suspiciously small ({len(response.content)} bytes) "
            "— the source URL or file format may have changed."
        )
    return response.content


def load_incidents(xlsx_bytes):
    """Parse the main incidents sheet and validate the schema we depend on."""
    import io
    df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=MPV_SHEET)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"MPV workbook is missing expected column(s): {missing}. "
            "The upstream schema may have changed — update the COL_* constants "
            "in scripts/generate_mpv_dashboard.py."
        )

    df['_date'] = pd.to_datetime(df[COL_DATE], errors='coerce')
    df = df.dropna(subset=['_date']).copy()

    # Administrative/category text fields: normalize case before any
    # grouping so casing inconsistencies in the source data (e.g. "Allegedly
    # Armed" vs "Allegedly armed") don't silently split a single category.
    # fillna('') first -- on this pandas version, .astype(str) alone leaves
    # real NaN floats untouched in a mixed object column (confirmed via a
    # live run: Encounter Type is 27% blank in the source and every blank
    # cell survived as an actual float, not the string 'nan', which broke
    # downstream .lower() calls expecting a string).
    for col in [COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY, COL_CAUSE, COL_ENCOUNTER, COL_WEAPON]:
        df[col] = df[col].fillna('').astype(str).str.strip()

    # MPV's dataset covers every cause of death in police custody, not just
    # shootings (Taser-only, vehicle, restraint, etc. are all included).
    # This dashboard is scoped to shootings, matching the site's other
    # police-shooting pages — case-insensitive match so "Gunshot, Taser"
    # combo rows are kept (a firearm was involved) while Taser-only/
    # Vehicle/Physical-Restraint-only rows are dropped.
    df = df[df[COL_CAUSE].str.upper().str.contains('GUNSHOT', na=False)].copy()

    return df


def bucket_race(raw_race):
    """Collapse the source's free-text race field into a small set of
    display categories (case-insensitive matching per project convention)."""
    if not raw_race or raw_race.lower() in ('nan', 'unknown race', 'unknown'):
        return 'Unknown'
    normalized = raw_race.upper()
    if ';' in raw_race or ' AND ' in normalized:
        return 'Multiracial'
    mapping = {
        'WHITE': 'White',
        'BLACK': 'Black',
        'HISPANIC': 'Hispanic',
        'ASIAN': 'Asian',
        'NATIVE AMERICAN': 'Native American',
        'PACIFIC ISLANDER': 'Pacific Islander',
    }
    return mapping.get(normalized, 'Unknown')


def bucket_armed_status(raw_status):
    """Collapse the source's armed/unarmed field into display categories
    (case-insensitive matching per project convention)."""
    if not raw_status or raw_status.lower() == 'nan':
        return 'Unclear/Unknown'
    normalized = raw_status.upper()
    if 'UNARMED' in normalized:
        return 'Unarmed'
    if 'VEHICLE' in normalized:
        return 'Vehicle'
    if 'ARMED' in normalized:
        return 'Allegedly Armed'
    return 'Unclear/Unknown'


def build_capped_breakdown(df, col, top_n=8, empty_label='Not Reported', aliases=None):
    """Generic free-text-column breakdown: title-cases each value (which
    also merges casing duplicates in the source data, e.g. "Traffic Stop"
    vs "Traffic stop" -- confirmed via a live run that Encounter Type has
    exactly this problem), maps missing values to `empty_label`, applies
    `aliases` (e.g. folding "Machete" into "Knife") before counting, then
    keeps the top `top_n` categories distinct and consolidates everything
    else (a long tail of rare/combo values) into 'Other' so the chart
    stays legible. Used for both Alleged Weapon and Encounter Type."""
    titled = df[col].apply(lambda v: v.strip().title() if v and v.strip() else empty_label)
    if aliases:
        titled = titled.map(lambda v: aliases.get(v, v))
    counts = titled.value_counts()
    top_labels = set(counts.head(top_n).index) - {empty_label}
    bucketed = titled.map(lambda v: v if (v in top_labels or v == empty_label) else 'Other')
    final_counts = bucketed.value_counts()
    return [{'label': str(k), 'count': int(v)} for k, v in final_counts.items()]


def build_yearly_counts(df):
    counts = df['_date'].dt.year.value_counts().sort_index()
    return [{'year': int(y), 'count': int(c)} for y, c in counts.items()]


def build_cumulative_trajectory(df, as_of):
    """Year-over-year cumulative incident count by month, for the most
    recent TRAJECTORY_YEARS years — lets the front end plot each year's
    running total on the same axis (Adams's dashboard's 'cumulative
    trajectory' comparison). The current year's line stops at `as_of`
    (lag-adjusted) rather than the true current month, so its tail isn't
    an under-count artifact of MPV's reporting lag."""
    current_year = datetime.now().year
    current_month = as_of.month
    years = list(range(current_year - TRAJECTORY_YEARS + 1, current_year + 1))

    series = []
    for year in years:
        year_df = df[df['_date'].dt.year == year]
        monthly = year_df.groupby(year_df['_date'].dt.month).size()
        cumulative = []
        running_total = 0
        last_month = current_month if year == current_year else 12
        for month in range(1, 13):
            if month > last_month:
                cumulative.append(None)
                continue
            running_total += int(monthly.get(month, 0))
            cumulative.append(running_total)
        series.append({'year': year, 'cumulative_by_month': cumulative})

    return {'months': MONTH_LABELS, 'series': series}


def build_calendar_heatmap(df, year=None):
    """GitHub-style single-year calendar heatmap: rows = weekday (Mon-Sun),
    columns = week-of-year index computed from days-since-Jan-1 (so weeks
    roll over on Mondays, matching DOW_LABELS' Mon-first order). Defaults
    to the current calendar year; future/not-yet-happened days are simply
    zero, the same way a GitHub contribution graph reads. Also returns
    month_starts (which week-index each month begins at) so the front end
    can label months along the top axis instead of raw week numbers."""
    if year is None:
        year = datetime.now().year

    year_df = df[df['_date'].dt.year == year]

    jan1 = datetime(year, 1, 1)
    jan1_weekday = jan1.weekday()  # Monday=0
    dec31_index = (datetime(year, 12, 31) - jan1).days
    n_weeks = (dec31_index + jan1_weekday) // 7 + 1

    matrix = [[0] * n_weeks for _ in range(7)]
    for d in year_df['_date']:
        day_index = (d - jan1).days
        week_index = (day_index + jan1_weekday) // 7
        matrix[d.weekday()][week_index] += 1

    month_starts = []
    for month in range(1, 13):
        first_of_month = datetime(year, month, 1)
        day_index = (first_of_month - jan1).days
        week_index = (day_index + jan1_weekday) // 7
        month_starts.append({'month': MONTH_LABELS[month - 1], 'week_index': week_index})

    return {
        'year': year,
        'day_labels': DOW_LABELS,
        'counts': matrix,
        'month_starts': month_starts,
    }


def build_breakdown(df, col, bucket_fn=None):
    values = df[col].map(bucket_fn) if bucket_fn else df[col]
    counts = values.value_counts()
    return [{'label': str(k), 'count': int(v)} for k, v in counts.items()]


def build_top_n(df, col, n=TOP_N):
    counts = df[col].value_counts().head(n)
    return [{'label': str(k), 'count': int(v)} for k, v in counts.items()]


def load_state_population(xlsx_bytes):
    """Read population-by-race context from the 'Killings by State' sheet.
    Only population columns are used here -- never that sheet's own Rate/
    Disparity columns, which are computed over MPV's all-cause killings
    total (see STATE_RACE_POPULATION_COLS comment above for why)."""
    import io
    df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=MPV_STATE_SHEET)
    missing = [c for c in STATE_SHEET_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"MPV '{MPV_STATE_SHEET}' sheet is missing expected column(s): {missing}. "
            "The upstream schema may have changed."
        )
    return df


def build_disparity_rates(df, state_pop_df):
    """National per-100k rate by race, computed from our own shooting-only
    incident counts (never MPV's own all-cause rate columns) divided by
    Census population by race summed across states. Only the six race
    categories with a matching population figure are included --
    Multiracial/Unknown have no population denominator to divide by."""
    race_counts = df[COL_RACE].map(bucket_race).value_counts()

    results = []
    white_rate = None
    for race, pop_col in STATE_RACE_POPULATION_COLS.items():
        population = int(state_pop_df[pop_col].sum())
        count = int(race_counts.get(race, 0))
        rate = (count / population * 100_000) if population else 0.0
        results.append({
            'race': race,
            'count': count,
            'population': population,
            'rate_per_100k': round(rate, 2),
        })
        if race == 'White':
            white_rate = rate

    for r in results:
        r['disparity_vs_white'] = round(r['rate_per_100k'] / white_rate, 2) if white_rate else None

    results.sort(key=lambda r: r['rate_per_100k'], reverse=True)
    return results


def build_state_rates(df, state_pop_df):
    """Per-state rate per 1,000,000 population, cumulative 2013-present, for
    the state choropleth map. Mirrors build_disparity_rates()'s approach
    (our own shooting-only incident counts divided by Census population,
    never MPV's own all-cause rate columns) but sliced by state instead of
    race. Both sheets already use the same 2-letter USPS codes (confirmed
    against a live pull), so this is a direct case-insensitive match with
    no name-mapping step."""
    incident_counts = df[COL_STATE].str.upper().str.strip().value_counts()

    results = []
    for _, row in state_pop_df.iterrows():
        code = row['State']
        if pd.isna(code):
            continue
        code = str(code).upper().strip()
        population = row['Total Population']
        if pd.isna(population) or population <= 0:
            continue
        population = int(population)
        count = int(incident_counts.get(code, 0))
        rate = count / population * 1_000_000
        results.append({
            'state': code,
            'name': STATE_NAME_BY_ABBR.get(code, code),
            'count': count,
            'population': population,
            'rate_per_million': round(rate, 2),
        })

    results.sort(key=lambda r: r['rate_per_million'], reverse=True)
    return results


def build_arrest_rate_trend(df):
    """Year-by-year per-100k-arrests rate by race (White/Black/Other),
    2013-2025, for the arrest-rate trend line chart. Each year divides
    our own shooting-only incident counts *for that year* by
    hand-maintained FBI arrest totals for that year
    (ARRESTS_BY_RACE_BY_YEAR -- see that constant's comment for sourcing
    and why Hispanic isn't included). "Other" sums three of
    bucket_race()'s categories (ARREST_RATE_RACE_GROUPS) to match FBI's
    own combined grouping. Any year with no FBI arrest total would be
    skipped rather than estimated -- see ARREST_DATA_EXCLUDED_YEARS
    (currently empty; every year 2013-2025 has data).

    Note this chart's "White" comparison carries a real, unavoidable
    limitation: FBI's White arrest count includes Hispanic-White
    individuals (race and ethnicity aren't cleanly separable in FBI
    reporting), while our own "White" shooting-victim count does not
    (MPV/bucket_race() treats Hispanic as its own exclusive category).
    This makes the computed White arrest-rate a slight underestimate
    relative to a true non-Hispanic-White rate -- flagged in the UI
    caption, not hidden."""
    years = sorted(ARRESTS_BY_RACE_BY_YEAR.keys())
    race_counts_by_year = {
        year: df[df['_date'].dt.year == year][COL_RACE].map(bucket_race).value_counts()
        for year in years
    }

    series = {race: [] for race in ARREST_RATE_RACE_GROUPS}
    for race, mpv_categories in ARREST_RATE_RACE_GROUPS.items():
        for year in years:
            arrests = ARRESTS_BY_RACE_BY_YEAR[year][race.lower()]
            count = sum(int(race_counts_by_year[year].get(r, 0)) for r in mpv_categories)
            rate = (count / arrests * 100_000) if arrests else 0.0
            series[race].append({
                'year': year,
                'count': count,
                'arrests': arrests,
                'rate_per_100k_arrests': round(rate, 2),
            })

    return {
        'years': years,
        'excluded_years': ARREST_DATA_EXCLUDED_YEARS,
        'series': series,
    }


def build_dashboard_json(df, state_pop_df):
    most_recent = df['_date'].max()
    current_year = datetime.now().year

    # Lag-adjusted year-to-date comparison: MPV incidents get added/verified
    # over time, so comparing "as of today" would make the current year
    # look artificially low against a fully-caught-up prior year. Compare
    # both years as of the same lag-adjusted date instead.
    as_of = datetime.now() - timedelta(days=YTD_LAG_DAYS)
    as_of_day_of_year = as_of.timetuple().tm_yday

    ytd_count = int((
        (df['_date'].dt.year == current_year) &
        (df['_date'].dt.dayofyear <= as_of_day_of_year)
    ).sum())
    prior_year_same_point = int((
        (df['_date'].dt.year == current_year - 1) &
        (df['_date'].dt.dayofyear <= as_of_day_of_year)
    ).sum())

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': 'Mapping Police Violence (mappingpoliceviolence.us)',
        'source_last_incident_date': most_recent.strftime('%Y-%m-%d'),
        'scope': SCOPE_DESCRIPTION,
        'stats': {
            'total_incidents': int(len(df)),
            'current_year': current_year,
            'prior_year': current_year - 1,
            'as_of_date': as_of.strftime('%Y-%m-%d'),
            'lag_days': YTD_LAG_DAYS,
            'current_year_to_date': ytd_count,
            'prior_year_same_point': prior_year_same_point,
        },
        'yearly_counts': build_yearly_counts(df),
        'cumulative_trajectory': build_cumulative_trajectory(df, as_of),
        'heatmap': build_calendar_heatmap(df),
        'race_breakdown': build_breakdown(df, COL_RACE, bucket_race),
        'armed_status_breakdown': build_breakdown(df, COL_ARMED, bucket_armed_status),
        'encounter_breakdown': build_capped_breakdown(df, COL_ENCOUNTER, empty_label='Not Reported'),
        'weapon_breakdown': build_capped_breakdown(df, COL_WEAPON, empty_label='Unknown', aliases={'Machete': 'Knife'}),
        'disparity_rates': build_disparity_rates(df, state_pop_df),
        'arrest_rate_trend': build_arrest_rate_trend(df),
        'state_rates': build_state_rates(df, state_pop_df),
        'top_agencies': build_top_n(df, COL_AGENCY),
    }


def main():
    print("Downloading Mapping Police Violence dataset...")
    try:
        xlsx_bytes = download_mpv_workbook()
    except Exception as e:
        print(f"ERROR: failed to download MPV dataset: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Downloaded {len(xlsx_bytes):,} bytes. Parsing '{MPV_SHEET}' sheet...")
    try:
        df = load_incidents(xlsx_bytes)
        state_pop_df = load_state_population(xlsx_bytes)
    except Exception as e:
        print(f"ERROR: failed to parse MPV dataset: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df):,} incidents "
          f"({df['_date'].min().date()} to {df['_date'].max().date()})")
    print(f"Loaded population context for {state_pop_df['State'].notna().sum()} states/DC")

    dashboard = build_dashboard_json(df, state_pop_df)

    os.makedirs(os.path.dirname(DASHBOARD_OUTPUT_FILE), exist_ok=True)
    with open(DASHBOARD_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    print(f"Dashboard aggregates saved to: {DASHBOARD_OUTPUT_FILE}")

    print("\nSummary:")
    print(f"  Total incidents: {dashboard['stats']['total_incidents']:,}")
    print(f"  {dashboard['stats']['current_year']} YTD: {dashboard['stats']['current_year_to_date']:,} "
          f"(same point last year: {dashboard['stats']['prior_year_same_point']:,})")


if __name__ == '__main__':
    main()
