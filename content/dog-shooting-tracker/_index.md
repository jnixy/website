---
title: "Police Shootings of Dogs"
summary: "A running, news-derived count of incidents in which U.S. law enforcement officers fired a gun at a dog"
type: page
reading_time: false
share: true
profile: false
comments: false
---

A running record of incidents in which a sworn U.S. law enforcement officer discharged a firearm at or toward a dog — killed, wounded, or missed. It is built automatically from news coverage and updated daily.

{{% alert note %}}
No government agency tracks how often police shoot dogs. This tracker is assembled from news reports we monitor automatically, so these numbers represent a **floor, not a full count** — incidents in news deserts, or that were never reported, are missing. Earlier volunteer efforts — the [Puppycide Database Project](https://github.com/puppycidedatabaseproject/pdb-database) and a citizen-compiled [1998–2014 spreadsheet](https://archive.org/details/1998THRU2014DOGSSHOTBYPOLICE) — stopped years ago and used broader, less consistent definitions (e.g., animals that were not dogs, mercy killings of animals struck by vehicles). See the notes below the charts for scope and limitations.
{{% /alert %}}

---

<link rel="stylesheet" href="/css/dog-shooting-tracker.css">

<div id="dst-dashboard" class="dst-container">
  <div id="dst-loading" class="dst-loading"><p>Loading tracker data…</p></div>
  <div id="dst-error" class="dst-error" style="display:none;"></div>
  <div id="dst-content" style="display:none;">
    <div id="dst-meta" class="dst-meta"></div>
    <div id="dst-stats" class="dst-stats-row"></div>
    <div id="dst-empty" class="dst-empty" style="display:none;">
      <p>No incidents have been recorded yet. The tracker is live; this page will fill in as qualifying news coverage is found and reviewed.</p>
    </div>
    <div id="dst-charts">
      <div class="dst-chart-grid">
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Incidents by Year</h3>
          <div id="dst-chart-yearly" class="dst-chart"></div>
          <p class="dst-chart-note">Earlier years are undercounted: automated news discovery reaches back only so far, and older local coverage is harder to find.</p>
        </div>
      </div>
      <div class="dst-chart-grid dst-two-col">
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Outcome for the Dog</h3>
          <div id="dst-chart-outcome" class="dst-chart"></div>
        </div>
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Circumstance of the Encounter</h3>
          <div id="dst-chart-circumstance" class="dst-chart"></div>
        </div>
      </div>
      <div class="dst-chart-grid dst-two-col">
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Type of Agency</h3>
          <div id="dst-chart-agency" class="dst-chart"></div>
        </div>
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Recorded Incidents by State</h3>
          <div id="dst-chart-states" class="dst-chart"></div>
          <p class="dst-chart-note" id="dst-state-caption"></p>
        </div>
      </div>
      <div class="dst-chart-grid">
        <div class="dst-chart-card">
          <h3 class="dst-chart-title">Most Recent Incidents</h3>
          <div id="dst-recent"></div>
        </div>
      </div>
    </div>
    <div class="dst-notes">
      <h3>How this is built</h3>
      <p>
        A scheduled job searches GDELT and Google News for coverage of police shooting dogs, pulls the
        article text, and uses a language model to decide whether the story describes a specific incident
        that fits the scope below and to pull out structured details (date, location, agency, circumstance,
        outcome). A second model pass merges multiple articles about the same event into one record.
        Every record starts machine-extracted and is marked <strong>Unverified</strong> until a person
        checks it against the sources; the line above shows how many have been verified so far. The full
        dataset is downloadable as CSV, and corrections are welcome via
        <a href="https://github.com/jnixy/website/issues">GitHub issues</a>.
      </p>
      <h3>What counts</h3>
      <p>
        <strong>Included:</strong> a sworn law enforcement officer (municipal police, county sheriff/deputy,
        state police, federal, tribal, or campus) fired a gun at or toward a dog, whether the dog was killed,
        wounded, or missed.
        <strong>Excluded:</strong> animal-control officers and civilians; non-firearm force; an officer's own
        police K-9 or a service dog; mercy killings of wildlife or livestock (a deer hit by a car, for
        example); animals that were not dogs; and stories about policy, training, or litigation with no
        specific incident described.
      </p>
      <h3>Limitations</h3>
      <p>
        This is a media-derived undercount. Incidents that draw a lawsuit or body-camera release are covered
        more heavily than those that do not; rural areas and non-English outlets are under-covered; and
        descriptions of a dog's behavior ("the dog charged") usually originate with the officer or department.
        Breed is recorded as the source described it, which is often unreliable. Counts and the state map
        reflect <em>where incidents are reported and found</em>, not necessarily where they most often occur.
        Every figure is current as of the "updated" date shown above.
      </p>
    </div>
  </div>
</div>

<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="/js/dog-shooting-tracker.js"></script>
