# Google Scholar Metrics Implementation

This documentation explains how the automatic Google Scholar metrics display works on your publications page.

## Overview

Your publications page now displays four key metrics at the top:
- **Total Citations** - From Google Scholar
- **h-index** - From Google Scholar
- **i10-index** - From Google Scholar
- **Publications** - Count of publications on your site

These metrics update automatically via GitHub Actions.

## Files Added/Modified

### 1. Python Script
**File:** `scripts/fetch_scholar_metrics.py`
- Fetches metrics from Google Scholar using the `scholarly` library
- Saves data to `data/scholar_metrics.json`
- Handles errors gracefully with fallback data

### 2. Custom Layout
**File:** `layouts/section/publication.html`
- Overrides the theme's default publication layout
- Reads metrics from `data/scholar_metrics.json`
- Displays metrics in four styled boxes
- Maintains all original publication page functionality

### 3. CSS Styling
**File:** `static/css/custom.css`
- Added `.scholar-metrics` and `.metric-box` styles
- Responsive design for mobile devices
- Hover effects for visual feedback

### 4. GitHub Actions Workflow
**File:** `.github/workflows/update-scholar-metrics.yml`
- Runs weekly on Mondays at 6 AM UTC
- Can be manually triggered from GitHub Actions tab
- Automatically commits updated metrics

### 5. Requirements File
**File:** `requirements.txt`
- Lists Python dependencies: `scholarly` and `requests`

## Manual Usage

### First Time Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the script manually to generate initial data:
```bash
python scripts/fetch_scholar_metrics.py
```

This will create `data/scholar_metrics.json` with your current metrics.

### Update Metrics Manually

To update metrics at any time:
```bash
python scripts/fetch_scholar_metrics.py
git add data/scholar_metrics.json
git commit -m "Update Google Scholar metrics"
git push
```

## Automatic Updates

The GitHub Actions workflow automatically runs weekly. You can also:

1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Update Google Scholar Metrics"
4. Click "Run workflow" button

## Data File Location

**File:** `data/scholar_metrics.json`

Example structure:
```json
{
  "name": "Justin Nix",
  "affiliation": "University of Nebraska Omaha",
  "h_index": 21,
  "i10_index": 32,
  "citations": 1782,
  "updated": "2025-01-21T12:00:00+00:00",
  "scholar_url": "https://scholar.google.com/citations?user=_Jr8r8UAAAAJ"
}
```

## Customization

### Change Update Frequency

Edit `.github/workflows/update-scholar-metrics.yml`:
```yaml
schedule:
  # Daily at 6 AM UTC
  - cron: '0 6 * * *'

  # Or every 2 weeks
  - cron: '0 6 1,15 * *'
```

### Change Metrics Display

Edit `layouts/section/publication.html` to:
- Reorder metric boxes
- Add/remove metrics
- Change labels

### Change Styling

Edit `static/css/custom.css` in the "Google Scholar Metrics Styling" section to:
- Change colors
- Adjust box sizing
- Modify hover effects

## Troubleshooting

### Metrics not showing

1. Ensure `data/scholar_metrics.json` exists
2. Check file format is valid JSON
3. Rebuild your site: `hugo server`

### GitHub Actions failing

1. Check Actions tab for error logs
2. Ensure `scholarly` package can access Google Scholar
3. May need to add delays if rate-limited

### Wrong Google Scholar ID

Update the ID in `scripts/fetch_scholar_metrics.py`:
```python
SCHOLAR_ID = "YOUR_ID_HERE"
```

## Credits

Implementation inspired by Ian T. Adams' approach:
https://github.com/ian-adams/academic-website
