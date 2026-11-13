/* CCJ dashboard: coauthorship network card.
   Ported from the approved standalone page (scripts/network_page/ in the
   paper's repo). Data come from scripts/63_coauthor_network.R, copied to
   /data/ccj-network/. Faculty appear with names and article counts only; the
   public file carries no per-person credit. Needs d3 v7. */
(function () {
  'use strict';

  var BASE = '/data/ccj-network/';
  var ABBR = {"Michigan State University":"MSU","Arizona State University":"ASU","Florida State":"FSU","Sam Houston State":"SHSU","University of South Florida":"USF","Cincinnati":"Cincinnati","George Mason":"GMU","Rutgers University - Newark":"Rutgers","University of South Carolina":"S. Carolina","UMass Lowell":"UML","Northeastern":"Northeastern","University of California - Irvine":"UCI","University of Miami":"Miami","Texas State University":"Texas State","Pennsylvania State University":"Penn State","University of Nebraska - Omaha":"UNO","University of Central Florida":"UCF","University of Pennsylvania":"Penn","Temple University":"Temple","Florida International":"FIU","University of Maribor":"Maribor","University of Maryland":"Maryland","American University":"American","Georgia State":"GSU","University of Delaware":"Delaware","CUNY Graduate Center":"CUNY","University at Albany - SUNY":"Albany","University of Mississippi":"Ole Miss","University of Alabama":"Alabama","Southern Illinois University - Carbondale":"SIU","University of Missouri - St. Louis":"UMSL","University of Louisville":"Louisville","University of Texas - Dallas":"UTD","Washington State University":"WSU","Indiana University - Bloomington":"IU","University of Florida":"UF","University of New Haven":"New Haven","Tarleton State":"Tarleton","University of Arkansas - Little Rock":"UALR","Prairie View A&M":"PVAMU","UNLV":"UNLV","Texas Southern University":"TSU","Indiana University of Pennsylvania":"IUP","North Dakota State":"NDSU"};
  var TCOL = { 'Top third': 'var(--net-t1)', 'Middle third': 'var(--net-t2)', 'Bottom third': 'var(--net-t3)' };
  var CATS = [['Solo', 'net-c-solo', 'solo'], ['With another ranked program', 'net-c-other', 'other'],
              ['With program colleagues', 'net-c-coll', 'coll'], ['Outside coauthors only', 'net-c-out', 'out']];
  var W = 900, H = 680;

  function $(id) { return document.getElementById(id); }
  function ab(p) { return ABBR[p] || p; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function start(DATA) {
    var fmt1 = d3.format(',.1f'), fmt0 = d3.format(','), pct = d3.format('.0%');
    var prog = DATA.program, fac = DATA.faculty, S = DATA.summary;
    var nodes = prog.nodes.map(function (d) { return Object.assign({}, d); });
    var byId = new Map(nodes.map(function (d) { return [d.id, d]; }));
    var state = { sel: null, edge: null, minW: 1, sizeBy: 'total_credit' };
    try { var saved = JSON.parse(localStorage.getItem('ccjnet') || '{}'); if (saved.sizeBy) state.sizeBy = saved.sizeBy; } catch (e) {}
    function save() { try { localStorage.setItem('ccjnet', JSON.stringify({ sizeBy: state.sizeBy })); } catch (e) {} }

    // Coauthor ties per faculty member, counted from the edges.
    var facDegree = new Map();
    fac.edges.forEach(function (e) {
      facDegree.set(e.source, (facDegree.get(e.source) || 0) + 1);
      facDegree.set(e.target, (facDegree.get(e.target) || 0) + 1);
    });

    // Facts strip
    var F = function (k) { return +S[k]; };
    var nProg = nodes.length, possible = nProg * (nProg - 1) / 2;
    $('ccj-net-facts').innerHTML = [
      [fmt0(F('program pairs sharing >= 1 article')), 'program pairs share at least one article (of ' + fmt0(possible) + ' possible)'],
      [fmt0(F('articles linking >= 2 programs')), 'articles have authors now at two or more programs'],
      [pct(F('share of distinct articles: roster authors at 2+ programs')), 'of the ' + fmt0(F('distinct articles')) + ' articles have authors at two or more programs (' + pct(F('share of program-articles: with another ranked program')) + ' when each program counts its own copy)'],
      [d3.format('+.2f')(F('rank assortativity (total-credit rank)')), 'rank assortativity: top programs don’t mainly coauthor with each other']
    ].map(function (x) { return '<div class="ccj-net-fact"><span class="v">' + x[0] + '</span><span class="k">' + x[1] + '</span></div>'; }).join('');
    $('ccj-net-mix').textContent = pct(F('share of distinct articles: solo')) + ' are solo, ' +
      pct(F('share of distinct articles: one roster author, outside coauthors only')) + ' have one program’s faculty member writing with outside coauthors only, ' +
      pct(F('share of distinct articles: 2+ roster authors, same program')) + ' have two or more faculty from the same program, and ' +
      pct(F('share of distinct articles: roster authors at 2+ programs')) + ' have faculty at two or more programs.';

    // Program network
    var svg = d3.select('#ccj-net-svg');
    var gL = svg.append('g'), gN = svg.append('g');
    var tip = $('ccj-net-tip');
    function showTip(ev, html) {
      tip.innerHTML = html; tip.hidden = false;
      tip.style.left = Math.min(ev.clientX + 12, innerWidth - 300) + 'px';
      tip.style.top = (ev.clientY + 12) + 'px';
    }
    function hideTip() { tip.hidden = true; }

    function currentLinks() {
      return prog.edges.filter(function (e) { return e.n_works >= state.minW; })
        .map(function (e) { return Object.assign({}, e, { w: e.n_works, source: byId.get(e.source), target: byId.get(e.target) }); });
    }
    var links = [];
    function layout() {
      links = currentLinks();
      var r = d3.scaleSqrt().domain([0, d3.max(nodes, function (d) { return d[state.sizeBy]; })]).range([4, 28]);
      nodes.forEach(function (d) { d.r = r(d[state.sizeBy]); });
      var wMax = d3.max(links, function (l) { return l.w; }) || 1;
      var sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(function (d) { return d.id; })
          .distance(function (l) { return 150 - 90 * Math.sqrt(l.w / wMax); })
          .strength(function (l) { return 0.15 + 0.5 * Math.sqrt(l.w / wMax); }))
        .force('charge', d3.forceManyBody().strength(-260))
        .force('collide', d3.forceCollide(function (d) { return d.r + 8; }))
        .force('x', d3.forceX(W / 2).strength(0.06)).force('y', d3.forceY(H / 2).strength(0.08))
        .stop();
      for (var i = 0; i < 400; i++) sim.tick();
      nodes.forEach(function (d) {
        d.x = Math.max(d.r + 24, Math.min(W - d.r - 24, d.x));
        d.y = Math.max(d.r + 14, Math.min(H - d.r - 16, d.y));
      });
      fitView();
      draw();
    }
    // The force layout settles into the middle of the canvas, which left the
    // labels piled up at the dashboard's card width. Zoom the view box to the
    // network's extent (circles plus labels), keeping the canvas's aspect ratio.
    function fitView() {
      var pad = 18;
      var x0 = d3.min(nodes, function (d) { return d.x - d.r - 22; }) - pad;
      var x1 = d3.max(nodes, function (d) { return d.x + d.r + 22; }) + pad;
      var y0 = d3.min(nodes, function (d) { return d.y - d.r; }) - pad;
      var y1 = d3.max(nodes, function (d) { return d.y + d.r + 14; }) + pad;
      var w = x1 - x0, h = y1 - y0, aspect = W / H;
      if (w / h > aspect) { var nh = w / aspect; y0 -= (nh - h) / 2; h = nh; }
      else { var nw = h * aspect; x0 -= (nw - w) / 2; w = nw; }
      svg.attr('viewBox', [x0, y0, w, h].join(' '));
    }
    function select(p, edge) { state.sel = p; state.edge = edge || null; render(); }
    function draw() {
      var wMax = d3.max(links, function (l) { return l.w; }) || 1;
      var sw = d3.scaleSqrt().domain([1, wMax]).range([0.8, 9]);
      gL.selectAll('line').data(links, function (l) { return l.source.id + '|' + l.target.id; }).join('line')
        .attr('class', 'ccj-net-link')
        .attr('x1', function (l) { return l.source.x; }).attr('y1', function (l) { return l.source.y; })
        .attr('x2', function (l) { return l.target.x; }).attr('y2', function (l) { return l.target.y; })
        .attr('stroke-width', function (l) { return sw(l.w); })
        .on('mousemove', function (ev, l) { showTip(ev, '<b>' + esc(ab(l.source.id)) + ' – ' + esc(ab(l.target.id)) + '</b><br>' + l.n_works + ' shared article' + (l.n_works === 1 ? '' : 's')); })
        .on('mouseleave', hideTip)
        .on('click', function (ev, l) { select(l.source.id, l.target.id); });
      var g = gN.selectAll('g.ccj-net-node').data(nodes, function (d) { return d.id; }).join(function (enter) {
        var e = enter.append('g').attr('class', 'ccj-net-node').attr('tabindex', 0).attr('role', 'button');
        e.append('circle'); e.append('text').attr('text-anchor', 'middle');
        return e;
      });
      g.attr('transform', function (d) { return 'translate(' + d.x + ',' + d.y + ')'; }).attr('aria-label', function (d) { return d.id; })
        .on('mousemove', function (ev, d) { showTip(ev, '<b>' + esc(d.id) + '</b><br>Rank ' + d.rank + ' by total credit · ' + fmt1(d.total_credit) + ' credit<br>' + d.n_faculty + ' faculty · ' + fmt1(d.credit_per_faculty) + ' per faculty'); })
        .on('mouseleave', hideTip)
        .on('click', function (ev, d) { select(d.id); })
        .on('keydown', function (ev, d) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(d.id); } });
      g.select('circle').attr('r', function (d) { return d.r; }).attr('fill', function (d) { return TCOL[d.tertile]; });
      g.select('text').attr('dy', function (d) { return d.r + 11; }).text(function (d) { return ab(d.id); });
      highlight();
    }
    function highlight() {
      var s = state.sel;
      var nb = new Set();
      if (s) links.forEach(function (l) { if (l.source.id === s || l.target.id === s) { nb.add(l.source.id); nb.add(l.target.id); } });
      gN.selectAll('g.ccj-net-node').classed('dim', function (d) { return s && !nb.has(d.id) && d.id !== s; })
        .classed('sel', function (d) { return d.id === s; });
      gL.selectAll('line').classed('dim', function (l) { return s && l.source.id !== s && l.target.id !== s; })
        .classed('hot', function (l) {
          return s && state.edge && ((l.source.id === s && l.target.id === state.edge) || (l.target.id === s && l.source.id === state.edge));
        });
    }

    // Detail panel
    var profByProg = d3.group(DATA.profile, function (d) { return d.program; });
    function profileOf(p) {
      var rows = profByProg.get(p) || [];
      var o = { n: rows[0] ? +rows[0].n_articles : 0 };
      CATS.forEach(function (c) { var r = rows.find(function (x) { return x.category === c[0]; }); o[c[2]] = r ? +r.share : 0; });
      return o;
    }
    function stackHTML(o) {
      return '<div class="ccj-net-stack" aria-hidden="true">' + CATS.map(function (c) {
        return '<i class="' + c[1] + '" style="width:' + (o[c[2]] * 100) + '%" title="' + c[0] + ': ' + pct(o[c[2]]) + '"></i>';
      }).join('') + '</div>';
    }
    function partnersOf(p) {
      return prog.edges.filter(function (e) { return e.source === p || e.target === p; })
        .map(function (e) { return { other: e.source === p ? e.target : e.source, e: e, w: e.n_works }; })
        .filter(function (x) { return x.w > 0; })
        .sort(function (a, b) { return b.w - a.w || a.other.localeCompare(b.other); });
    }
    function papersHTML(e) {
      return '<div class="ccj-net-papers">' + e.works.map(function (w) {
        return '<div class="ccj-net-paper"><span class="t">' + esc(w.title) + '</span><span class="m">' + esc(w.venue) + ' · ' + w.year + ' · ' + esc(w.authors) + '</span></div>';
      }).join('') + '</div>';
    }
    function renderPanel() {
      var el = $('ccj-net-panel');
      var p = state.sel;
      if (!p) {
        el.innerHTML = '<div class="ccj-net-eyebrow">Select a program</div><h4>Click any circle</h4><p class="ccj-note">Circle size shows the chosen measure and color shows the credit tertile. Line width shows the number of shared articles. Click a line to list the papers behind it.</p>';
        return;
      }
      var d = byId.get(p), o = profileOf(p), parts = partnersOf(p);
      var max = d3.max(parts, function (x) { return x.w; }) || 1;
      var html = '<div><div class="ccj-net-eyebrow">Rank ' + d.rank + ' by total credit · ' + d.tertile.toLowerCase() + '</div><h4>' + esc(p) + '</h4></div>' +
        '<div class="ccj-net-stats">' +
        '<div><span class="v">' + fmt1(d.total_credit) + '</span><span class="k">total credit</span></div>' +
        '<div><span class="v">' + fmt1(d.credit_per_faculty) + '</span><span class="k">credit per faculty (rank ' + d.rank_per_faculty + ')</span></div>' +
        '<div><span class="v">' + parts.length + '</span><span class="k">partner programs</span></div>' +
        '<div><span class="v">' + d.n_faculty + '</span><span class="k">faculty on the January 2025 roster</span></div></div>' +
        '<div class="ccj-net-block"><span class="ccj-net-eyebrow">Its ' + fmt0(o.n) + ' articles</span>' + stackHTML(o) +
        '<span class="ccj-note">' + pct(o.solo) + ' solo · ' + pct(o.other) + ' with another program · ' + pct(o.coll) + ' with colleagues · ' + pct(o.out) + ' outside coauthors only</span></div>';
      if (state.edge) {
        var e = prog.edges.find(function (x) { return (x.source === p && x.target === state.edge) || (x.target === p && x.source === state.edge); });
        html += '<div class="ccj-net-block"><div class="ccj-net-row"><span class="ccj-net-eyebrow">Shared with ' + esc(state.edge) + '</span>' +
          '<button type="button" class="ccj-net-back" id="ccj-net-back">All partners</button></div>' + (e ? papersHTML(e) : '') + '</div>';
      } else {
        html += '<div class="ccj-net-block"><span class="ccj-net-eyebrow">Partner programs (shared articles)</span><div class="ccj-net-partners">' +
          (parts.map(function (x) {
            return '<button type="button" class="ccj-net-partner" data-p="' + esc(x.other) + '"><span>' + esc(x.other) + '</span><span class="bar" style="width:' + Math.max(4, 90 * x.w / max) + 'px"></span><span class="n">' + x.w + '</span></button>';
          }).join('') || '<p class="ccj-note">No shared articles at this setting.</p>') + '</div></div>';
      }
      html += '<div class="ccj-net-block ccj-net-ego"><span class="ccj-net-eyebrow">Faculty network</span><svg id="ccj-net-ego" viewBox="0 0 420 300" role="img" aria-label="Faculty coauthorship network for ' + esc(p) + '"></svg>' +
        '<span class="ccj-note">Filled circles are ' + esc(ab(p)) + ' faculty, sized by their credited articles; grey circles are their coauthors at other programs.</span></div>';
      el.innerHTML = html;
      el.querySelectorAll('.ccj-net-partner[data-p]').forEach(function (b) { b.onclick = function () { state.edge = b.dataset.p; render(); }; });
      var back = $('ccj-net-back'); if (back) back.onclick = function () { state.edge = null; render(); };
      drawEgo(p);
    }
    function drawEgo(p) {
      var own = new Set(fac.nodes.filter(function (n) { return n.program === p; }).map(function (n) { return n.id; }));
      var es = fac.edges.filter(function (e) { return own.has(e.source) || own.has(e.target); });
      var ids = new Set(own); es.forEach(function (e) { ids.add(e.source); ids.add(e.target); });
      var fn = fac.nodes.filter(function (n) { return ids.has(n.id); }).map(function (n) { return Object.assign({}, n, { own: own.has(n.id) }); });
      var fl = es.map(function (e) { return Object.assign({}, e); });
      var r = d3.scaleSqrt().domain([0, d3.max(fn, function (n) { return n.authorships; }) || 1]).range([2.5, 11]);
      var sim = d3.forceSimulation(fn).force('link', d3.forceLink(fl).id(function (n) { return n.id; }).distance(40))
        .force('charge', d3.forceManyBody().strength(-40)).force('collide', d3.forceCollide(function (n) { return r(n.authorships) + 2; }))
        .force('x', d3.forceX(210).strength(0.07)).force('y', d3.forceY(150).strength(0.1)).stop();
      for (var i = 0; i < 300; i++) sim.tick();
      fn.forEach(function (n) { n.x = Math.max(12, Math.min(408, n.x)); n.y = Math.max(10, Math.min(290, n.y)); });
      var s = d3.select('#ccj-net-ego');
      s.append('g').selectAll('line').data(fl).join('line')
        .attr('x1', function (l) { return l.source.x; }).attr('y1', function (l) { return l.source.y; })
        .attr('x2', function (l) { return l.target.x; }).attr('y2', function (l) { return l.target.y; })
        .attr('stroke', function (l) { return l.tie_type === 'same_program' ? 'var(--net-teal)' : 'var(--text-muted, #666)'; })
        .attr('stroke-opacity', 0.5).attr('stroke-width', function (l) { return Math.min(4, 0.6 + 0.5 * l.n_works); });
      var g = s.append('g').selectAll('g').data(fn).join('g').attr('transform', function (n) { return 'translate(' + n.x + ',' + n.y + ')'; });
      g.append('circle').attr('r', function (n) { return r(n.authorships); })
        .attr('fill', function (n) { return n.own ? 'var(--net-accent)' : 'var(--net-then)'; }).attr('stroke', 'var(--net-surface)')
        .on('mousemove', function (ev, n) { showTip(ev, '<b>' + esc(n.name) + '</b><br>' + esc(n.program) + '<br>' + n.authorships + ' credited article' + (n.authorships === 1 ? '' : 's')); })
        .on('mouseleave', hideTip);
      g.filter(function (n) { return n.own && (facDegree.get(n.id) || 0) > 0; }).append('text').attr('text-anchor', 'middle')
        .attr('dy', function (n) { return -r(n.authorships) - 3; })
        .text(function (n) { return n.name.split(' ').slice(-1)[0]; });
    }

    // Profile table
    function renderTable() {
      var key = $('ccj-net-sort').value;
      var rows = nodes.map(function (d) { return Object.assign({ p: d.id }, profileOf(d.id)); })
        .sort(function (a, b) { return (b[key] - a[key]) || a.p.localeCompare(b.p); });
      $('ccj-net-table').innerHTML = '<div class="ccj-net-prow head"><span>Program</span><span>Article mix</span><span class="num">Articles</span><span class="num">With another program</span></div>' +
        rows.map(function (r) {
          return '<div class="ccj-net-prow click" data-p="' + esc(r.p) + '" tabindex="0"><span class="name" title="' + esc(r.p) + '">' + esc(r.p) + '</span>' + stackHTML(r) +
            '<span class="num">' + fmt0(r.n) + '</span><span class="num">' + pct(r.other) + '</span></div>';
        }).join('');
      document.querySelectorAll('.ccj-net-prow.click').forEach(function (row) {
        var go = function () { select(row.dataset.p); $('ccj-net-svg').scrollIntoView({ behavior: 'smooth', block: 'center' }); };
        row.onclick = go;
        row.onkeydown = function (ev) { if (ev.key === 'Enter') go(); };
      });
    }

    function render() { highlight(); renderPanel(); }
    var sizeSel = $('ccj-net-size'), minW = $('ccj-net-minw');
    sizeSel.value = state.sizeBy;
    sizeSel.onchange = function () { state.sizeBy = sizeSel.value; save(); layout(); renderPanel(); };
    minW.oninput = function () { state.minW = +minW.value; $('ccj-net-minwv').textContent = minW.value; layout(); renderPanel(); };
    $('ccj-net-sort').onchange = renderTable;
    svg.on('click', function (ev) { if (ev.target === svg.node()) select(null); });
    $('ccj-net-built').textContent = 'Network built ' + prog.built + ' from the same data as the rankings above.';
    $('ccj-net-loading').style.display = 'none';
    $('ccj-net-body').style.display = '';
    layout(); renderPanel(); renderTable();
  }

  function load() {
    var get = function (f) { return fetch(BASE + f, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(f + ': HTTP ' + r.status); return r; }); };
    Promise.all([
      get('program_network.json').then(function (r) { return r.json(); }),
      get('faculty_network.json').then(function (r) { return r.json(); }),
      get('collab_profile.csv').then(function (r) { return r.text(); }),
      get('network_summary.csv').then(function (r) { return r.text(); })
    ]).then(function (x) {
      var summary = {};
      d3.csvParse(x[3]).forEach(function (r) { summary[r.statistic] = r.value; });
      start({ program: x[0], faculty: x[1], profile: d3.csvParse(x[2]), summary: summary });
    }).catch(function (err) {
      var el = $('ccj-net-loading');
      el.className = 'ccj-error';
      el.textContent = 'The network could not be loaded (' + err.message + ').';
    });
  }

  // Load the network only when its card comes near the viewport: the faculty
  // file is about 220 KB and most visitors start with the rankings.
  function init() {
    var card = $('network');
    if (!card || typeof d3 === 'undefined') return;
    if (!('IntersectionObserver' in window)) { load(); return; }
    var obs = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) { obs.disconnect(); load(); }
    }, { rootMargin: '400px' });
    obs.observe(card);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
