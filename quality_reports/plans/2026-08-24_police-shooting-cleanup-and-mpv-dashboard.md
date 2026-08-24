# Plan: Clean up police-shooting trackers + build an MPV-style dashboard

**Date:** 2026-08-24
**Status:** APPROVED
**Task:** Revisit `content/police-shooting-news` and `content/police-shooting-research` (and their generator scripts) for cleanup, and add a new dashboard page modeled on Ian Adams's "MPV Analysis" dashboard.

## Context

Two existing features — a daily news tracker and a weekly academic-research tracker on police shootings — have been iterated on for months (20+ commits to the two Python scripts, including a recent `fix blank pages` commit). They work, but exploration surfaced several real bugs and a code-duplication problem worth fixing while we're in here.

Separately, the user wants a dashboard like colleague Ian Adams's ["MPV Analysis"](https://ianadamsresearch.com/dashboard/). His site's GitHub source isn't public anymore (his profile shows no `dashboard`/`mpv`/website repo — he also migrated his own site Hugo→Astro recently, which likely explains this). Confirmed via his live dashboard page, though: it's a static, client-side setup — it fetches a local `/data/mpv-data.json` and shows no server/Shiny dependency — i.e. the same "scheduled script writes a data file, static site renders it client-side" architecture this site already uses for the news/research trackers. We can't fork his code, but we can replicate the architecture and the underlying public dataset (Mapping Police Violence, downloadable as `.xlsx` from mappingpoliceviolence.us).

Per your answers: the dashboard will use the **national Mapping Police Violence dataset**, built as **static JSON + client-side JS charts** (no Shiny/server), and cleanup will **fix all identified issues** in the existing scripts.

---

## Part A — Clean up the two existing trackers

### A1. Bug fixes in the generator scripts

**`scripts/generate_police_shooting_news.py`:**
- `normalize_title()` has dead code: the mojibake fix on lines 348-349 calls `.replace('â€"', '-')` twice with the identical (already-garbled) string, so nothing is actually fixed for other mojibake variants (curly quotes, apostrophes). Replace with a general Latin-1→UTF-8 mojibake repair (`text.encode('latin1').decode('utf-8')` wrapped in try/except) instead of a hardcoded replace list.
- `main()` silently returns without writing the file when zero articles survive filtering (lines 406-412) — this is what caused the earlier "blank pages" bug and can recur any time GDELT has a quiet day or filtering is too strict. Fix by reading the previous run's data before generating and merging new+old (dedup by URL, keep newest N) instead of overwriting from scratch each run — this also gives the feed a persistent rolling history instead of a single ephemeral top-50 snapshot.
- GDELT's `description` field is always empty (line 70) — news cards currently render with no summary text. Leave as-is (GDELT genuinely doesn't provide one) but note it's a known source limitation, not a bug to "fix."

**`scripts/generate_police_shooting_research.py`:**
- `fetch_crossref()` and `fetch_pubmed()` calls have no `timeout=` (unlike the news script's GDELT call, which sets `timeout=30`) — add explicit timeouts so a slow API can't hang the whole workflow.
- Same zero-results-overwrites-nothing issue as the news script — apply the same merge-with-previous-run fix here.
- Crossref abstracts contain raw JATS markup (`<jats:p>…`) that gets dropped unescaped into the RSS `<description>` and then injected via `innerHTML` client-side — strip JATS tags before storing the abstract.
- The front-end JS (`_index.md`) reads `item.querySelector('priority')`, but the script never writes a `<priority>` element — dead/vestigial code. Implement it: flag items from a small "flagship" subset of `WHITELISTED_JOURNALS` (e.g. *Criminology*, *Criminology & Public Policy*, *Justice Quarterly*, *Journal of Criminal Justice*, *Police Quarterly*, *Justice Evaluation Journal* — aligned with your `CLAUDE.md` target journals) as `priority = true` so the existing "KEY JOURNAL" badge actually lights up.
- PubMed abstracts are always empty (comment acknowledges this — `esummary` doesn't return them). Leave as a documented limitation for v1; noting `efetch` as a future enhancement if desired.

### A2. Replace duplicated inline HTML/CSS/JS with the existing shared component

Found that `content/media/_index.md` already uses a clean, reusable pattern — a shared `static/js/news-feed.js` (`NewsFeed` class: JSON-driven, paginated, filterable, **and HTML-escapes every field before injecting into the DOM**) plus `static/css/news-feed.css`. The two police-shooting pages currently do **not** use this component — each hand-rolls ~250-300 lines of duplicated inline `<style>`/`<script>`, parses RSS/XML client-side, and interpolates article titles/descriptions into `innerHTML` **without escaping** (a real, if low-severity, hardening gap versus the existing `NewsFeed.escapeHtml()`).

Fix: have both generator scripts additionally emit a JSON sidecar (`static/data/police-shooting-news.json`, `static/data/police-shooting-research.json`) in the `{stories: [...]}` shape `NewsFeed` expects, keep writing the RSS XML too (both pages advertise "Subscribe via RSS" and that should keep working), and rewrite both `_index.md` pages to instantiate `NewsFeed` against the JSON — same as `content/media/_index.md` does — instead of their bespoke fetch/parse/render code. This removes the duplication, adds pagination for free, and closes the escaping gap.

### A3. Housekeeping

- Delete the two stray 0-byte `.Rhistory` files in `content/police-shooting-news/` and `content/police-shooting-research/`; confirm `.gitignore` covers `.Rhistory` (there's already an uncommitted `.gitignore` change in the working tree — check it doesn't already handle this before adding a duplicate rule).
- Standardize the two workflows (`update-police-news.yml`, `update-police-research.yml`) to `pip install -r requirements.txt` like `update-scholar-metrics.yml` does, instead of ad hoc `pip install requests`, and add any new deps there.

---

## Part B — New "MPV Analysis"-style dashboard

### B1. Data pipeline: `scripts/generate_mpv_dashboard.py` (new)

- Downloads the public MPV dataset (`https://mappingpoliceviolence.us/s/MPVDatasetDownload.xlsx`) with `pandas`/`openpyxl`.
- Cleans/normalizes: dates, state postal codes, race/ethnicity categories (case-insensitive per your `CLAUDE.md` data-analysis conventions), armed/unarmed status.
- Computes aggregates only (not the full incident-level table, to keep the page light) and writes `static/data/mpv-dashboard.json`:
  - Total incidents, most recent incident date, last-updated timestamp
  - Yearly counts + current-year-to-date vs. same-point-in-prior-years (the "cumulative trajectory" comparison Adams's dashboard features)
  - Monthly/day-of-week counts (temporal heatmap)
  - Breakdown by race/ethnicity and by armed/unarmed status
  - Top states and top agencies by incident count
- v1 scope excludes per-capita rates (needs a Census population lookup) — flagged as a clean follow-on, not a blocker.
- Also writes a slim per-incident JSON (`static/data/mpv-incidents.json`: id, date, state, city, race, armed status, agency — no victim names, to keep it small and avoid re-publishing identifying details beyond what MPV itself already makes public) for a "download the data" link, mirroring Adams's dashboard offering a raw JSON download.

### B2. Scheduling

New `.github/workflows/update-mpv-dashboard.yml`: weekly cron (Mondays, matching the research tracker's cadence — MPV itself doesn't update more than daily/weekly) + `workflow_dispatch`, `pip install -r requirements.txt` (add `pandas`, `openpyxl` to `requirements.txt`), commit the two JSON files if changed.

### B3. Front-end: `content/police-shooting-dashboard/_index.md` (new)

- New Hugo page (`type: page`, same theme fallback as the other two trackers), fetches `mpv-dashboard.json` client-side.
- Charts via **Plotly.js** (CDN `<script src="https://cdn.plot.ly/…">`, no install/build step needed — fits the static-site constraint) rendered by a new `static/js/mpv-dashboard.js`, styled with a new `static/css/mpv-dashboard.css` that reuses the site's existing `var(--article-bg-color)`/`var(--text-muted)` theme variables so it respects light/dark mode like the rest of the site.
- v1 chart set (matches Adams's stated modules): stat tiles (total incidents, YTD count), yearly trend line, current-year-vs-prior-years cumulative comparison, race/ethnicity bar breakdown, day-of-week × month heatmap, top-agencies bar chart. A future iteration can add a state-level map.
- Add nav entry in `config/_default/menus.toml` (same pattern as the existing `OIS News` / `OIS Research` entries, e.g. `name = "OIS Dashboard"`, `url = "/police-shooting-dashboard/"`).

---

## Files touched

- `scripts/generate_police_shooting_news.py` — bug fixes (A1)
- `scripts/generate_police_shooting_research.py` — bug fixes (A1)
- `content/police-shooting-news/_index.md`, `content/police-shooting-research/_index.md` — switch to shared `NewsFeed` component (A2)
- `static/js/news-feed.js` — minor extension if the police-feed card layout needs fields `NewsFeed`'s default renderer doesn't have (e.g. `category` filter, `priority` badge) — likely a custom `renderCard` passed in config, no core class changes needed
- `.github/workflows/update-police-news.yml`, `.github/workflows/update-police-research.yml` — use `requirements.txt` (A3)
- `requirements.txt` — add `pandas`, `openpyxl`
- `scripts/generate_mpv_dashboard.py` — new (B1)
- `.github/workflows/update-mpv-dashboard.yml` — new (B2)
- `content/police-shooting-dashboard/_index.md`, `static/js/mpv-dashboard.js`, `static/css/mpv-dashboard.css` — new (B3)
- `config/_default/menus.toml` — add dashboard nav entry (B3)
- Delete: `content/police-shooting-news/.Rhistory`, `content/police-shooting-research/.Rhistory` (A3)

## Verification

- Run both updated generator scripts locally (`python scripts/generate_police_shooting_news.py`, `...research.py`) and confirm: exit code 0, both RSS XML and new JSON sidecars are written with non-zero item counts, and a simulated zero-result run (e.g. temporarily point `SEARCH_QUERIES` at nonsense) leaves the previous file intact rather than wiping it.
- Run `scripts/generate_mpv_dashboard.py` locally, confirm `static/data/mpv-dashboard.json` and `mpv-incidents.json` are created with sane aggregate totals (spot-check yearly counts against MPV's own published totals).
- `hugo server` locally (or Netlify deploy preview) and visually check all three pages: news/research trackers still render, filter/paginate correctly, no unescaped-HTML rendering glitches; dashboard renders all v1 charts with real data, respects dark/light theme toggle.
- Confirm the three GitHub Actions workflows still parse (`workflow_dispatch` manual run) and commit only the expected files.

## Notes / risks

- MPV's `.xlsx` schema/URL could change without notice (it's an external nonprofit dataset, not a stable API) — the script should fail loudly (non-zero exit, clear error) rather than silently producing an empty dashboard if the download or expected columns don't match.
- Keeping a rolling history (A1) means `static/data/*.xml`/`*.json` will grow over time — cap at a fixed N (e.g. 200 news items, 100 research items) so file size stays small.
- Per-capita rates and a state-choropleth map are natural v2 additions once v1 ships, not required for parity with what the dashboard needs to do on day one.
