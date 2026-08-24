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
from datetime import datetime

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

REQUIRED_COLUMNS = [COL_DATE, COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY]

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DOW_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

# How many of the most recent years to include in the year-over-year
# cumulative trajectory comparison.
TRAJECTORY_YEARS = 6
TOP_N = 15


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
    for col in [COL_STATE, COL_RACE, COL_ARMED, COL_AGENCY]:
        df[col] = df[col].astype(str).str.strip()

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


def build_cumulative_trajectory(df):
    """Year-over-year cumulative incident count by month, for the most
    recent TRAJECTORY_YEARS years — lets the front end plot each year's
    running total on the same axis (Adams's dashboard's 'cumulative
    trajectory' comparison)."""
    current_year = datetime.now().year
    current_month = datetime.now().month
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


def build_heatmap(df):
    """Day-of-week x month incident-count matrix for a temporal heatmap."""
    dow = df['_date'].dt.dayofweek  # Monday=0
    month = df['_date'].dt.month
    matrix = [[0] * 12 for _ in range(7)]
    for d, m in zip(dow, month):
        matrix[int(d)][int(m) - 1] += 1
    return {'day_labels': DOW_LABELS, 'month_labels': MONTH_LABELS, 'counts': matrix}


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
    ytd_count = int((df['_date'].dt.year == current_year).sum())
    prior_year_same_point = df[
        (df['_date'].dt.year == current_year - 1) &
        (df['_date'].dt.dayofyear <= datetime.now().timetuple().tm_yday)
    ].shape[0]

    return {
        'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': 'Mapping Police Violence (mappingpoliceviolence.us)',
        'source_last_incident_date': most_recent.strftime('%Y-%m-%d'),
        'stats': {
            'total_incidents': int(len(df)),
            'current_year': current_year,
            'current_year_to_date': ytd_count,
            'prior_year_same_point': int(prior_year_same_point),
        },
        'yearly_counts': build_yearly_counts(df),
        'cumulative_trajectory': build_cumulative_trajectory(df),
        'heatmap': build_heatmap(df),
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
