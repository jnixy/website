/**
 * Police Shootings of Dogs — tracker dashboard.
 * Renders charts from /data/dog-shooting-tracker.json using Plotly.js
 * (loaded separately via CDN). Theme-aware: mirrors mpv-dashboard.js so the
 * two dashboards behave identically in light/dark and on a runtime toggle.
 */
(function () {
  var PALETTE = ['#1565c0', '#c62828', '#ef6c00', '#00897b', '#7b1fa2', '#5e35b1', '#2e7d32', '#757575'];
  var DATA_URL = '/data/dog-shooting-tracker.json';
  var CSV_URL = '/data/dog-shootings.csv';

  var OUTCOME_LABELS = {
    'killed': 'Killed',
    'injured-survived': 'Injured, survived',
    'injured-euthanized': 'Injured, euthanized',
    'unharmed': 'Unharmed (missed)',
    'unknown': 'Unknown'
  };

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

  function escapeHtml(text) {
    if (text === undefined || text === null || text === '') return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatDateTime(iso, opts) {
    var parseTarget = (typeof iso === 'string' && iso.indexOf('T') === -1) ? iso + 'T00:00:00' : iso;
    var d = new Date(parseTarget);
    if (isNaN(d.getTime())) return iso || '';
    var fmt = { month: 'short', day: 'numeric' };
    if (!(opts && opts.omitYear)) fmt.year = 'numeric';
    return d.toLocaleDateString('en-US', fmt);
  }

  function titleCase(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function renderStats(data) {
    var s = data.stats || {};
    var delta = (s.current_year_to_date || 0) - (s.prior_year_same_point || 0);
    var deltaPct = s.prior_year_same_point > 0 ? Math.round((delta / s.prior_year_same_point) * 100) : 0;
    var deltaClass = delta > 0 ? 'up' : (delta < 0 ? 'down' : '');
    var deltaSign = delta > 0 ? '+' : '';
    var latest = data.date_range && data.date_range.latest ? formatDateTime(data.date_range.latest) : '—';

    var priorRow = s.prior_year_same_point > 0
      ? '<div class="dst-stat-delta ' + deltaClass + '">' + deltaSign + deltaPct + '% vs. ' + s.prior_year + ' same point</div>'
      : '';

    document.getElementById('dst-stats').innerHTML = '' +
      '<div class="dst-stat-tile">' +
        '<div class="dst-stat-value">' + (data.total_incidents || 0).toLocaleString() + '</div>' +
        '<div class="dst-stat-label">Incidents recorded</div>' +
      '</div>' +
      '<div class="dst-stat-tile">' +
        '<div class="dst-stat-value">' + (s.current_year_to_date || 0).toLocaleString() + '</div>' +
        '<div class="dst-stat-label">' + (s.current_year || '') + ' year to date</div>' + priorRow +
      '</div>' +
      '<div class="dst-stat-tile">' +
        '<div class="dst-stat-value">' + latest + '</div>' +
        '<div class="dst-stat-label">Most recent incident</div>' +
      '</div>';

    var range = '';
    if (data.date_range && data.date_range.earliest) {
      range = 'Incidents from ' + formatDateTime(data.date_range.earliest) + ' to ' +
        formatDateTime(data.date_range.latest) + '. ';
    }
    document.getElementById('dst-meta').innerHTML =
      range +
      'Compiled from ' + (data.total_sources || 0).toLocaleString() + ' news reports. ' +
      'Every count is a floor — see the notes below the charts. ' +
      'Updated ' + formatDateTime(data.generated_at) +
      ' &middot; <a href="' + CSV_URL + '" download>Download the data (CSV)</a>.';
  }

  function renderYearly(data) {
    var yc = data.yearly_counts || [];
    Plotly.newPlot('dst-chart-yearly', [{
      x: yc.map(function (d) { return d.year; }),
      y: yc.map(function (d) { return d.count; }),
      type: 'bar',
      marker: { color: PALETTE[0] },
      hovertemplate: '%{x}: %{y} incidents<extra></extra>'
    }], baseLayout({ yaxis: { title: 'Incidents', gridcolor: themeColors().grid } }), PLOTLY_CONFIG);
  }

  function renderHBar(elementId, breakdown, labelMap) {
    var items = (breakdown || []).slice().reverse();
    var labels = items.map(function (d) { return (labelMap && labelMap[d.label]) || titleCase(d.label); });
    var counts = items.map(function (d) { return d.count; });
    Plotly.newPlot(elementId, [{
      x: counts,
      y: labels,
      type: 'bar',
      orientation: 'h',
      marker: { color: labels.map(function (_, i) { return PALETTE[i % PALETTE.length]; }) },
      hovertemplate: '%{y}: %{x}<extra></extra>'
    }], baseLayout({
      margin: { t: 10, r: 20, l: 150, b: 40 },
      yaxis: { automargin: true, gridcolor: themeColors().grid }
    }), PLOTLY_CONFIG);
  }

  function renderStateMap(data) {
    var counts = data.state_counts || [];
    var colors = themeColors();
    Plotly.newPlot('dst-chart-states', [{
      type: 'choropleth',
      locationmode: 'USA-states',
      locations: counts.map(function (r) { return r.state; }),
      z: counts.map(function (r) { return r.count; }),
      customdata: counts.map(function (r) { return [r.name]; }),
      colorscale: [[0, 'rgba(21,101,192,0.10)'], [1, PALETTE[0]]],
      marker: { line: { color: colors.grid, width: 0.5 } },
      colorbar: { title: { text: 'Incidents', font: { color: colors.font } }, tickfont: { color: colors.font } },
      hovertemplate: '%{customdata[0]}: %{z} incidents<extra></extra>'
    }], baseLayout({
      margin: { t: 10, r: 10, l: 10, b: 10 },
      geo: {
        scope: 'usa',
        bgcolor: 'rgba(0,0,0,0)',
        lakecolor: 'rgba(0,0,0,0)',
        landcolor: 'rgba(0,0,0,0)',
        subunitcolor: colors.grid
      }
    }), PLOTLY_CONFIG);

    var cap = document.getElementById('dst-state-caption');
    if (cap && counts.length) {
      cap.textContent = counts[0].name + ' has the most recorded incidents (' + counts[0].count +
        '). This map reflects where incidents are reported and found, not necessarily where they most often occur.';
    }
  }

  function renderRecent(data) {
    var rows = data.recent_incidents || [];
    var host = document.getElementById('dst-recent');
    if (!rows.length) { host.innerHTML = '<p class="dst-chart-note">No incidents recorded yet.</p>'; return; }
    var html = '<ul class="dst-incident-list">';
    rows.forEach(function (r) {
      var loc = [r.city, r.state].filter(Boolean).join(', ');
      var when = r.incident_date ? formatDateTime(r.incident_date) : 'Date unknown';
      if (r.date_precision === 'month') when = 'Around ' + when;
      if (r.date_precision === 'approximate') when = 'Approx. ' + when;
      var sources = '<a href="' + escapeHtml(r.source_url) + '" target="_blank" rel="noopener">' +
        escapeHtml(r.source_name || 'source') + '</a>';
      (r.additional_sources || []).forEach(function (u, i) {
        sources += ' &middot; <a href="' + escapeHtml(u) + '" target="_blank" rel="noopener">+' + (i + 1) + '</a>';
      });
      var tags = [];
      if (r.dog_outcome && r.dog_outcome !== 'unknown') tags.push(OUTCOME_LABELS[r.dog_outcome] || r.dog_outcome);
      if (r.circumstance && r.circumstance !== 'unknown') tags.push(titleCase(r.circumstance));
      if (r.human_injured_by_fire === 'yes') tags.push('Person injured by gunfire');
      html += '<li class="dst-incident">' +
        '<div class="dst-incident-head"><span class="dst-incident-loc">' + escapeHtml(loc || 'Location unknown') +
        '</span><span class="dst-incident-date">' + escapeHtml(when) + '</span></div>' +
        (r.agency_name ? '<div class="dst-incident-agency">' + escapeHtml(r.agency_name) + '</div>' : '') +
        (r.summary ? '<p class="dst-incident-summary">' + escapeHtml(r.summary) + '</p>' : '') +
        (tags.length ? '<div class="dst-incident-tags">' + tags.map(function (t) {
          return '<span class="dst-tag">' + escapeHtml(t) + '</span>';
        }).join('') + '</div>' : '') +
        '<div class="dst-incident-sources">' + sources + '</div>' +
        '</li>';
    });
    html += '</ul>';
    host.innerHTML = html;
  }

  function renderAll(data) {
    renderStats(data);
    if (!data.total_incidents) {
      document.getElementById('dst-charts').style.display = 'none';
      document.getElementById('dst-empty').style.display = '';
      return;
    }
    renderYearly(data);
    renderHBar('dst-chart-outcome', data.outcome_breakdown, OUTCOME_LABELS);
    renderHBar('dst-chart-circumstance', data.circumstance_breakdown, null);
    renderHBar('dst-chart-agency', data.agency_type_breakdown, null);
    renderStateMap(data);
    renderRecent(data);
  }

  function relayoutForTheme() {
    var colors = themeColors();
    ['dst-chart-yearly', 'dst-chart-outcome', 'dst-chart-circumstance', 'dst-chart-agency'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.data) {
        Plotly.relayout(id, {
          'font.color': colors.font,
          'xaxis.gridcolor': colors.grid,
          'yaxis.gridcolor': colors.grid
        });
      }
    });
    var mapEl = document.getElementById('dst-chart-states');
    if (mapEl && mapEl.data) {
      Plotly.relayout('dst-chart-states', { 'font.color': colors.font, 'geo.subunitcolor': colors.grid });
      Plotly.restyle('dst-chart-states', {
        'colorbar.tickfont.color': colors.font,
        'colorbar.title.font.color': colors.font
      });
    }
  }

  function init() {
    fetch(DATA_URL)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (data) {
        document.getElementById('dst-loading').style.display = 'none';
        document.getElementById('dst-content').style.display = '';
        renderAll(data);
        var observer = new MutationObserver(relayoutForTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        if (window.matchMedia) {
          window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', relayoutForTheme);
        }
      })
      .catch(function (err) {
        console.error('dog-shooting-tracker: could not load data', err);
        document.getElementById('dst-loading').style.display = 'none';
        var e = document.getElementById('dst-error');
        e.style.display = '';
        e.textContent = 'Could not load tracker data (' + err.message + '). Please try again later.';
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
