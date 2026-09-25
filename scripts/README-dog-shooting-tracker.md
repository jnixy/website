# Police Shootings of Dogs Tracker

`generate_dog_shooting_tracker.py` builds and maintains a news-derived dataset of
incidents in which a sworn U.S. law enforcement officer fired a gun at or toward a
dog. It is modeled on Charles Fain Lehman's
[flock-crime-tracker](https://github.com/CharlesFainLehman/flock-crime-tracker)
and follows the same pattern as this site's other trackers (a Python script writes
JSON into `static/data/`; a Hugo page renders it; a GitHub Actions cron commits the
result and Netlify redeploys).

## Pipeline

| Stage | What happens |
|---|---|
| discover | Google News RSS (`GOOGLE_NEWS_PHRASINGS`, the only source). Blocked domains, non-US TLDs, already-seen URLs, and human-excluded URLs (`datasets/dog-shootings-excluded.json`) are dropped. Queries are single quoted phrases. |
| extract | Article body text via `trafilatura`. If the page is video- or script-only (no body text), the article is **not** dropped — it goes to classify with a headline-only flag and stricter rules: a passive headline ("dog shot by officers", "…her dog, who was shot by police") qualifies, but the law-enforcement actor must be named in the headline itself (not inferred from the URL or town), and a headline that names a civilian, an off-duty/retired officer, or an officer under SBI/DA/IA investigation for the shooting does not. |
| classify | One `claude-haiku-4-5` call per article (forced tool call), given the article's **publication date** as the anchor for resolving "Thursday" / "this week". Returns `qualifies` plus structured fields. `PROMPT_VERSION` is stamped on every row. Date guards: the model must quote its evidence in `incident_date_source` (no quote → date blanked); a resolved year more than one year before publication with `litigation = none` is dropped (mis-resolved relative date). Enum drift is coerced onto the vocab. A row with no `state`, or a `state` that is not a US state (Canadian stories sometimes pass the headline-only classifier), is dropped rather than failing the whole batch at `validate_rows()`. |
| dedupe | Candidates are blocked by `state` (or `city` when the row has no state) — no date window. One `claude-haiku-4-5` call decides same-incident **from the summary alone, ignoring dates** (they are often wrong): same agency, same metro, same described sequence of events / named officials. A match appends the URL to the existing row's `additional_sources`; no new row. |
| store | Append new incidents to `datasets/dog-shootings.csv` (`reviewed = no`). Update `datasets/dog-shootings-seen-urls.json`. Existing rows' fields are never overwritten — only `additional_sources` grows on a dedupe match. |
| validate | Parse check, no future dates, enum vocab, no duplicate ids, no blocklisted source domains. Aborts the write if >50% of processed articles errored. |
| emit | `static/data/dog-shooting-tracker.json` (aggregates + recent incidents) and `static/data/dog-shootings.csv` (published copy). |

## Scope

**Included:** a currently-serving sworn law enforcement officer — municipal
police, county sheriff/deputy, state police, federal, tribal, or campus — who,
**while acting as police** (a call, stop, arrest, patrol, warrant, or otherwise
handling a police matter), discharged a firearm at or toward a dog — or fired at
someone else and struck a dog, including a police K-9 (`dog_targeted=no`; scope
widened 2026-09-24). Why the officer fired doesn't matter: protecting a person, a
dog attacking another dog, a loose dog. Any outcome counts (killed, wounded,
missed). On- vs. off-duty is a recorded field, not an
exclusion — an off-duty officer who intervenes *as police* still counts. What
happens *after* the shooting — a criminal charge, discipline, resignation, a
lawsuit, or a clearance — is recorded (in `dept_response`), not an exclusion.
The test is only whether the shooter was an officer acting as police when they
fired, the same standard applied to officer-involved shootings of people.

**Excluded:** animal-control officers, civilians, security guards, game wardens
acting in a wildlife capacity; **retired/former officers, and off-duty officers
acting as private citizens in a personal dispute**;
dogs shot by a suspect rather than police; non-firearm force; mercy killings of
injured wildlife or livestock; animals that were not dogs; multi-topic news
roundups that only mention a shooting in passing; and stories about policy,
training, procurement, or litigation with no specific incident described.

## Data schema (`datasets/dog-shootings.csv`)

`id, date_added, incident_date, date_precision, city, county, state, agency_name,
agency_type, on_duty, officer_named, dogs_fired_at, dog_targeted, dog_outcome, dog_breed_reported,
dog_restrained, circumstance, warrant_type, human_injured_by_fire, dept_response,
litigation, summary, source_name, source_url, additional_sources, discovery,
official_ref, official_url, confidence, prompt_version, reviewed`

- `dog_targeted` ∈ {yes, no, unknown}: `yes` = fired at/toward the dog; `no` = hit
  by rounds aimed at someone else. Every row before 2026-09-24 is `yes`.
- **Classifier regression check:** `python scripts/eval_dog_classifier.py --repeat 3`
  (14 scope edge cases, about $0.03). Run it after any prompt change.
- `discovery` ∈ {media, official, both} — found in the news, only in a police
  department's own records, or in both. Every row before 2026-09-24 is `media`.
- `official_ref` / `official_url` — the agency's case id (`LAPD NRF035-26`,
  `PPD 26-03`) and its record page. `official_ref` is the idempotency key: a
  record already in the CSV is never re-added.

- `reviewed` ∈ {yes, no} — `no` on every automated row; a person sets it to `yes`
  after checking the row against its sources. The dashboard shows "N of M
  human-verified" and tags unverified incidents.
- `agency_type` ∈ {municipal PD, county SO, state, federal, tribal, campus, other, unknown}
- `dog_outcome` ∈ {killed, injured-survived, injured-euthanized, unharmed, unknown}
- `circumstance` ∈ {welfare check, warrant service, wrong address, traffic stop,
  loose/roaming dog, unrelated call response, pursuit, domestic call, noise
  complaint, other, unknown}
- `officer_named` — an individual officer's name is stored **only** when the source
  attributes it to an official record (charging document, lawsuit, department
  statement, disciplinary record). Otherwise blank. The agency is always named.
- `dog_breed_reported` — verbatim from the source (breed IDs in news are unreliable).

## Human review & corrections

Git history is the audit log. An automated run **never overwrites an existing
row's fields** — it only appends new rows and grows `additional_sources` — so
hand edits are safe against the daily job. `validate` runs on the combined set
before every automated write, so a broken manual edit (bad enum, future date,
duplicate `id`) aborts that run rather than corrupting the data.

**To fix a field or vet a row:** edit `datasets/dog-shootings.csv` directly, set
`reviewed` to `yes` once you've checked the row against its sources, then
`python scripts/generate_dog_shooting_tracker.py --rebuild-json` and commit.

**To remove a false positive:** delete the row (leave the other `id`s alone —
gaps are fine), then blocklist its article(s) so nothing re-creates it:

```bash
python scripts/generate_dog_shooting_tracker.py --exclude <source_url> [<additional_source_url> ...]
python scripts/generate_dog_shooting_tracker.py --rebuild-json
```

`--exclude` appends the URLs (with a dated note) to
`datasets/dog-shootings-excluded.json`; `discover()` and the classify loop skip
excluded URLs the same way they skip already-seen ones. You can also edit that
JSON by hand — it accepts a bare list of URL strings or `{"url": ..., "note": ...}`
objects.

Do **not** add a CSV column without also adding it to `CSV_FIELDS` in the script
— `save_incidents()` drops unknown columns on the next automated run.

Corrections from outside can also come in via a
[GitHub issue](https://github.com/jnixy/website/issues).

## Running

```bash
# Daily run (last 3 days) — needs ANTHROPIC_API_KEY
python scripts/generate_dog_shooting_tracker.py

# Test the news queries only, no LLM calls, nothing written
python scripts/generate_dog_shooting_tracker.py --discover-only --days 14

# Wider historical sweep, capped article count
python scripts/generate_dog_shooting_tracker.py --days 60 --limit 200

# Classify but write nothing
python scripts/generate_dog_shooting_tracker.py --dry-run

# Rebuild static/data/dog-shooting-tracker.json from the CSV (after manual edits)
python scripts/generate_dog_shooting_tracker.py --rebuild-json

# Blocklist a false-positive article (after deleting its row), then exit
python scripts/generate_dog_shooting_tracker.py --exclude https://example.com/story
```

CI: `.github/workflows/update-dog-shooting-tracker.yml`. Requires the
`ANTHROPIC_API_KEY` repository secret.

**The daily cron is on** (enabled 2026-09-03, `41 6 * * *` UTC).
`workflow_dispatch` takes `days`, `limit`, `discover_only`, `dry_run`, and
`official_only` inputs, so you can do a no-cost query check (`discover_only`) or
a no-write classifier check (`dry_run`) without touching the dataset.

## Agency records (cross-checking the news)

Some departments publish incident-level officer-involved-shooting lists that
include shootings of dogs. `scripts/dog_tracker_official.py` fetches and parses
them (one parser + one `OFFICIAL_SOURCES` entry per agency; no LLM calls there).
The main script then runs each record through the **same classifier** as a news
article (so the off-duty / scope rules apply unchanged) and matches it:

1. `official_ref` already in the CSV → skip.
2. Same state + same agency + `incident_date` within a day → that row.
3. Otherwise the usual LLM dedupe adjudicates.

A match sets `discovery=both` and fills `official_ref`/`official_url`. No other
field is touched, so reviewed rows stay intact. No match adds a row with
`discovery=official`, `reviewed=no`. A news article that later merges into an
agency-only row flips it to `both`. Classifier rejections are remembered in the
seen-URLs file as `official:<ref>`, so they are not re-billed each week. To
drop an agency-only row, delete it and `--exclude` its `official_url`.

```bash
python scripts/generate_dog_shooting_tracker.py --official --dry-run   # preview
python scripts/generate_dog_shooting_tracker.py --official             # write
```

The scheduled workflow runs `--official` on **Mondays** after the news pass. A
page that fails to fetch or parse only prints a warning (and a parser that
returns 0 records from a large page prints `layout changed?`). An API failure on
more than half the records fails the run, the same as the news path.

| Agency | Source | Notes |
|---|---|---|
| Los Angeles PD | 2026 O.I.S. table (`Name` = "Dog") → newsroom release | **URL slug is per year — update it each January** |
| Philadelphia PD | `/ois/` index, narratives inline | Also lists earlier years; only 2026+ is ingested |
| DC Metropolitan PD | dmpsj.dc.gov newsroom, pages 0-2: Deputy Mayor's letters to the Council titled "Firearm Discharge at an Animal … on <date>" | **Match-only.** The letters (and their PDFs) never name the species, so a letter only links to an existing DC row within a day; an unmatched one prints `!! UNMATCHED` every run until someone adds a row or `--exclude`s the URL. Posting lags weeks to months. No 2026 animal letters as of 2026-09-25 |
| Seattle PD | SPD Blotter WordPress REST search (`/wp-json/wp/v2/posts?search=dog&after=2026-01-01`) | Standalone releases (ref = `Incident Number`) and daily roundups (ref = each `#2026-NNNNN/...` header); a segment is kept only if a dog and a shot share a sentence. Record date = the post date (releases say "this afternoon") or the roundup's title date. One event can appear in both under different numbers; the second matches the first by date. Found 2026-01-30 Freeway Park, which the news pass had missed |

On 2026-09-24, LAPD listed 4 dog shootings in 2026 and the news had found all 4.
Philadelphia PD listed 4 on-duty ones (plus 1 off-duty, which is out of scope),
and the news had found none of them.

### Annual reports (manual)

Some agencies report dog shootings only in an annual PDF, e.g. the Milwaukee
Fire & Police Commission use-of-force report (bot-blocked for curl, so download
it in a browser). These are entered by hand into
`datasets/dog-shootings-official-staging.csv`
(`agency_name, city, state, official_ref, incident_date, location, url, text`,
where `text` is the report's description of the incident) and ingested with
`--official-staging` (same classify + match path). Only incident-level entries
work; an aggregate count ("officers shot 12 dogs") can't be matched and belongs
in the page notes, not the CSV.

**Q1 2027 checklist** (2026 reports):
- [ ] Milwaukee FPC use-of-force report
- [ ] candidates from `quality_reports/dog-tracker-official-source-candidates.md`

**GDELT was dropped (2026-09-21).** It was a best-effort second discovery
source, but it timed out or returned 429 on nearly every request — from GitHub
Actions (shared runner IPs hit its per-IP rate limiter) and later from a local IP
too — and cost about six minutes of timeouts per daily run for no candidates.
Google News is now the only discovery source. If its breadth proves too thin,
widen `GOOGLE_NEWS_PHRASINGS` (or, as a last resort, front GDELT with a proxy on
a non-Actions IP); more retries will not help. `generate_police_shooting_news.py`
still queries GDELT.

**Exit codes.** The script exits non-zero only on real failures: `ANTHROPIC_API_KEY`
missing, >50% of classified articles erroring, or a validation problem. A quiet
news window with no new candidates is not one of these.

## Limitations

A media-derived undercount. Litigated and body-camera cases are over-covered;
rural and non-English incidents are under-covered; claims about a dog's behavior
usually originate with the officer or department. Counts and the state map reflect
where incidents are reported and found, not necessarily where they occur.

A 2026-09-02 comparison against a parallel OIAS tracker (raw Bing + Google News,
no LLM, no dedup, no scope filter) found three in-scope incidents our discovery
had missed entirely — headlines using an adjective inside the verb phrase
("deputies shoot **aggressive** dog"), a "kills" verb, or a passive
construction. `GOOGLE_NEWS_PHRASINGS` and `HEADLINE_ONLY_NOTE` were widened to
cover those forms. The other direction held up: our set caught a pack-attack
incident the parallel tracker missed. Recall is bounded by Google News
being the only discovery source (see below).

## Historical data (deliberately not ingested)

The [Puppycide Database Project](https://github.com/puppycidedatabaseproject/pdb-database)
(~1,260 records, ~2011–2016, public domain) and the Hoffman & Muro
[1998–2014 spreadsheet](https://archive.org/details/1998THRU2014DOGSSHOTBYPOLICE)
are the main prior efforts. They are linked from the dashboard for readers but not
merged in: their definitions are broader and inconsistent (all pets, sometimes
non-dog animals), and their coding is unaudited.
