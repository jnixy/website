#!/usr/bin/env python3
"""
One-off: freeze MPV's state population-by-race figures into a committed CSV.

The MPV dashboard's per-state map and per-100k race rates need Census
population denominators. Those used to come from the "Killings by State"
sheet of the mappingpoliceviolence.us workbook, but MPV moved to
mappingpoliceviolence.org (Campaign Zero) in 2026 and its new Airtable
export is incident-level only -- no state sheet. The .us workbook is frozen
(last incident 2026-08-18) and may eventually disappear, so this pulls its
population columns once into datasets/mpv-state-population.csv, which
generate_mpv_dashboard.py now reads instead.

Only population columns are kept -- never the sheet's own Rate/Disparity
columns (all-cause, not shooting-only; see generate_mpv_dashboard.py).

Usage: python scripts/extract_mpv_state_population.py [path/to/MPVDatasetDownload.xlsx]
       (downloads the frozen .us workbook if no path is given)
"""

import io
import os
import sys

import pandas as pd
import requests

LEGACY_MPV_URL = 'https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx'
LEGACY_STATE_SHEET = '2013-2026 Killings by State'
OUTPUT_FILE = 'datasets/mpv-state-population.csv'

KEEP_COLUMNS = [
    'State', 'Total Population',
    'White Population', 'Black Population', 'Hispanic Population',
    'Asian Population', 'Native American Population', 'Pacific Islander Population',
]


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'rb') as f:
            xlsx_bytes = f.read()
    else:
        response = requests.get(LEGACY_MPV_URL, timeout=120)
        response.raise_for_status()
        xlsx_bytes = response.content

    df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=LEGACY_STATE_SHEET)
    missing = [c for c in KEEP_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"'{LEGACY_STATE_SHEET}' sheet is missing column(s): {missing}")

    # The sheet ends in summary/blank rows; keep only real 2-letter states.
    df = df[KEEP_COLUMNS].copy()
    df['State'] = df['State'].astype(str).str.upper().str.strip()
    df = df[df['State'].str.fullmatch(r'[A-Z]{2}') & df['Total Population'].notna()]
    for col in KEEP_COLUMNS[1:]:
        df[col] = df[col].fillna(0).astype('int64')

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.sort_values('State').to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(df)} states to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
