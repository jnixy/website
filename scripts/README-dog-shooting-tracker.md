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
| discover | Google News RSS (`GOOGLE_NEWS_PHRASINGS`, the primary source) + GDELT DOC 2.0 API (`GDELT_QUERIES`, best-effort). Blocked domains, non-US TLDs, already-seen URLs, and human-excluded URLs (`datasets/dog-shootings-excluded.json`) are dropped. Queries are single quoted phrases. A GDELT query whose retries all fail is logged `FAIL` and kept distinct from a genuine zero, but does **not** fail the run — GDELT is unreliable from GitHub Actions and Google News carries discovery. |
| extract | Article body text via `trafilatura`. If the page is video- or script-only (no body text), the article is **not** dropped — it goes to classify with a headline-only flag and stricter rules (a passive headline — "dog shot by officers", "…her dog, who was shot by police" — still qualifies; a headline silent on who shot, or naming a civilian shooter, does not). |
| classify | One `claude-haiku-4-5` call per article (forced tool call), given the article's **publication date** as the anchor for resolving "Thursday" / "this week". Returns `qualifies` plus structured fields. `PROMPT_VERSION` is stamped on every row. Date guards: the model must quote its evidence in `incident_date_source` (no quote → date blanked); a resolved year more than one year before publication with `litigation = none` is dropped (mis-resolved relative date). Enum drift is coerced onto the vocab. A row with no `state` is dropped as unplaceable. |
| dedupe | Candidates are blocked by `state` (or `city` when the row has no state) — no date window. One `claude-haiku-4-5` call decides same-incident **from the summary alone, ignoring dates** (they are often wrong): same agency, same metro, same described sequence of events / named officials. A match appends the URL to the existing row's `additional_sources`; no new row. |
| store | Append new incidents to `datasets/dog-shootings.csv` (`reviewed = no`). Update `datasets/dog-shootings-seen-urls.json`. Existing rows' fields are never overwritten — only `additional_sources` grows on a dedupe match. |
| validate | Parse check, no future dates, enum vocab, no duplicate ids, no blocklisted source domains. Aborts the write if >50% of processed articles errored. |
| emit | `static/data/dog-shooting-tracker.json` (aggregates + recent incidents) and `static/data/dog-shootings.csv` (published copy). |

## Scope

**Included:** a currently-serving sworn law enforcement officer — municipal
police, county sheriff/deputy, state police, federal, tribal, or campus — who,
**while acting as police** (a call, stop, arrest, patrol, warrant, or otherwise
handling a police matter), discharged a firearm at or toward a dog. Any outcome
counts (killed, wounded, missed). On- vs. off-duty is a recorded field, not an
exclusion — an off-duty officer who intervenes *as police* still counts.

**Excluded:** animal-control officers, civilians, security guards, game wardens
acting in a wildlife capacity; **retired/former officers, and off-duty officers
acting as private citizens in a personal dispute**; **any officer charged with a
crime for the shooting** (it was not a lawful act in a law-enforcement capacity);
non-firearm force; an officer's own police K-9 or a service dog; mercy killings of
injured wildlife or livestock; animals that were not dogs; multi-topic news
roundups that only mention a shooting in passing; and stories about policy,
training, procurement, or litigation with no specific incident described.

## Data schema (`datasets/dog-shootings.csv`)

`id, date_added, incident_date, date_precision, city, county, state, agency_name,
agency_type, on_duty, officer_named, dogs_fired_at, dog_outcome, dog_breed_reported,
dog_restrained, circumstance, warrant_type, human_injured_by_fire, dept_response,
litigation, summary, source_name, source_url, additional_sources, confidence,
prompt_version, reviewed`

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

**The daily cron is currently commented out.** Until the discovery queries are
tuned and the classifier has been checked against hand-labelled articles, an
unattended run would auto-commit unvetted rows. Run it by hand from the Actions
tab instead — `workflow_dispatch` takes `days`, `limit`, `discover_only`, and
`dry_run` inputs, so you can do a no-cost query check (`discover_only`) or a
no-write classifier check (`dry_run`) without touching the dataset. Re-enable
the `schedule:` block once precision is acceptable.

**GDELT is unreliable from GitHub Actions** — runners share an IP pool that
GDELT rate-limits, so CI runs on 2026-09-01 saw it 429 and connect-timeout on
nearly every request (`generate_police_shooting_news.py` hits the same wall).
The GDELT leg is deliberately small (7 non-overlapping queries, `(10, 30)`s
timeout, 2 retries) so a mostly-failing leg still finishes in a few minutes, and
its failure is logged but **does not fail the run**. Google News is the primary
source. If Google-News-only breadth proves too thin after a few real runs, the
fix is a GDELT proxy on a non-Actions IP (Val.town / Cloudflare Worker), not
more retries. GDELT is also unreachable from some university networks, so a local
`--discover-only` may return Google News only.

**Exit codes.** The script exits non-zero only on real failures: `ANTHROPIC_API_KEY`
missing, >50% of classified articles erroring, or a validation problem. A GDELT
outage is not one of these.

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
incident the parallel tracker missed. Recall is still bounded by GDELT being
unusable from Actions (see below).

## Historical data (deliberately not ingested)

The [Puppycide Database Project](https://github.com/puppycidedatabaseproject/pdb-database)
(~1,260 records, ~2011–2016, public domain) and the Hoffman & Muro
[1998–2014 spreadsheet](https://archive.org/details/1998THRU2014DOGSSHOTBYPOLICE)
are the main prior efforts. They are linked from the dashboard for readers but not
merged in: their definitions are broader and inconsistent (all pets, sometimes
non-dog animals), and their coding is unaudited.
