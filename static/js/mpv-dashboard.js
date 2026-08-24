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

    var html = '' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + stats.total_incidents.toLocaleString() + '</div>' +
        '<div class="mpv-stat-label">Total Incidents (2013–present)</div>' +
      '</div>' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + stats.current_year_to_date.toLocaleString() + '</div>' +
        '<div class="mpv-stat-label">' + stats.current_year + ' Year-to-Date</div>' +
        '<div class="mpv-stat-delta ' + deltaClass + '">' + deltaSign + deltaPct + '% vs. same point ' + (stats.current_year - 1) + '</div>' +
      '</div>' +
      '<div class="mpv-stat-tile">' +
        '<div class="mpv-stat-value">' + data.source_last_incident_date + '</div>' +
        '<div class="mpv-stat-label">Most Recent Incident</div>' +
      '</div>';

    document.getElementById('mpv-stats').innerHTML = html;
    document.getElementById('mpv-meta').innerHTML =
      'Data: <a href="https://mappingpoliceviolence.us" target="_blank" rel="noopener">Mapping Police Violence</a> ' +
      '&middot; Dashboard generated ' + formatDateTime(data.generated_at) +
      ' &middot; <a class="mpv-download-link" href="https://mappingpoliceviolence.us" target="_blank" rel="noopener">Download the full incident-level dataset</a>';
  }

  function formatDateTime(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
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
    Plotly.newPlot('chart-heatmap', [{
      z: hm.counts,
      x: hm.month_labels,
      y: hm.day_labels,
      type: 'heatmap',
      colorscale: [[0, 'rgba(76,175,80,0.08)'], [1, '#2e7d32']],
      showscale: false
    }], baseLayout({ margin: { t: 10, r: 20, l: 50, b: 40 } }), PLOTLY_CONFIG);
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

  function renderAll(data) {
    renderStats(data);
    renderYearlyTrend(data);
    renderTrajectory(data);
    renderBreakdown('chart-race', data.race_breakdown);
    renderBreakdown('chart-armed', data.armed_status_breakdown);
    renderHeatmap(data);
    renderTopN('chart-states', data.top_states);
    renderTopN('chart-agencies', data.top_agencies);
  }

  function relayoutAllForTheme() {
    var ids = ['chart-yearly', 'chart-trajectory', 'chart-race', 'chart-armed', 'chart-heatmap', 'chart-states', 'chart-agencies'];
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
