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

REQUIRED_COLUMNS = [COL_DATE, COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY, COL_CAUSE]

# This dashboard lives next to the site's shooting-specific news/research
# trackers, but MPV's own dataset covers every cause of death in police
# custody (Taser, vehicle, restraint, etc.), not just gunshots — so every
# chart here is scoped to incidents where a firearm was involved.
SCOPE_DESCRIPTION = "Incidents involving a firearm (MPV 'Cause of death' contains Gunshot)"

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
    for col in [COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY, COL_CAUSE]:
        df[col] = df[col].astype(str).str.strip()

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


def build_dashboard_json(df):
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
        'top_states': build_top_n(df, COL_STATE),
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
    except Exception as e:
        print(f"ERROR: failed to parse MPV dataset: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df):,} incidents "
          f"({df['_date'].min().date()} to {df['_date'].max().date()})")

    dashboard = build_dashboard_json(df)

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
