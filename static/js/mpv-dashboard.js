/**
 * MPV Dashboard — renders charts from /data/mpv-dashboard.json using
 * Plotly.js (loaded separately via CDN script tag). Theme-aware: reads
 * light/dark state the same way the rest of the site does and re-colors
 * charts if the theme toggles at runtime.
 */
(function () {
  var PALETTE = ['#4caf50', '#1565c0', '#c62828', '#ef6c00', '#7b1fa2', '#00897b', '#5e35b1', '#757575'];
  var DATA_URL = '/data/mpv-dashboard.json';

  function isDarkMode() {
    var root = document.documentElement;
    var body = document.body;
    if (root.classList.contains('dark') || body.classList.contains('dark')) return true;
    if (root.classList.contains('light') || body.classList.contains('light')) return false;
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  function themeColors() {
    var dark = isDarkMode();
    return {
      font: dark ? '#e0e0e0' : '#1a1a1a',
      grid: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
      muted: dark ? '#999' : '#666'
    };
  }

  function baseLayout(extra) {
    var colors = themeColors();
    var layout = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: colors.font, size: 12 },
      margin: { t: 10, r: 20, l: 50, b: 40 },
      xaxis: { gridcolor: colors.grid, zerolinecolor: colors.grid },
      yaxis: { gridcolor: colors.grid, zerolinecolor: colors.grid },
      showlegend: false
    };
    return Object.assign(layout, extra || {});
  }

  var PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

  function renderStats(data) {
    var stats = data.stats;
    var delta = stats.current_year_to_date - stats.prior_year_same_point;
    var deltaPct = stats.prior_year_same_point > 0
      ? Math.round((delta / stats.prior_year_same_point) * 100)
      : 0;
    var deltaClass = delta > 0 ? 'up' : (delta < 0 ? 'down' : '');
    var deltaSign = delta > 0 ? '+' : '';
    var asOfShort = formatDateTime(stats.as_of_date, { omitYear: true });

    var html = '' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + stats.total_incidents.toLocaleString() + '</div>' +
        '<div class="mpv-stat-label">Total Incidents (2013–present)</div>' +
      '</div>' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + stats.current_year_to_date.toLocaleString() + '</div>' +
        '<div class="mpv-stat-label">' + stats.current_year + ' YTD (as of ' + asOfShort + ')</div>' +
        '<div class="mpv-stat-delta ' + deltaClass + '">' + deltaSign + deltaPct + '% vs. ' + stats.prior_year + ' same point</div>' +
      '</div>' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + data.source_last_incident_date + '</div>' +
        '<div class="mpv-stat-label">Most Recent Incident</div>' +
      '</div>';

    document.getElementById('mpv-stats').innerHTML = html;
    document.getElementById('mpv-meta').innerHTML =
      escapeHtml(data.scope) + ' &middot; year-to-date figures use a ' + stats.lag_days +
      '-day reporting-lag adjustment, so both years are compared as of ' + asOfShort + '.<br>' +
      'Data: <a href="https://mappingpoliceviolence.us" target="_blank" rel="noopener">Mapping Police Violence</a> ' +
      '&middot; Dashboard generated ' + formatDateTime(data.generated_at) +
      ' &middot; <a class="mpv-download-link" href="https://mappingpoliceviolence.us" target="_blank" rel="noopener">Download the full incident-level dataset</a>';
  }

  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatDateTime(iso, opts) {
    // Bare "YYYY-MM-DD" strings are parsed by `new Date()` as UTC midnight;
    // toLocaleDateString then renders in the browser's local timezone,
    // which rolls the displayed date back a day for any timezone west of
    // UTC. Force local-time parsing for date-only strings so the date
    // shown always matches the date the server meant.
    var parseTarget = (typeof iso === 'string' && iso.indexOf('T') === -1)
      ? iso + 'T00:00:00'
      : iso;
    var d = new Date(parseTarget);
    if (isNaN(d.getTime())) return iso;
    var fmt = { month: 'short', day: 'numeric' };
    if (!(opts && opts.omitYear)) fmt.year = 'numeric';
    return d.toLocaleDateString('en-US', fmt);
  }

  function renderYearlyTrend(data) {
    var years = data.yearly_counts.map(function (d) { return d.year; });
    var counts = data.yearly_counts.map(function (d) { return d.count; });
    Plotly.newPlot('chart-yearly', [{
      x: years,
      y: counts,
      type: 'bar',
      marker: { color: PALETTE[0] }
    }], baseLayout({ yaxis: { title: 'Incidents', gridcolor: themeColors().grid } }), PLOTLY_CONFIG);
  }

  function renderTrajectory(data) {
    var traj = data.cumulative_trajectory;
    var currentYear = data.stats.current_year;
    var traces = traj.series.map(function (s, i) {
      var isCurrent = s.year === currentYear;
      return {
        x: traj.months,
        y: s.cumulative_by_month,
        type: 'scatter',
        mode: 'lines+markers',
        name: String(s.year),
        line: { color: PALETTE[i % PALETTE.length], width: isCurrent ? 4 : 2 },
        opacity: isCurrent ? 1 : 0.55
      };
    });
    Plotly.newPlot('chart-trajectory', traces, baseLayout({
      showlegend: true,
      legend: { orientation: 'h', y: -0.2 },
      yaxis: { title: 'Cumulative Incidents', gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);
  }

  function renderBreakdown(elementId, breakdown) {
    var labels = breakdown.map(function (d) { return d.label; });
    var counts = breakdown.map(function (d) { return d.count; });
    Plotly.newPlot(elementId, [{
      x: counts,
      y: labels,
      type: 'bar',
      orientation: 'h',
      marker: { color: labels.map(function (_, i) { return PALETTE[i % PALETTE.length]; }) }
    }], baseLayout({
      margin: { t: 10, r: 20, l: 140, b: 40 },
      yaxis: { autorange: 'reversed', gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);
  }

  function renderHeatmap(data) {
    var hm = data.heatmap;
    var nWeeks = hm.counts[0].length;
    var weekIndices = [];
    for (var i = 0; i < nWeeks; i++) weekIndices.push(i);

    var titleEl = document.getElementById('heatmap-title');
    if (titleEl) titleEl.textContent = 'Daily Incidents — ' + hm.year + ' Calendar';

    Plotly.newPlot('chart-heatmap', [{
      z: hm.counts,
      x: weekIndices,
      y: hm.day_labels,
      type: 'heatmap',
      colorscale: [[0, 'rgba(76,175,80,0.08)'], [1, '#2e7d32']],
      showscale: false,
      hovertemplate: '%{y}, week of %{x}<br>%{z} incidents<extra></extra>'
    }], baseLayout({
      margin: { t: 10, r: 20, l: 50, b: 30 },
      xaxis: {
        tickvals: hm.month_starts.map(function (m) { return m.week_index; }),
        ticktext: hm.month_starts.map(function (m) { return m.month; }),
        gridcolor: themeColors().grid
      },
      yaxis: { autorange: 'reversed', gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);
  }

  function renderTopN(elementId, breakdown) {
    var top = breakdown.slice(0, 10).reverse();
    var labels = top.map(function (d) { return d.label; });
    var counts = top.map(function (d) { return d.count; });
    Plotly.newPlot(elementId, [{
      x: counts,
      y: labels,
      type: 'bar',
      orientation: 'h',
      marker: { color: PALETTE[0] }
    }], baseLayout({
      margin: { t: 10, r: 20, l: 190, b: 40 }
    }), PLOTLY_CONFIG);
  }

  function renderDisparity(data) {
    var rates = data.disparity_rates;
    var labels = rates.map(function (d) { return d.race; });
    var values = rates.map(function (d) { return d.rate_per_100k; });
    var colors = rates.map(function (d) { return d.race === 'White' ? '#757575' : PALETTE[2]; });

    Plotly.newPlot('chart-disparity', [{
      x: values,
      y: labels,
      type: 'bar',
      orientation: 'h',
      marker: { color: colors },
      hovertemplate: '%{y}: %{x} per 100,000<extra></extra>'
    }], baseLayout({
      margin: { t: 10, r: 20, l: 140, b: 40 },
      yaxis: { autorange: 'reversed', gridcolor: themeColors().grid },
      xaxis: { title: 'Rate per 100,000 population', gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);

    var highest = null;
    rates.forEach(function (r) {
      if (r.race !== 'White' && (!highest || r.disparity_vs_white > highest.disparity_vs_white)) highest = r;
    });
    var captionEl = document.getElementById('disparity-caption');
    if (captionEl && highest) {
      captionEl.textContent = highest.race + ' people are killed by police gunfire at ' +
        highest.disparity_vs_white.toFixed(1) + '× the per-capita rate of white people ' +
        '(2020 Census population; national figures, all years combined).';
    }
  }

  function renderAgencyRates(data) {
    var top = data.agency_rates.slice(0, 10).reverse();
    var labels = top.map(function (d) { return d.agency + ' (' + d.state + ')'; });
    var values = top.map(function (d) { return d.rate_per_10k_arrests; });
    Plotly.newPlot('chart-agency-rate', [{
      x: values,
      y: labels,
      type: 'bar',
      orientation: 'h',
      marker: { color: PALETTE[1] },
      hovertemplate: '%{y}: %{x} per 10k arrests<extra></extra>'
    }], baseLayout({
      margin: { t: 10, r: 20, l: 220, b: 40 },
      xaxis: { title: 'Shootings per 10,000 arrests', gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);

    var years = data.agency_rate_years || [];
    var captionEl = document.getElementById('agency-rate-caption');
    if (captionEl && years.length === 2) {
      captionEl.textContent = 'Limited to the ~106 municipal police departments MPV tracks arrest data for ' +
        '(excludes county sheriffs, state police, and federal agencies) with at least 5 shooting deaths in ' +
        years[0] + '–' + years[1] + ', the window covered by the arrest-volume data.';
    }
  }

  function renderAll(data) {
    renderStats(data);
    renderYearlyTrend(data);
    renderTrajectory(data);
    renderBreakdown('chart-race', data.race_breakdown);
    renderBreakdown('chart-armed', data.armed_status_breakdown);
    renderBreakdown('chart-encounter', data.encounter_breakdown);
    renderBreakdown('chart-weapon', data.weapon_breakdown);
    renderHeatmap(data);
    renderDisparity(data);
    renderTopN('chart-states', data.top_states);
    renderTopN('chart-agencies', data.top_agencies);
    renderAgencyRates(data);
  }

  function relayoutAllForTheme() {
    var ids = ['chart-yearly', 'chart-trajectory', 'chart-race', 'chart-armed', 'chart-encounter',
      'chart-weapon', 'chart-heatmap', 'chart-disparity', 'chart-states', 'chart-agencies', 'chart-agency-rate'];
    var colors = themeColors();
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.data) {
        Plotly.relayout(id, {
          'font.color': colors.font,
          'xaxis.gridcolor': colors.grid,
          'yaxis.gridcolor': colors.grid
        });
      }
    });
  }

  function init() {
    var container = document.getElementById('mpv-dashboard');
    fetch(DATA_URL)
      .then(function (response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function (data) {
        document.getElementById('mpv-dashboard-content').style.display = '';
        document.getElementById('mpv-loading').style.display = 'none';
        renderAll(data);

        // Re-color charts if the site's theme toggles at runtime.
        var observer = new MutationObserver(relayoutAllForTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        if (window.matchMedia) {
          window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', relayoutAllForTheme);
        }
      })
      .catch(function (error) {
        console.error('Error loading MPV dashboard data:', error);
        document.getElementById('mpv-loading').style.display = 'none';
        var errEl = document.getElementById('mpv-error');
        errEl.style.display = '';
        errEl.textContent = 'Could not load dashboard data (' + error.message + '). Please try again later.';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
