# Session Log: Police research tracker — OpenAlex rebuild

**Date:** 2026-08-28
**Plan:** `~/.claude/plans/let-s-revisit-content-police-shooting-re-lazy-ember.md`

## Goal

The "OIS Research" feed (`content/police-shooting-research/`) has been stuck at the same 4 articles for months. Diagnose and fix the discovery half of `scripts/generate_police_shooting_research.py`.

## Diagnosis (empirically verified with live API calls during planning)

- **Primary bug:** `fetch_crossref` uses `sort=published&order=desc` + `rows=100`. Every query's top 100 results are books/chapters with garbage future dates (`[2050,4,21]`, dozens of `[2026,12,31]`). Zero real journal articles reach the filter.
- Crossref free-text `query` is weak for this domain regardless of sort.
- No OpenAlex — the best source (proper `title_and_abstract.search`, reconstructable abstracts).
- PubMed abstracts always blank (`esummary`), so `is_relevant_article` runs title-only for PubMed → silent over-rejection.
- Whitelist missing ~20 journals (JAMA Network Open most important — 3+ recent hits).

**Verified:** OpenAlex + expanded whitelist + the *unchanged* `is_relevant_article` = 55 on-topic articles from the right journals in 180 days, vs. 4 today.

## Decisions (with user)

- Sources: OpenAlex primary + PubMed backup; **remove** Crossref (not just demote — user picked "drop the broken Crossref path").
- Keep the curated whitelist gate, expand it.
- Backfill: one local `--backfill` run (1095-day window), commit the data files manually.
- **Keep `is_relevant_article` as-is** — user explicitly chose this. It is not the bottleneck. The design agent's loosening proposal is recorded as deferred/optional only.

## Rejected alternatives

- Demoting rather than removing Crossref (design agent's preference) — user chose removal.
- Loosening the relevance filter / `require_positive=False` mode — user chose to keep the filter untouched.
- Dropping the whitelist entirely or switching to an OpenAlex topic filter — user chose to keep the curated list.

## Implementation notes

- **2026-08-29** — First full run after the rebuild: 145 candidates (vs 4). But ~60% non-U.S. and ~15–20 off-topic (burden-of-disease reviews, sex-worker interventions, IPV-reporting studies). The plan's "keep `is_relevant_article` as-is" assumption didn't survive contact with the real result set — the earlier 10-query OpenAlex-only test (55 clean hits) understated the noise from PubMed + reviews + the international policing journals.
- Went back to the user with two questions. Decisions:
  - **Keep global scope** (no U.S. filter). RSS `<title>` still says "U.S. …" — flagged, not changed.
  - **Tighten topical match** — so `is_relevant_article` *was* changed after all: added `core_topic_terms` gate (police must be tied *to* force/violence/oversight/pursuit/custody), `non_research_prefixes` title check, `type:article,is_paratext:false` on OpenAlex, `PUBMED_EXCLUDE_TYPES` on PubMed. Result ~57/180-day run.
- **[LEARN:data]** Crossref `sort=published&order=desc` floats fake-future-dated books/chapters (`[2050,4,21]`, many `[2026,12,31]`) to the top of every result page — never use it for a "recent articles" feed. → memory `crossref-sort-published-trap`.
- **Dedup bug found & fixed**: same paper from OpenAlex + old PubMed history wasn't deduped (trailing "." + no DOI on the old entry). Added `_title_key()` normalization to both `merge_stories` and the within-run dedup.
- **Resilience**: OpenAlex 429'd during repeated testing. Added `get_with_retry()` (backoff, honors `Retry-After`) to both fetchers; fail-loud preserved for persistent failure.
- Verified: zero-result run (`--days-back 1`) doesn't blank the page; simulated OpenAlex exception → `sys.exit(1)`, data files untouched; no dupes; abstracts populated (11/100 legitimately empty — Elsevier); priority badge fires for 4 items.
- Local testing used a scratchpad venv (`pip install requests`) — repo Python has no `requests`. The GitHub Action installs `requirements.txt`, so no workflow change.

## 2026-08-30 — closing

- Repeated local test runs got this machine's IP rate-limited by OpenAlex; one 429 came back with `Retry-After: 22141` (6 h). Exposed a bug: `get_with_retry` slept on it literally. Fixed: `RETRY_MAX_WAIT = 60` — a longer `Retry-After` now re-raises (fail loud) instead of sleeping for hours.
- After the throttle cleared, a clean 180-day run produced **56 stories** (Mar–Aug 2026), 0 dupes, 8 legitimately-empty abstracts, 3 priority badges. This is the committed state of the two data files.
- `--backfill` (3-yr, ~100 stories) was **not** re-run — 3× the request volume risks re-throttling for hours. Left for the user to run later, or the Monday cron handles the normal refresh from a clean runner IP.
- Also updated `content/police-shooting-research/_index.md` intro line: "Crossref and PubMed" → "OpenAlex and PubMed". NOTE: that file had a *pre-existing* unstaged edit (removed the "Research areas covered" bullet list) that was not made this session — flagged to the user.
- RSS `<channel><title>` changed "U.S. Police Shooting Research Tracker" → "Police Shooting Research Tracker" per user (feed is global scope now).

### Open items for next session
- User to review + commit: `scripts/generate_police_shooting_research.py`, the two `static/data/police-shooting-research.*` files, `content/police-shooting-research/_index.md`.
- Optional: run `python scripts/generate_police_shooting_research.py --backfill` once for a deeper initial history (~100 stories vs 56).
- Decide on the pre-existing `_index.md` bullet-list deletion.
- `--backfill`'s `get_with_retry` path is now exercised; the normal weekly path is unchanged and low-volume.

## Committed & pushed 2026-08-30

- `525ac39` "Rebuild research tracker on OpenAlex; drop broken Crossref source" — 6 files (script, both data files, both tracker `_index.md`, this log).
- Rebase onto origin/master (4 new `Update police shooting news feed [automated]` commits) failed mid-pick on OneDrive I/O; aborted cleanly and used `git merge` instead → merge commit `57a9934`. No file conflicts (incoming commits only touched `static/data/police-shooting-news.*`).
- Pushed to `origin/master`; local and remote in sync.
