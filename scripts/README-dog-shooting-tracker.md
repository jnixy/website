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
| discover | GDELT DOC 2.0 API + Google News RSS, a fixed query list (`GDELT_QUERIES`, `GOOGLE_NEWS_PHRASINGS`). Blocked domains and already-seen URLs are dropped. |
| extract | Article body text via `trafilatura`. |
| classify | One `claude-haiku-4-5` call per article (forced tool call). Returns `qualifies` plus structured fields. The system prompt (`CLASSIFY_SYSTEM`) encodes the scope below; `PROMPT_VERSION` is stamped on every row. |
| dedupe | For a qualifying article, block existing rows by `state` + `incident_date` within 21 days, then one `claude-haiku-4-5` call decides same-incident. A match appends the URL to the existing row's `additional_sources`; no new row. |
| store | Append to `data/dog-shootings.csv`. Update `data/dog-shootings-seen-urls.json`. |
| validate | Parse check, no future dates, enum vocab, no duplicate ids, no blocklisted source domains. Aborts the write if >50% of processed articles errored. |
| emit | `static/data/dog-shooting-tracker.json` (aggregates + recent incidents) and `static/data/dog-shootings.csv` (published copy). |

## Scope

**Included:** a sworn law enforcement officer — municipal police, county
sheriff/deputy, state police, federal, tribal, or campus — discharged a firearm at
or toward a dog. Any outcome counts (killed, wounded, missed). On- vs. off-duty is
a recorded field, not an exclusion.

**Excluded:** animal-control officers, civilians, security guards, game wardens
acting in a wildlife capacity; non-firearm force; an officer's own police K-9 or a
service dog; mercy killings of injured wildlife or livestock; animals that were not
dogs; and stories about policy, training, procurement, or litigation with no
specific incident described.

## Data schema (`data/dog-shootings.csv`)

`id, date_added, incident_date, date_precision, city, county, state, agency_name,
agency_type, on_duty, officer_named, dogs_fired_at, dog_outcome, dog_breed_reported,
dog_restrained, circumstance, warrant_type, human_injured_by_fire, dept_response,
litigation, summary, source_name, source_url, additional_sources, confidence,
prompt_version`

- `agency_type` ∈ {municipal PD, county SO, state, federal, tribal, campus, other, unknown}
- `dog_outcome` ∈ {killed, injured-survived, injured-euthanized, unharmed, unknown}
- `circumstance` ∈ {welfare check, warrant service, wrong address, traffic stop,
  loose/roaming dog, unrelated call response, pursuit, domestic call, noise
  complaint, other, unknown}
- `officer_named` — an individual officer's name is stored **only** when the source
  attributes it to an official record (charging document, lawsuit, department
  statement, disciplinary record). Otherwise blank. The agency is always named.
- `dog_breed_reported` — verbatim from the source (breed IDs in news are unreliable).

## Corrections

Edit `data/dog-shootings.csv` directly and commit, or open a
[GitHub issue](https://github.com/jnixy/website/issues). Git history is the audit
log. After editing the CSV, run `--rebuild-json` to refresh the dashboard.

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
```

CI: `.github/workflows/update-dog-shooting-tracker.yml`. Requires the
`ANTHROPIC_API_KEY` repository secret.

**The daily cron is currently commented out.** Until the discovery queries are
tuned and the classifier has been checked against hand-labelled articles, an
unattended run would auto-commit unvetted rows. Run it by hand from the Actions
tab instead — `workflow_dispatch` takes `days`, `limit`, `discover_only`, and
`dry_run` inputs, so you can do a no-cost query check (`discover_only`) or a
no-write classifier check (`dry_run`) without touching the dataset. Re-enable
the `schedule:` block once precision is acceptable.

Note that GDELT is unreachable from some university networks, so `--discover-only`
run locally may return Google News results only; the CI run is the reliable test
of the GDELT leg.

## Limitations

A media-derived undercount. Litigated and body-camera cases are over-covered;
rural and non-English incidents are under-covered; claims about a dog's behavior
usually originate with the officer or department. Counts and the state map reflect
where incidents are reported and found, not necessarily where they occur.

## Historical data (deliberately not ingested)

The [Puppycide Database Project](https://github.com/puppycidedatabaseproject/pdb-database)
(~1,260 records, ~2011–2016, public domain) and the Hoffman & Muro
[1998–2014 spreadsheet](https://archive.org/details/1998THRU2014DOGSSHOTBYPOLICE)
are the main prior efforts. They are linked from the dashboard for readers but not
merged in: their definitions are broader and inconsistent (all pets, sometimes
non-dog animals), and their coding is unaudited.
