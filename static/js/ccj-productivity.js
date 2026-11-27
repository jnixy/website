/**
 * CCJ Doctoral Program Productivity dashboard. Renders from
 * /data/ccj-productivity.json, which is written by scripts/50_dashboard_export.R
 * in the ccj-phd-productivity project. Every ranking is recomputed here from
 * anonymous authorship rows, so any weighting, year range, or subset the user
 * picks is scored by the same rules as the paper (Kleck & Mims, 2017).
 * Plotly.js is loaded separately via a CDN script tag. Theme handling follows
 * mpv-dashboard.js.
 */
(function () {
  'use strict';

  var DATA_URL = '/data/ccj-productivity.json';
  var PALETTE = ['#1565c0', '#c62828', '#2e7d32', '#ef6c00', '#7b1fa2', '#00897b'];
  var BYLINES = ['sole', 'first', 'middle', 'last', 'unknown'];
  var BYLINE_LABELS = { sole: 'Sole', first: 'First', middle: 'Middle', last: 'Last', unknown: 'Unknown' };
  var MAX_COMPARE = 6;
  var PAGE_SIZE = 25;
  // Programs left with fewer faculty than this under the rank/admin filters are
  // hidden, so the page never shows one or two people's numbers.
  var MIN_GROUP = 3;
  var LAW_RE = /\blaw review\b|\blaw journal\b|\bjournal of law\b|\blaw quarterly\b|\blaw & policy\b/i;

  var WEIGHTINGS = {
    km: { label: 'Credit (Kleck & Mims weights)', short: 'Credit',
          help: 'Journal prestige rating × authorship weight, as in the paper.' },
    auth: { label: 'Authorship-weighted count', short: 'Weighted articles',
            help: 'Authorship weight only (sole = 1, first of two = .60, ...); every journal counts the same.' },
    frac: { label: 'Fractional count (1/authors)', short: 'Fractional articles',
            help: 'Each article split equally among its authors; byline order ignored.' },
    count: { label: 'Authorships (unweighted)', short: 'Authorships',
             help: 'Every faculty authorship counts 1.' }
  };

  var DEFAULTS = {
    y0: null, y1: null, wt: 'km', meas: 'total', js: 'all', byl: 'all',
    rk: '', adm: '', cmp: '', sx: 'n_fac', sy: 'pf', jr: '', jp: '', ap: '', q: '', sort: 'rank', pg: 0
  };

  var D = null;        // decoded data
  var S = {};          // UI state (mirrored in the URL query string)
  var R = null;        // latest computation

  // ---------------------------------------------------------------- theme --
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
      muted: dark ? '#888' : '#b0b0b0',
      bar: dark ? '#64b5f6' : '#1565c0'
    };
  }

  function baseLayout(extra) {
    var c = themeColors();
    var layout = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: c.font, size: 12 },
      margin: { t: 10, r: 20, l: 50, b: 40 },
      xaxis: { gridcolor: c.grid, zerolinecolor: c.grid },
      yaxis: { gridcolor: c.grid, zerolinecolor: c.grid },
      showlegend: false,
      hoverlabel: { namelength: -1 }
    };
    return Object.assign(layout, extra || {});
  }

  var PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

  // -------------------------------------------------------------- helpers --
  function $(id) { return document.getElementById(id); }

  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    var div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  function fmt(x, digits) {
    if (x === null || x === undefined || isNaN(x)) return '—';
    return Number(x).toLocaleString(undefined, {
      minimumFractionDigits: digits || 0, maximumFractionDigits: digits || 0
    });
  }

  function minRank(values) {
    // Ties share the best rank, matching dplyr::min_rank(desc(x)) in the paper.
    return values.map(function (v) {
      var r = 1;
      for (var i = 0; i < values.length; i++) if (values[i] > v + 1e-9) r++;
      return r;
    });
  }

  function spearman(x, y) {
    var ok = [];
    for (var i = 0; i < x.length; i++) if (x[i] !== null && y[i] !== null && !isNaN(x[i]) && !isNaN(y[i])) ok.push(i);
    if (ok.length < 3) return null;
    function avgRanks(v) {
      var idx = v.map(function (val, i) { return i; }).sort(function (a, b) { return v[a] - v[b]; });
      var r = new Array(v.length);
      for (var i = 0; i < idx.length;) {
        var j = i;
        while (j + 1 < idx.length && v[idx[j + 1]] === v[idx[i]]) j++;
        for (var k = i; k <= j; k++) r[idx[k]] = (i + j) / 2 + 1;
        i = j + 1;
      }
      return r;
    }
    var rx = avgRanks(ok.map(function (i) { return x[i]; }));
    var ry = avgRanks(ok.map(function (i) { return y[i]; }));
    var n = ok.length, mx = 0, my = 0;
    for (var i = 0; i < n; i++) { mx += rx[i]; my += ry[i]; }
    mx /= n; my /= n;
    var sxy = 0, sxx = 0, syy = 0;
    for (var i = 0; i < n; i++) {
      sxy += (rx[i] - mx) * (ry[i] - my); sxx += (rx[i] - mx) * (rx[i] - mx); syy += (ry[i] - my) * (ry[i] - my);
    }
    return sxy / Math.sqrt(sxx * syy);
  }

  function parseList(s) {
    if (!s) return [];
    return String(s).split('.').filter(function (v) { return v !== ''; }).map(Number)
      .filter(function (v) { return !isNaN(v); });
  }

  // ----------------------------------------------------------- data decode --
  function decode(raw) {
    var d = { meta: raw.meta, rankCats: raw.rank_categories };
    var P = raw.programs;
    d.programs = P.name.map(function (name, i) {
      return {
        i: i, name: name, short: P.short[i], institution: P.institution[i], unit: P.academic_unit[i],
        n_faculty: P.n_faculty[i], n_unresolved: P.n_unresolved[i],
        rankN: [P.rank_assistant[i], P.rank_associate[i], P.rank_full[i], P.rank_research[i], P.rank_unlisted[i]],
        km: [P.km_rank_2000_04[i], P.km_rank_2005_09[i], P.km_rank_2010_14[i]],
        km_cpf_2014: P.km_cpf_rank_2010_14[i],
        top_producer_share: P.top_producer_share[i],
        // Faculty counts by rank x admin; cell = rank index * 2 + admin (0/1).
        rankAdminN: P.fac_rank_admin ? P.fac_rank_admin[i] : null
      };
    });
    var F = raw.former_programs || { name: [] };
    d.former = (F.name || []).map(function (name, i) {
      return { name: name, km: [F.rank_2000_04[i], F.rank_2005_09[i], F.rank_2010_14[i]] };
    });
    var J = raw.journals;
    d.journals = J.name.map(function (name, i) {
      return {
        i: i, name: name, prestige: J.prestige[i], source: J.prestige_source[i],
        top: J.top[i], law: LAW_RE.test(name),
        rated: J.prestige_source[i] !== 'unrated_fallback_4'
      };
    });
    var A = raw.articles;
    d.articles = A.id.map(function (id, i) {
      return { i: i, id: id, title: A.title[i], doi: A.doi[i], j: A.j[i], year: A.year[i], n: A.n_authors[i],
        cx: A.cx ? A.cx[i] === 1 : false };
    });
    var U = raw.authorships;
    d.rows = U.p.map(function (p, i) {
      return { p: p, a: U.a[i], byline: U.byline[i], w: U.w[i], r: U.r[i], ad: U.ad ? U.ad[i] : 0 };
    });
    var C = raw.paper_check;
    d.paper = {};
    C.p.forEach(function (p, i) {
      d.paper[p] = { total: C.total_credit[i], pf: C.credit_per_faculty[i], rank: C.rank[i], rank_pf: C.rank_pf[i] };
    });
    var years = d.articles.map(function (a) { return a.year; });
    d.yMin = Math.min.apply(null, years);
    d.yMax = Math.max.apply(null, years);
    return d;
  }

  // --------------------------------------------------------------- state --
  function readState() {
    var q = new URLSearchParams(window.location.search);
    Object.keys(DEFAULTS).forEach(function (k) {
      S[k] = q.has(k) ? q.get(k) : DEFAULTS[k];
    });
    S.y0 = clampYear(parseInt(S.y0, 10) || D.yMin);
    S.y1 = clampYear(parseInt(S.y1, 10) || D.yMax);
    if (S.y0 > S.y1) { var t = S.y0; S.y0 = S.y1; S.y1 = t; }
    if (!WEIGHTINGS[S.wt]) S.wt = 'km';
    if (S.adm !== '0' && S.adm !== '1') S.adm = '';
    S.pg = parseInt(S.pg, 10) || 0;
  }

  function clampYear(y) { return Math.max(D.yMin, Math.min(D.yMax, y)); }

  function writeState() {
    var q = new URLSearchParams();
    Object.keys(DEFAULTS).forEach(function (k) {
      var v = S[k];
      var dflt = DEFAULTS[k];
      if (k === 'y0') dflt = D.yMin;
      if (k === 'y1') dflt = D.yMax;
      if (v !== null && v !== undefined && String(v) !== String(dflt)) q.set(k, v);
    });
    var s = q.toString();
    history.replaceState(null, '', window.location.pathname + (s ? '?' + s : '') + window.location.hash);
  }

  function isDefaultScoring() {
    return S.y0 === D.yMin && S.y1 === D.yMax && S.js === 'all' && S.byl === 'all' && !S.rk && !S.adm;
  }

  // ------------------------------------------------------------- compute --
  function rowValue(row, wt) {
    var art = D.articles[row.a];
    var j = D.journals[art.j];
    switch (wt) {
      case 'km': return row.w * j.prestige;
      case 'auth': return row.w;
      case 'frac': return 1 / art.n;
      default: return 1;
    }
  }

  function journalPasses(j, js) {
    if (js === 'top') return j.top;
    if (js === 'rated') return j.rated;
    if (js === 'nolaw') return !j.law;
    return true;
  }

  function rowPasses(row, opts) {
    var art = D.articles[row.a];
    if (art.year < S.y0 || art.year > S.y1) return false;
    if (!opts.ignoreJournal && !journalPasses(D.journals[art.j], S.js)) return false;
    if (S.byl === 'first' && !(row.byline === 'first' || row.byline === 'sole')) return false;
    if (S.rk) {
      var ranks = parseList(S.rk);
      if (ranks.indexOf(row.r) === -1) return false;
    }
    if (S.adm && row.ad !== +S.adm) return false;
    if (SUP[row.p]) return false;
    return true;
  }

  function denominator(prog) {
    if (!S.rk && !S.adm) return prog.n_faculty;
    var ranks = S.rk ? parseList(S.rk) : D.rankCats.map(function (lab, i) { return i; });
    if (!S.adm) return ranks.reduce(function (s, r) { return s + (prog.rankN[r] || 0); }, 0);
    var m = prog.rankAdminN || [];
    return ranks.reduce(function (s, r) { return s + (m[r * 2 + +S.adm] || 0); }, 0);
  }

  // Programs hidden under the current rank/admin filters (1 or 2 faculty).
  var SUP = {};

  function updateSuppression() {
    SUP = {};
    D.programs.forEach(function (p) {
      var den = denominator(p);
      if (den > 0 && den < MIN_GROUP) SUP[p.i] = true;
    });
  }

  function compute() {
    updateSuppression();
    var rows = D.rows.filter(function (r) { return rowPasses(r, {}); });
    var stats = D.programs.map(function (p) {
      return { total: 0, auth: 0, arts: {}, cxArts: {}, top: 0, team: 0, firstSole: 0, byline: {}, years: {} };
    });
    rows.forEach(function (r) {
      var v = rowValue(r, S.wt);
      var art = D.articles[r.a];
      var st = stats[r.p];
      st.total += v;
      st.auth += 1;
      st.arts[r.a] = true;
      if (art.cx) st.cxArts[r.a] = true;
      if (D.journals[art.j].top) st.top += 1;
      st.team += art.n;
      if (r.byline === 'first' || r.byline === 'sole') st.firstSole += 1;
      st.byline[r.byline] = (st.byline[r.byline] || 0) + 1;
      st.years[art.year] = (st.years[art.year] || 0) + v;
    });
    var progs = D.programs.map(function (p, i) {
      var st = stats[i];
      var den = denominator(p);
      return {
        p: i, name: p.name, short: p.short, n_fac: den, total: st.total,
        pf: den > 0 ? st.total / den : null,
        auth: st.auth, auth_pf: den > 0 ? st.auth / den : null,
        articles: Object.keys(st.arts).length,
        crimrxiv_share: Object.keys(st.arts).length ? 100 * Object.keys(st.cxArts).length / Object.keys(st.arts).length : null,
        top_share: st.auth ? 100 * st.top / st.auth : null,
        team: st.auth ? st.team / st.auth : null,
        first_share: st.auth ? 100 * st.firstSole / st.auth : null,
        byline: st.byline, years: st.years,
        km2014: p.km[2], km_cpf_2014: p.km_cpf_2014,
        top_producer: p.top_producer_share === null ? null : 100 * p.top_producer_share,
        unresolved: p.n_unresolved
      };
    });
    // Hidden programs show no numbers and take no rank; the rest rank among themselves.
    progs.forEach(function (x) {
      if (!SUP[x.p]) return;
      x.suppressed = true;
      ['total', 'pf', 'auth', 'auth_pf', 'articles', 'crimrxiv_share', 'top_share', 'team', 'first_share']
        .forEach(function (k) { x[k] = null; });
      x.byline = {}; x.years = {};
    });
    var rt = minRank(progs.map(function (x) { return x.suppressed ? -1 : x.total; }));
    var rp = minRank(progs.map(function (x) { return x.pf === null ? -1 : x.pf; }));
    progs.forEach(function (x, i) {
      x.rank_total = x.suppressed ? null : rt[i];
      x.rank_pf = x.suppressed ? null : rp[i];
      x.paper_rank = D.paper[i] ? D.paper[i].rank : null;
      x.paper_rank_pf = D.paper[i] ? D.paper[i].rank_pf : null;
    });
    return { rows: rows, progs: progs };
  }

  function measureKey() { return S.meas === 'pf' ? 'pf' : 'total'; }
  function rankKey() { return S.meas === 'pf' ? 'rank_pf' : 'rank_total'; }
  function paperRankKey() { return S.meas === 'pf' ? 'paper_rank_pf' : 'paper_rank'; }

  function measureLabel() {
    return WEIGHTINGS[S.wt].short + (S.meas === 'pf' ? ' per faculty member' : ' (program total)');
  }

  // ---------------------------------------------------------- self-check --
  function selfCheck() {
    // With the paper's settings, recomputed credit must reproduce Table 2.
    var saved = Object.assign({}, S);
    S.y0 = D.yMin; S.y1 = Math.min(D.yMax, D.meta.window[1]); S.js = 'all'; S.byl = 'all'; S.rk = ''; S.adm = ''; S.wt = 'km';
    var res = compute();
    Object.assign(S, saved);
    updateSuppression();
    var bad = res.progs.filter(function (x) {
      return D.paper[x.p] && Math.abs(x.total - D.paper[x.p].total) > 0.05;
    });
    if (bad.length) {
      console.error('[ccj-productivity] self-check failed for', bad.map(function (x) { return x.name; }));
      var el = $('ccj-check');
      el.style.display = 'block';
      el.textContent = 'Data check failed: recomputed credit for ' + bad.length +
        ' program(s) does not match the published table. Please report this.';
    }
  }

  // ------------------------------------------------------------ controls --
  function optionHtml(value, label, selected) {
    return '<option value="' + escapeHtml(value) + '"' + (String(value) === String(selected) ? ' selected' : '') +
      '>' + escapeHtml(label) + '</option>';
  }

  function buildControls() {
    var years = [];
    for (var y = D.yMin; y <= D.yMax; y++) years.push(y);
    $('ccj-y0').innerHTML = years.map(function (y) { return optionHtml(y, y, S.y0); }).join('');
    $('ccj-y1').innerHTML = years.map(function (y) { return optionHtml(y, y, S.y1); }).join('');
    $('ccj-wt').innerHTML = Object.keys(WEIGHTINGS).map(function (k) {
      return optionHtml(k, WEIGHTINGS[k].label, S.wt);
    }).join('');
    $('ccj-meas').value = S.meas;
    $('ccj-js').value = S.js;
    $('ccj-byl').value = S.byl;
    $('ccj-adm').value = S.adm;
    if (!D.programs.length || !D.programs[0].rankAdminN) $('ccj-adm').disabled = true;

    var rk = parseList(S.rk);
    $('ccj-rk').innerHTML = D.rankCats.map(function (lab, i) {
      var checked = !S.rk || rk.indexOf(i) !== -1;
      return '<label class="ccj-rank-opt"><input type="checkbox" value="' + i + '"' + (checked ? ' checked' : '') +
        '> ' + escapeHtml(lab) + '</label>';
    }).join('');

    var sorted = D.programs.slice().sort(function (a, b) { return a.short.localeCompare(b.short); });
    var progOpts = sorted.map(function (p) { return optionHtml(p.i, p.short, ''); }).join('');
    $('ccj-cmp-add').innerHTML = '<option value="">Add a program…</option>' + progOpts;
    $('ccj-jp').innerHTML = '<option value="">Choose a program…</option>' +
      sorted.map(function (p) { return optionHtml(p.i, p.short, S.jp); }).join('');
    $('ccj-ap').innerHTML = '<option value="">All programs</option>' +
      sorted.map(function (p) { return optionHtml(p.i, p.short, S.ap); }).join('');
    $('ccj-q').value = S.q || '';

    var metricOpts = Object.keys(SCATTER_METRICS);
    $('ccj-sx').innerHTML = metricOpts.map(function (k) { return optionHtml(k, SCATTER_METRICS[k].label(), S.sx); }).join('');
    $('ccj-sy').innerHTML = metricOpts.map(function (k) { return optionHtml(k, SCATTER_METRICS[k].label(), S.sy); }).join('');

    // Journal picker: datalist ordered by how often the journal appears.
    var counts = {};
    D.rows.forEach(function (r) { var j = D.articles[r.a].j; counts[j] = (counts[j] || 0) + 1; });
    var js = D.journals.slice().sort(function (a, b) { return (counts[b.i] || 0) - (counts[a.i] || 0); });
    $('ccj-journal-list').innerHTML = js.map(function (j) {
      return '<option value="' + escapeHtml(j.name) + '"></option>';
    }).join('');
    if (S.jr === '' && js.length) S.jr = String(js[0].i);
    $('ccj-jr').value = D.journals[+S.jr] ? D.journals[+S.jr].name : '';

    function on(id, ev, fn) { $(id).addEventListener(ev, fn); }
    on('ccj-y0', 'change', function (e) { S.y0 = +e.target.value; if (S.y0 > S.y1) { S.y1 = S.y0; $('ccj-y1').value = S.y1; } refresh(); });
    on('ccj-y1', 'change', function (e) { S.y1 = +e.target.value; if (S.y1 < S.y0) { S.y0 = S.y1; $('ccj-y0').value = S.y0; } refresh(); });
    on('ccj-wt', 'change', function (e) { S.wt = e.target.value; refresh(); });
    on('ccj-meas', 'change', function (e) { S.meas = e.target.value; refresh(); });
    on('ccj-js', 'change', function (e) { S.js = e.target.value; refresh(); });
    on('ccj-byl', 'change', function (e) { S.byl = e.target.value; refresh(); });
    on('ccj-adm', 'change', function (e) { S.adm = e.target.value; refresh(); });
    on('ccj-rk', 'change', function () {
      var boxes = $('ccj-rk').querySelectorAll('input');
      var picked = [];
      boxes.forEach(function (b) { if (b.checked) picked.push(+b.value); });
      if (!picked.length) { boxes.forEach(function (b) { b.checked = true; }); picked = []; }
      S.rk = picked.length === D.rankCats.length || !picked.length ? '' : picked.join('.');
      refresh();
    });
    on('ccj-reset', 'click', function (e) {
      e.preventDefault();
      Object.keys(DEFAULTS).forEach(function (k) { S[k] = DEFAULTS[k]; });
      S.y0 = D.yMin; S.y1 = D.yMax;
      buildControlsValues();
      refresh();
    });
    on('ccj-cmp-add', 'change', function (e) {
      var v = e.target.value;
      e.target.value = '';
      if (v === '') return;
      addCompare(+v);
    });
    on('ccj-sx', 'change', function (e) { S.sx = e.target.value; renderScatter(); writeState(); });
    on('ccj-sy', 'change', function (e) { S.sy = e.target.value; renderScatter(); writeState(); });
    on('ccj-jr', 'change', function (e) {
      var name = e.target.value.trim().toUpperCase();
      var hit = D.journals.filter(function (j) { return j.name.toUpperCase() === name; })[0];
      if (hit) { S.jr = String(hit.i); renderJournal(); writeState(); }
    });
    on('ccj-jp', 'change', function (e) { S.jp = e.target.value; renderProgramJournals(); writeState(); });
    on('ccj-ap', 'change', function (e) { S.ap = e.target.value; S.pg = 0; renderArticles(); writeState(); });
    var qTimer = null;
    on('ccj-q', 'input', function (e) {
      clearTimeout(qTimer);
      qTimer = setTimeout(function () { S.q = e.target.value; S.pg = 0; renderArticles(); writeState(); }, 250);
    });
    on('ccj-download', 'click', function (e) { e.preventDefault(); downloadCsv(); });
    on('ccj-copy-link', 'click', function (e) {
      e.preventDefault();
      var btn = e.target;
      var done = function () { btn.textContent = 'Link copied'; setTimeout(function () { btn.textContent = 'Copy link to this view'; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(window.location.href).then(done, done); else done();
    });
  }

  function buildControlsValues() {
    $('ccj-y0').value = S.y0; $('ccj-y1').value = S.y1; $('ccj-wt').value = S.wt;
    $('ccj-meas').value = S.meas; $('ccj-js').value = S.js; $('ccj-byl').value = S.byl;
    $('ccj-adm').value = S.adm;
    $('ccj-rk').querySelectorAll('input').forEach(function (b) { b.checked = true; });
    $('ccj-ap').value = ''; $('ccj-jp').value = ''; $('ccj-q').value = '';
  }

  function addCompare(p) {
    var cmp = parseList(S.cmp);
    if (cmp.indexOf(p) !== -1) return;
    if (cmp.length >= MAX_COMPARE) cmp.shift();
    cmp.push(p);
    S.cmp = cmp.join('.');
    renderCompareAll();
    writeState();
  }

  function removeCompare(p) {
    S.cmp = parseList(S.cmp).filter(function (x) { return x !== p; }).join('.');
    renderCompareAll();
    writeState();
  }

  function compareColor(p) {
    var idx = parseList(S.cmp).indexOf(p);
    return idx === -1 ? null : PALETTE[idx % PALETTE.length];
  }

  // ------------------------------------------------------------- render --
  function refresh() {
    R = compute();
    writeState();
    renderStats();
    renderRankings();
    renderCompareAll();
    renderScatter();
    renderTrends();
    renderJournal();
    renderProgramJournals();
    renderArticles();
  }

  function renderCompareAll() {
    renderChips();
    renderRankings();
    renderCompare();
    renderScatter();
    renderTrends();
  }

  function renderStats() {
    var arts = {};
    R.rows.forEach(function (r) { arts[r.a] = true; });
    var fac = R.progs.reduce(function (s, x) { return s + (x.suppressed ? 0 : x.n_fac); }, 0);
    var tiles = [
      [fmt(R.progs.filter(function (x) { return !x.suppressed; }).length), 'Programs'],
      [fmt(fac), 'Faculty in denominator'],
      [fmt(Object.keys(arts).length), 'Articles'],
      [fmt(R.rows.length), 'Faculty authorships'],
      [S.y0 === S.y1 ? String(S.y0) : S.y0 + '–' + S.y1, 'Issue years']
    ];
    $('ccj-stats').innerHTML = tiles.map(function (t) {
      return '<div class="ccj-stat-tile"><div class="ccj-stat-value">' + t[0] +
        '</div><div class="ccj-stat-label">' + t[1] + '</div></div>';
    }).join('');
    $('ccj-wt-help').textContent = WEIGHTINGS[S.wt].help;
    $('ccj-paper-note').style.display = isDefaultScoring() && S.wt === 'km' ? 'none' : 'block';
  }

  function renderRankings() {
    if (!R) return;
    var c = themeColors();
    var key = measureKey();
    var rk = rankKey();
    var sorted = R.progs.filter(function (x) { return !x.suppressed; })
      .sort(function (a, b) { return a[rk] - b[rk] || a.short.localeCompare(b.short); });
    var digits = S.wt === 'count' && S.meas === 'total' ? 0 : 1;
    var trace = {
      type: 'bar', orientation: 'h',
      y: sorted.map(function (x) { return x.short; }),
      x: sorted.map(function (x) { return x[key]; }),
      marker: { color: sorted.map(function (x) { return compareColor(x.p) || c.bar; }) },
      customdata: sorted.map(function (x) { return x.p; }),
      text: sorted.map(function (x) { return fmt(x[key], digits); }),
      textposition: 'outside', cliponaxis: false,
      hovertemplate: sorted.map(function (x) {
        return '<b>' + escapeHtml(x.name) + '</b><br>Rank ' + x[rk] + ' of ' + sorted.length +
          '<br>' + escapeHtml(measureLabel()) + ': ' + fmt(x[key], 2) +
          '<br>Faculty: ' + x.n_fac + ' · Authorships: ' + x.auth + '<extra></extra>';
      })
    };
    var el = $('chart-rankings');
    Plotly.react(el, [trace], baseLayout({
      height: Math.max(360, sorted.length * 19 + 60),
      margin: { t: 10, r: 60, l: 150, b: 40 },
      yaxis: { autorange: 'reversed', automargin: true, gridcolor: c.grid, tickfont: { size: 11 } },
      xaxis: { title: { text: measureLabel() }, gridcolor: c.grid, zerolinecolor: c.grid, rangemode: 'tozero' },
      bargap: 0.25
    }), PLOTLY_CONFIG);
    if (!el._ccjBound) {
      el.on('plotly_click', function (ev) { if (ev.points && ev.points.length) addCompare(ev.points[0].customdata); });
      el._ccjBound = true;
    }
    renderRankTable(digits);
  }

  function renderRankTable(digits) {
    var key = measureKey();
    var rk = rankKey();
    var prk = paperRankKey();
    var cols = [
      ['rank', 'Rank'], ['short', 'Program'], ['total', 'Total'], ['pf', 'Per faculty'],
      ['n_fac', 'Faculty'], ['auth', 'Authorships'], ['top_share', 'Top-journal %'], ['crimrxiv_share', 'CrimRxiv %'], ['delta', 'vs. paper']
    ];
    var rows = R.progs.map(function (x) {
      return Object.assign({}, x, { rank: x[rk], delta: x[prk] && x[rk] ? x[prk] - x[rk] : null });
    });
    var nHidden = rows.filter(function (x) { return x.suppressed; }).length;
    var sk = S.sort || 'rank';
    var desc = sk.charAt(0) === '-';
    var field = desc ? sk.slice(1) : sk;
    rows.sort(function (a, b) {
      var va = a[field], vb = b[field];
      var cmp = typeof va === 'string' ? va.localeCompare(vb) : (va === null ? 1e12 : va) - (vb === null ? 1e12 : vb);
      return desc ? -cmp : cmp;
    });
    var head = '<tr>' + cols.map(function (cdef) {
      var mark = field === cdef[0] ? (desc ? ' ▼' : ' ▲') : '';
      return '<th data-sort="' + cdef[0] + '" class="' + (cdef[0] === 'short' ? '' : 'ccj-num') + '">' +
        cdef[1] + mark + '</th>';
    }).join('') + '</tr>';
    var body = rows.map(function (x) {
      var d = x.delta;
      var dTxt = d === null ? '—' : (d > 0 ? '▲ ' + d : d < 0 ? '▼ ' + Math.abs(d) : '–');
      var dCls = d > 0 ? 'up' : d < 0 ? 'down' : '';
      var col = compareColor(x.p);
      if (x.suppressed) {
        return '<tr class="ccj-muted"><td class="ccj-num">—</td><td>' + escapeHtml(x.short) + '</td>' +
          '<td colspan="' + (cols.length - 2) + '">Fewer than ' + MIN_GROUP + ' faculty under these filters; not shown</td></tr>';
      }
      return '<tr' + (col ? ' style="box-shadow: inset 4px 0 0 ' + col + '"' : '') + '>' +
        '<td class="ccj-num">' + x.rank + '</td>' +
        '<td><a href="#" data-add="' + x.p + '" title="Add to comparison">' + escapeHtml(x.short) + '</a></td>' +
        '<td class="ccj-num">' + fmt(x.total, digits) + '</td>' +
        '<td class="ccj-num">' + fmt(x.pf, 2) + '</td>' +
        '<td class="ccj-num">' + x.n_fac + '</td>' +
        '<td class="ccj-num">' + fmt(x.auth) + '</td>' +
        '<td class="ccj-num">' + fmt(x.top_share, 1) + '</td>' +
        '<td class="ccj-num">' + fmt(x.crimrxiv_share, 1) + '</td>' +
        '<td class="ccj-num ccj-delta ' + dCls + '">' + dTxt + '</td></tr>';
    }).join('');
    var tbl = $('ccj-rank-table');
    tbl.innerHTML = '<thead>' + head + '</thead><tbody>' + body + '</tbody>';
    tbl.querySelectorAll('th').forEach(function (th) {
      th.addEventListener('click', function () {
        var f = th.getAttribute('data-sort');
        // First click: rank and name ascending, numbers descending; next click flips.
        var asc = f === 'rank' || f === 'short';
        S.sort = S.sort === f ? '-' + f : (S.sort === '-' + f ? f : (asc ? f : '-' + f));
        renderRankTable(digits);
        writeState();
      });
    });
    tbl.querySelectorAll('a[data-add]').forEach(function (a) {
      a.addEventListener('click', function (e) { e.preventDefault(); addCompare(+a.getAttribute('data-add')); });
    });
    $('ccj-rank-note').textContent = 'Ranked on ' + measureLabel().toLowerCase() +
      '. “vs. paper” compares each rank with the paper’s ' +
      (S.meas === 'pf' ? 'credit-per-faculty' : 'total-credit') + ' rank (▲ = higher now). Click a program or bar to add it to the comparison.' +
      (nHidden ? ' ' + nHidden + ' program' + (nHidden === 1 ? ' has' : 's have') + ' fewer than ' + MIN_GROUP +
        ' faculty under these filters and ' + (nHidden === 1 ? 'is' : 'are') + ' not shown.' : '');
  }

  function renderChips() {
    var cmp = parseList(S.cmp);
    $('ccj-chips').innerHTML = cmp.length ? cmp.map(function (p) {
      return '<span class="ccj-chip" style="border-color:' + compareColor(p) + '"><span class="ccj-dot" style="background:' +
        compareColor(p) + '"></span>' + escapeHtml(D.programs[p].short) +
        ' <button type="button" aria-label="Remove" data-rm="' + p + '">×</button></span>';
    }).join('') : '<span class="ccj-muted">No programs selected yet. Add up to ' + MAX_COMPARE + '.</span>';
    $('ccj-chips').querySelectorAll('button[data-rm]').forEach(function (b) {
      b.addEventListener('click', function () { removeCompare(+b.getAttribute('data-rm')); });
    });
  }

  function renderCompare() {
    if (!R) return;
    var cmp = parseList(S.cmp);
    var wrap = $('ccj-compare-charts');
    wrap.style.display = cmp.length ? '' : 'none';
    if (!cmp.length) return;
    var c = themeColors();
    var years = [];
    for (var y = S.y0; y <= S.y1; y++) years.push(y);
    // Hidden programs keep their chip but get no lines or bars.
    var sel = cmp.map(function (p) { return R.progs[p]; }).filter(function (x) { return !x.suppressed; });

    // Credit by year
    Plotly.react($('chart-compare-years'), sel.map(function (x) {
      return {
        type: 'scatter', mode: 'lines+markers', name: x.short,
        x: years, y: years.map(function (yr) {
          var v = x.years[yr] || 0;
          return S.meas === 'pf' ? (x.n_fac ? v / x.n_fac : null) : v;
        }),
        line: { color: compareColor(x.p), width: 3 }, marker: { size: 7 },
        hovertemplate: escapeHtml(x.short) + ' %{x}: %{y:.2f}<extra></extra>'
      };
    }), baseLayout({
      showlegend: true, legend: { orientation: 'h', y: -0.2 },
      xaxis: { dtick: 1, gridcolor: c.grid },
      yaxis: { title: { text: measureLabel() }, gridcolor: c.grid, rangemode: 'tozero' },
      margin: { t: 10, r: 20, l: 60, b: 60 }
    }), PLOTLY_CONFIG);

    // Journal mix: share of each program's value from the selection's top journals
    var byJ = {};
    var perProg = {};
    R.rows.forEach(function (r) {
      if (cmp.indexOf(r.p) === -1) return;
      var j = D.articles[r.a].j;
      var v = rowValue(r, S.wt);
      byJ[j] = (byJ[j] || 0) + v;
      perProg[r.p] = perProg[r.p] || {};
      perProg[r.p][j] = (perProg[r.p][j] || 0) + v;
    });
    var topJ = Object.keys(byJ).sort(function (a, b) { return byJ[b] - byJ[a]; }).slice(0, 8).map(Number);
    var mixColors = ['#1565c0', '#c62828', '#2e7d32', '#ef6c00', '#7b1fa2', '#00897b', '#5e35b1', '#6d4c41'];
    var traces = topJ.map(function (j, k) {
      return {
        type: 'bar', orientation: 'h', name: D.journals[j].name,
        y: sel.map(function (x) { return x.short; }),
        x: sel.map(function (x) {
          var tot = x.total || 0;
          return tot ? 100 * ((perProg[x.p] || {})[j] || 0) / tot : 0;
        }),
        marker: { color: mixColors[k] },
        hovertemplate: '%{y}: %{x:.1f}% from ' + escapeHtml(D.journals[j].name) + '<extra></extra>'
      };
    });
    traces.push({
      type: 'bar', orientation: 'h', name: 'All other journals',
      y: sel.map(function (x) { return x.short; }),
      x: sel.map(function (x) {
        var tot = x.total || 0;
        if (!tot) return 0;
        var inTop = topJ.reduce(function (s, j) { return s + ((perProg[x.p] || {})[j] || 0); }, 0);
        return 100 * (tot - inTop) / tot;
      }),
      marker: { color: c.muted },
      hovertemplate: '%{y}: %{x:.1f}% from other journals<extra></extra>'
    });
    Plotly.react($('chart-compare-journals'), traces, baseLayout({
      barmode: 'stack', showlegend: true, legend: { orientation: 'h', y: -0.12, yanchor: 'top', font: { size: 10 } },
      height: 300 + sel.length * 34,
      xaxis: { range: [0, 100], ticksuffix: '%', gridcolor: c.grid },
      yaxis: { autorange: 'reversed', automargin: true },
      margin: { t: 10, r: 20, l: 120, b: 150 }
    }), PLOTLY_CONFIG);

    // Byline position mix
    var bylineColors = { sole: '#2e7d32', first: '#1565c0', middle: '#90a4ae', last: '#ef6c00', unknown: '#cfd8dc' };
    Plotly.react($('chart-compare-byline'), BYLINES.map(function (b) {
      return {
        type: 'bar', orientation: 'h', name: BYLINE_LABELS[b],
        y: sel.map(function (x) { return x.short; }),
        x: sel.map(function (x) { return x.auth ? 100 * (x.byline[b] || 0) / x.auth : 0; }),
        marker: { color: bylineColors[b] },
        hovertemplate: '%{y}: %{x:.1f}% ' + BYLINE_LABELS[b].toLowerCase() + ' author<extra></extra>'
      };
    }), baseLayout({
      barmode: 'stack', showlegend: true, legend: { orientation: 'h', y: -0.12, yanchor: 'top', traceorder: 'normal' },
      height: 200 + sel.length * 34,
      xaxis: { range: [0, 100], ticksuffix: '%', gridcolor: c.grid },
      yaxis: { autorange: 'reversed', automargin: true },
      margin: { t: 10, r: 20, l: 120, b: 80 }
    }), PLOTLY_CONFIG);
  }

  var SCATTER_METRICS = {
    total: { label: function () { return WEIGHTINGS[S.wt].short + ' (total)'; } },
    pf: { label: function () { return WEIGHTINGS[S.wt].short + ' per faculty'; } },
    n_fac: { label: function () { return 'Faculty (n)'; } },
    auth: { label: function () { return 'Authorships'; } },
    auth_pf: { label: function () { return 'Authorships per faculty'; } },
    articles: { label: function () { return 'Distinct articles'; } },
    top_share: { label: function () { return 'Top-journal share of authorships (%)'; } },
    team: { label: function () { return 'Mean authors per article'; } },
    first_share: { label: function () { return 'First- or sole-author share (%)'; } },
    top_producer: { label: function () { return 'Top producer’s share of credit, 2020–24 (%)'; } },
    km2014: { label: function () { return 'Kleck & Mims 2010–14 rank (total)'; } },
    km_cpf_2014: { label: function () { return 'Kleck & Mims 2010–14 rank (per faculty)'; } },
    unresolved: { label: function () { return 'Faculty not matched (n)'; } },
    crimrxiv_share: { label: function () { return 'Articles with a CrimRxiv copy (%)'; } }
  };

  function renderScatter() {
    if (!R) return;
    var c = themeColors();
    var sx = SCATTER_METRICS[S.sx] ? S.sx : 'n_fac';
    var sy = SCATTER_METRICS[S.sy] ? S.sy : 'pf';
    var pts = R.progs.filter(function (x) { return !x.suppressed && x[sx] !== null && x[sy] !== null && x[sx] !== undefined && x[sy] !== undefined; });
    var cmp = parseList(S.cmp);
    var trace = {
      type: 'scatter', mode: 'markers+text',
      x: pts.map(function (x) { return x[sx]; }),
      y: pts.map(function (x) { return x[sy]; }),
      text: pts.map(function (x) { return cmp.indexOf(x.p) !== -1 ? x.short : ''; }),
      textposition: 'top center',
      customdata: pts.map(function (x) { return x.p; }),
      marker: {
        size: pts.map(function (x) { return cmp.indexOf(x.p) !== -1 ? 13 : 9; }),
        color: pts.map(function (x) { return compareColor(x.p) || c.bar; }),
        opacity: 0.85, line: { width: 1, color: 'rgba(255,255,255,0.6)' }
      },
      hovertemplate: pts.map(function (x) {
        return '<b>' + escapeHtml(x.name) + '</b><br>' + escapeHtml(SCATTER_METRICS[sx].label()) + ': ' + fmt(x[sx], 2) +
          '<br>' + escapeHtml(SCATTER_METRICS[sy].label()) + ': ' + fmt(x[sy], 2) + '<extra></extra>';
      })
    };
    var rankAxis = function (k) { return k === 'km2014' || k === 'km_cpf_2014'; };
    var el = $('chart-scatter');
    Plotly.react(el, [trace], baseLayout({
      height: 460,
      xaxis: { title: { text: SCATTER_METRICS[sx].label() }, gridcolor: c.grid, zerolinecolor: c.grid,
               autorange: rankAxis(sx) ? 'reversed' : true },
      yaxis: { title: { text: SCATTER_METRICS[sy].label() }, gridcolor: c.grid, zerolinecolor: c.grid,
               autorange: rankAxis(sy) ? 'reversed' : true },
      margin: { t: 20, r: 20, l: 70, b: 60 }
    }), PLOTLY_CONFIG);
    if (!el._ccjBound) {
      el.on('plotly_click', function (ev) { if (ev.points && ev.points.length) addCompare(ev.points[0].customdata); });
      el._ccjBound = true;
    }
    var rho = spearman(pts.map(function (x) { return x[sx]; }), pts.map(function (x) { return x[sy]; }));
    $('ccj-scatter-note').textContent = pts.length + ' programs' +
      (rho === null ? '' : ' · Spearman rank correlation = ' + rho.toFixed(2)) +
      (rankAxis(sx) || rankAxis(sy) ? ' (rank axes are reversed so better ranks sit up/right; the correlation uses the raw ranks)' : '') +
      '. Click a point to add it to the comparison.';
  }

  function renderTrends() {
    if (!R) return;
    var c = themeColors();
    var cmp = parseList(S.cmp);
    var labels = ['2000–04', '2005–09', '2010–14', 'Now'];
    var nowLabel = (S.y0 === S.y1 ? S.y0 : S.y0 + '–' + String(S.y1).slice(2));
    labels[3] = nowLabel;
    var traces = [];
    var items = D.programs.map(function (p) {
      return { p: p.i, name: p.short, ranks: p.km.concat([R.progs[p.i].rank_total]) };
    }).concat(D.former.map(function (f) {
      return { p: null, name: f.name + ' (former member)', ranks: f.km.concat([null]) };
    }));
    // Unselected programs first (grey), selected on top (color).
    items.sort(function (a, b) { return (cmp.indexOf(a.p) !== -1) - (cmp.indexOf(b.p) !== -1); });
    items.forEach(function (it) {
      var col = it.p !== null ? compareColor(it.p) : null;
      traces.push({
        type: 'scatter', mode: 'lines+markers', name: it.name,
        x: labels, y: it.ranks, connectgaps: false,
        line: { color: col || c.muted, width: col ? 3.5 : 1 },
        marker: { size: col ? 8 : 4, color: col || c.muted },
        opacity: col || !cmp.length ? 1 : 0.55,
        hovertemplate: '<b>' + escapeHtml(it.name) + '</b><br>%{x}: rank %{y}<extra></extra>'
      });
    });
    Plotly.react($('chart-trends'), traces, baseLayout({
      height: 560,
      yaxis: { autorange: 'reversed', title: { text: 'Rank on total credit' }, gridcolor: c.grid, dtick: 5 },
      xaxis: { gridcolor: c.grid, type: 'category' },
      margin: { t: 10, r: 20, l: 60, b: 40 }
    }), PLOTLY_CONFIG);
    $('ccj-trends-note').textContent = 'Earlier waves are the published ranks (Kleck et al., 2007; Kleck & Barnes, 2011; Kleck & Mims, 2017), each among the programs studied in that wave. ' +
      'The last point ranks programs on total ' + WEIGHTINGS[S.wt].short.toLowerCase() + ' under your current settings. Grey lines are other programs; pick programs in “Compare programs” to highlight them.';
  }

  function renderJournal() {
    if (!R) return;
    var c = themeColors();
    var j = D.journals[+S.jr];
    if (!j) return;
    var counts = {};
    var vals = {};
    D.rows.forEach(function (r) {
      if (D.articles[r.a].j !== j.i || !rowPasses(r, { ignoreJournal: true })) return;
      counts[r.p] = (counts[r.p] || 0) + 1;
      vals[r.p] = (vals[r.p] || 0) + rowValue(r, S.wt);
    });
    var ps = Object.keys(counts).map(Number).sort(function (a, b) { return counts[b] - counts[a] || vals[b] - vals[a]; });
    var srcLabel = { sorensen_2006: 'Sorensen et al. (2006) rating', calibrated_1992: 'calibrated Sorensen et al. (1992) rating', unrated_fallback_4: 'unrated (flat weight of 4)' };
    $('ccj-journal-info').innerHTML = '<strong>' + escapeHtml(j.name) + '</strong> · prestige weight ' + fmt(j.prestige, 2) +
      ' (' + (srcLabel[j.source] || j.source) + ')' +
      (j.top ? ' · one of Kleck & Mims’s top journals' : '') +
      ' · ' + ps.length + ' program' + (ps.length === 1 ? '' : 's') + ', ' +
      ps.reduce(function (s, p) { return s + counts[p]; }, 0) + ' faculty authorships in ' + (S.y0 === S.y1 ? S.y0 : S.y0 + '–' + S.y1);
    Plotly.react($('chart-journal'), [{
      type: 'bar', orientation: 'h',
      y: ps.map(function (p) { return D.programs[p].short; }),
      x: ps.map(function (p) { return counts[p]; }),
      marker: { color: ps.map(function (p) { return compareColor(p) || c.bar; }) },
      hovertemplate: '%{y}: %{x} authorships<extra></extra>'
    }], baseLayout({
      height: Math.max(220, ps.length * 20 + 60),
      xaxis: { title: { text: 'Faculty authorships' }, gridcolor: c.grid, dtick: ps.length && counts[ps[0]] < 10 ? 1 : null },
      yaxis: { autorange: 'reversed', automargin: true },
      margin: { t: 10, r: 20, l: 140, b: 40 }
    }), PLOTLY_CONFIG);
  }

  function renderProgramJournals() {
    if (!R) return;
    var c = themeColors();
    var el = $('chart-program-journals');
    if (S.jp === '' || !D.programs[+S.jp]) { el.innerHTML = '<p class="ccj-muted">Choose a program to see where its credit comes from.</p>'; return; }
    el.innerHTML = '';
    var p = +S.jp;
    var vals = {};
    var total = 0;
    R.rows.forEach(function (r) {
      if (r.p !== p) return;
      var j = D.articles[r.a].j;
      var v = rowValue(r, S.wt);
      vals[j] = (vals[j] || 0) + v;
      total += v;
    });
    var js = Object.keys(vals).map(Number).sort(function (a, b) { return vals[b] - vals[a]; }).slice(0, 15);
    Plotly.react(el, [{
      type: 'bar', orientation: 'h',
      y: js.map(function (j) { return D.journals[j].name; }),
      x: js.map(function (j) { return total ? 100 * vals[j] / total : 0; }),
      marker: { color: js.map(function (j) { return D.journals[j].top ? '#c62828' : c.bar; }) },
      hovertemplate: '%{y}: %{x:.1f}% of the program’s ' + WEIGHTINGS[S.wt].short.toLowerCase() + '<extra></extra>'
    }], baseLayout({
      height: Math.max(220, js.length * 22 + 60),
      xaxis: { title: { text: '% of ' + WEIGHTINGS[S.wt].short.toLowerCase() + ' (top 15 journals; red = top journal)' }, gridcolor: c.grid },
      yaxis: { autorange: 'reversed', automargin: true, tickfont: { size: 10 } },
      margin: { t: 10, r: 20, l: 260, b: 40 }
    }), PLOTLY_CONFIG);
  }

  // ------------------------------------------------------------ articles --
  function filteredArticles() {
    var q = (S.q || '').trim().toLowerCase();
    var ap = S.ap === '' ? null : +S.ap;
    var byArt = {};
    R.rows.forEach(function (r) {
      if (ap !== null && r.p !== ap) return;
      (byArt[r.a] = byArt[r.a] || []).push(r);
    });
    var list = Object.keys(byArt).map(Number).map(function (a) {
      return { art: D.articles[a], rows: byArt[a] };
    });
    if (q) {
      list = list.filter(function (x) {
        return x.art.title.toLowerCase().indexOf(q) !== -1 ||
          D.journals[x.art.j].name.toLowerCase().indexOf(q) !== -1 ||
          (x.art.doi || '').toLowerCase().indexOf(q) !== -1;
      });
    }
    list.sort(function (a, b) { return b.art.year - a.art.year || a.art.title.localeCompare(b.art.title); });
    return list;
  }

  function renderArticles() {
    if (!R) return;
    var list = filteredArticles();
    var pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
    S.pg = Math.min(Math.max(0, S.pg), pages - 1);
    var slice = list.slice(S.pg * PAGE_SIZE, (S.pg + 1) * PAGE_SIZE);
    var body = slice.map(function (x) {
      var progs = {};
      x.rows.forEach(function (r) { progs[r.p] = (progs[r.p] || 0) + 1; });
      var progTxt = Object.keys(progs).map(function (p) {
        return escapeHtml(D.programs[p].short) + (progs[p] > 1 ? ' (' + progs[p] + ')' : '');
      }).join(', ');
      var title = escapeHtml(x.art.title);
      if (x.art.doi) title = '<a href="https://doi.org/' + escapeHtml(x.art.doi) + '" target="_blank" rel="noopener">' + title + '</a>';
      return '<tr><td class="ccj-num">' + x.art.year + '</td><td>' + title + '</td><td>' +
        escapeHtml(D.journals[x.art.j].name) + '</td><td class="ccj-num">' + x.art.n + '</td><td>' + progTxt + '</td></tr>';
    }).join('');
    $('ccj-articles').innerHTML = '<thead><tr><th class="ccj-num">Year</th><th>Title</th><th>Journal</th>' +
      '<th class="ccj-num">Authors</th><th>Program(s) (faculty authors if &gt;1)</th></tr></thead><tbody>' +
      (body || '<tr><td colspan="5" class="ccj-muted">No articles match.</td></tr>') + '</tbody>';
    var pager = $('ccj-pager');
    pager.innerHTML = '<button type="button" ' + (S.pg === 0 ? 'disabled' : '') + ' data-pg="' + (S.pg - 1) + '">‹ Prev</button>' +
      '<span>' + fmt(list.length) + ' articles · page ' + (S.pg + 1) + ' of ' + pages + '</span>' +
      '<button type="button" ' + (S.pg >= pages - 1 ? 'disabled' : '') + ' data-pg="' + (S.pg + 1) + '">Next ›</button>';
    pager.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () { S.pg = +b.getAttribute('data-pg'); renderArticles(); writeState(); });
    });
  }

  function csvCell(v) {
    if (v === null || v === undefined) return '';
    var s = String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }

  function downloadCsv() {
    var list = filteredArticles();
    var lines = [['program', 'year', 'title', 'journal', 'doi', 'openalex_id', 'n_authors', 'byline_position',
      'faculty_rank', 'authorship_weight', 'journal_prestige_weight', 'value_' + S.wt].join(',')];
    list.forEach(function (x) {
      x.rows.forEach(function (r) {
        var j = D.journals[x.art.j];
        lines.push([D.programs[r.p].name, x.art.year, x.art.title, j.name, x.art.doi, x.art.id, x.art.n, r.byline,
          D.rankCats[r.r], r.w, j.prestige, rowValue(r, S.wt).toFixed(4)].map(csvCell).join(','));
      });
    });
    // BOM so Excel opens the UTF-8 file correctly.
    var blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'ccj-productivity-' + S.y0 + '-' + S.y1 + '.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function renderMeta() {
    var m = D.meta;
    var v = m.validation || {};
    $('ccj-meta').innerHTML = 'Release <strong>' + escapeHtml(m.release) + '</strong> · OpenAlex data pulled ' +
      escapeHtml(m.data_pulled) + ' · faculty rosters as of ' + escapeHtml(m.roster_reference) +
      ' · ' + fmt(m.counts.faculty) + ' faculty in ' + m.counts.programs + ' programs (' +
      fmt(m.counts.faculty - m.counts.faculty_resolved) + ' could not be matched and count as zero)';
    var vEl = $('ccj-validation');
    if (vEl) {
      vEl.textContent = 'Checked against hand counts from Web of Science and vitae for ' + v.people +
        ' randomly sampled faculty, the automated counts found ' + Math.round(100 * v.recall) +
        '% of their articles (recall), and ' + Math.round(100 * v.precision) + '% of the articles credited were confirmed (precision).';
    }
    var log = $('ccj-changelog');
    if (log && m.changelog) {
      log.innerHTML = m.changelog.map(function (c) {
        return '<li><strong>' + escapeHtml(c.release) + '</strong> (' + escapeHtml(c.date) + '): ' + escapeHtml(c.note) + '</li>';
      }).join('');
    }
  }

  // ---------------------------------------------------------------- init --
  function watchTheme() {
    var rerender = function () { if (R) { renderRankings(); renderCompare(); renderScatter(); renderTrends(); renderJournal(); renderProgramJournals(); } };
    var obs = new MutationObserver(rerender);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    obs.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-color-scheme: dark)');
      if (mq.addEventListener) mq.addEventListener('change', rerender);
    }
  }

  function thankReporter() {
    // Netlify Forms redirects back with ?reported=1 after a correction report.
    if (!new URLSearchParams(window.location.search).has('reported')) return;
    var form = $('correction-form');
    if (!form) return;
    var note = document.createElement('p');
    note.className = 'ccj-paper-note';
    note.style.display = 'block';
    note.textContent = 'Thank you. Your report was received and will get a decision in the next review batch.';
    form.parentNode.insertBefore(note, form);
  }

  function init() {
    thankReporter();
    fetch(DATA_URL, { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (raw) {
        D = decode(raw);
        readState();
        $('ccj-loading').style.display = 'none';
        $('ccj-content').style.display = '';
        buildControls();
        renderMeta();
        selfCheck();
        refresh();
        watchTheme();
      })
      .catch(function (err) {
        console.error('[ccj-productivity]', err);
        $('ccj-loading').style.display = 'none';
        var el = $('ccj-error');
        el.style.display = 'block';
        el.textContent = 'The dashboard data could not be loaded (' + err.message + ').';
      });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
