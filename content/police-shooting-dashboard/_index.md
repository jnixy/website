---
title: "Fatal Officer-Involved Shooting Dashboard"
summary: "Interactive dashboard of national police-involved shooting trends, built on the Mapping Police Violence dataset"
type: page
reading_time: false
share: true
profile: false
comments: false
---

An interactive look at national trends in fatal police shootings, built with the [Mapping Police Violence](https://mappingpoliceviolence.us) dataset (updated weekly).

{{% alert note %}}
Looking for recent news or academic research on police shootings instead? See the [news tracker](/police-shooting-news/) and [research tracker](/police-shooting-research/).
{{% /alert %}}

---

<link rel="stylesheet" href="/css/mpv-dashboard.css">

<div id="mpv-dashboard" class="mpv-dashboard-container">
  <div id="mpv-loading" class="mpv-loading">
    <p>Loading dashboard data...</p>
  </div>
  <div id="mpv-error" class="mpv-error" style="display:none;"></div>
  <div id="mpv-dashboard-content" style="display:none;">
    <div id="mpv-meta" class="mpv-meta"></div>
    <div id="mpv-stats" class="mpv-stats-row"></div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Incidents by Year</h3>
        <div id="chart-yearly" class="mpv-chart"></div>
      </div>
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Cumulative Incidents by Year (Year-over-Year Trajectory)</h3>
        <div id="chart-trajectory" class="mpv-chart"></div>
      </div>
    </div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title" id="heatmap-title">Daily Incidents Calendar</h3>
        <div id="chart-heatmap" class="mpv-chart"></div>
        <p class="mpv-chart-note">Most recent ~2 weeks may be undercounted due to MPV's reporting lag.</p>
      </div>
    </div>
    <div class="mpv-chart-grid mpv-two-col">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Victim Race/Ethnicity</h3>
        <div id="chart-race" class="mpv-chart"></div>
      </div>
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Armed Status</h3>
        <div id="chart-armed" class="mpv-chart"></div>
      </div>
    </div>
    <div class="mpv-chart-grid mpv-two-col">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Circumstances of Encounter</h3>
        <div id="chart-encounter" class="mpv-chart"></div>
      </div>
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Alleged Weapon</h3>
        <div id="chart-weapon" class="mpv-chart"></div>
      </div>
    </div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Fatal Shootings per 100,000 Population, by Race</h3>
        <div id="chart-disparity" class="mpv-chart"></div>
        <p class="mpv-chart-note" id="disparity-caption"></p>
      </div>
    </div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Fatal Shootings per 100,000 Arrests, by Race (2013–2025)</h3>
        <div id="chart-arrest-rate" class="mpv-chart"></div>
        <p class="mpv-chart-note" id="arrest-rate-caption"></p>
      </div>
    </div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Fatal Shootings per 1,000,000 Population, by State (2013–Present)</h3>
        <div id="chart-states" class="mpv-chart"></div>
        <p class="mpv-chart-note" id="state-map-caption"></p>
      </div>
    </div>
    <div class="mpv-chart-grid">
      <div class="mpv-chart-card">
        <h3 class="mpv-chart-title">Top 10 Agencies</h3>
        <div id="chart-agencies" class="mpv-chart"></div>
      </div>
    </div>
  </div>
</div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="/js/mpv-dashboard.js"></script>
