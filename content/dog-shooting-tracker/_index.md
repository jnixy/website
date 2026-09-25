---
title: "Dogs Shot by Police"
summary: "A running count of incidents in which U.S. law enforcement officers shot at, or shot, a dog"
type: page
reading_time: false
share: true
profile: false
comments: false
image:
  preview_only: true
---

How often do U.S. police officers shoot dogs? The only honest answer is no one knows for sure. There's no official data, and various unofficial data collection efforts are dated or inadequate. But every so often I see stories pop up (like [this one](https://www.thetrace.org/2026/06/police-dog-shootings-how-often/) from June 2026) regurgitating an [old claim from a DOJ COPS Office Employee](https://perma.cc/Y9JJ-2FSE) that police shoot ~10,000 dogs per year, or 25-30 per day on average. (In comparison, [best estimates](https://ajph.aphapublications.org/doi/pdf/10.2105/AJPH.2023.307560) are that police shoot ~1800 *people* per year.)

I've always been skeptical of this claim, but without good data who knows? So I built a running record of incidents in which a sworn U.S. law enforcement officer discharged a firearm at or toward a dog (whether the dog was killed, injured, or missed), or whose gunfire struck a dog. It is built automatically from news coverage, cross-checked against police records in a few cities, and updated daily.

{{% alert note %}}
This tracker is assembled from news reports we monitor automatically, so these numbers represent a **floor, not a full count** — incidents in news deserts, or that were never reported, are missing. Earlier volunteer efforts — the [Puppycide Database Project](https://github.com/puppycidedatabaseproject/pdb-database) and a citizen-compiled [1998–2014 spreadsheet](https://archive.org/details/1998THRU2014DOGSSHOTBYPOLICE) — stopped years ago and used broader, less consistent definitions (e.g., animals that were not dogs, mercy killings of animals struck by vehicles). See the notes below the charts for scope and limitations.
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
        A scheduled job searches Google News for coverage of police shooting dogs, pulls the
        article text, and uses a language model to decide whether the story describes a specific incident
        that fits the scope below and to pull out structured details (date, location, agency, circumstance,
        outcome). A second model pass merges multiple articles about the same event into one record.
        Every record starts machine-extracted and is marked <strong>Unverified</strong> until a person
        checks it against the sources; the line above shows how many have been verified so far. The full
        dataset is downloadable as CSV, and corrections are welcome via
        <a href="https://github.com/jnixy/website/issues">GitHub issues</a>.
      </p>
      <h3>Checking the news against police records</h3>
      <p>
        A few police departments post their own lists of officer-involved shootings, and some of those
        lists include shootings of dogs. Once a week the tracker compares those lists with what the news
        turned up. An incident that appears in a department's records but never made the news is added and
        tagged <strong>Agency record</strong>. The comparison also gives a rough sense of how much news
        coverage misses. Right now the tracker checks the Los Angeles, Philadelphia, and Seattle police departments, plus Washington,
        DC's Metropolitan Police Department (DC's records say "animal," not "dog," so they only confirm
        incidents found elsewhere).
        Know of another department that publishes incident-level records? Let me know via
        <a href="https://github.com/jnixy/website/issues">GitHub issues</a>.
      </p>
      <p class="dst-chart-note" id="dst-coverage"></p>
      <h3>What counts</h3>
      <p>
        <strong>Included:</strong> a sworn law enforcement officer (municipal police, county sheriff/deputy,
        state police, federal, tribal, or campus), acting as police, fired a gun at or toward a dog, whether
        the dog was killed, wounded, or missed. Also included: a dog struck by police gunfire aimed at someone
        else, such as a family dog or a police K-9 hit during a shootout; these are tagged
        <em>Hit by fire aimed at someone else</em>. Whether the shooting was justified, or led to charges,
        discipline, or a lawsuit, does not affect inclusion.
        <strong>Excluded:</strong> animal-control officers and civilians; retired officers, and off-duty
        officers acting as private citizens; dogs shot by a suspect rather than police; non-firearm force;
        mercy killings of wildlife or livestock (a deer hit by a car, for example); animals that were not
        dogs; and stories about policy, training, or litigation with no specific incident described.
      </p>
      <h3>Limitations</h3>
      <p>
        This is a mostly media-derived undercount. Incidents that draw a lawsuit or body-camera release are covered
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
