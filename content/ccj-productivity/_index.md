---
title: "Article Productivity of CCJ Doctoral Programs"
summary: "Interactive rankings of criminology and criminal justice doctoral programs by faculty article productivity, 2020 onward"
type: page
reading_time: false
share: true
profile: false
comments: false
# Kept as a draft while the accompanying paper is under double-blind review:
# a public page built from the same data would identify the authors. Hugo
# skips drafts on Netlify; preview locally with `hugo server -D`. To launch,
# delete this line and uncomment the menu entry in config/_default/menus.toml.
draft: true
---

Which criminology and criminal justice doctoral programs' faculty publish the most refereed articles, and in which journals? This dashboard extends a series of studies that began with Kleck, Wang, and Tark (2007), continued with Kleck and Barnes (2011), and most recently Kleck and Mims (2017). It covers the 44 member programs of the [Association of Doctoral Programs in Criminology and Criminal Justice](https://adpccj.com/members).

Every number on this page is recomputed in your browser from article-level data. Change the years, the weighting, the journals counted, or the faculty included, and the rankings, charts, and article list all update. The address bar keeps your settings, so you can share any view by copying the link.

{{% alert note %}}
The default settings reproduce the published rankings. The other settings are for exploration: they are not the paper's method, and small differences between neighboring programs rarely mean much (see *How the numbers work* below).
{{% /alert %}}

---

<link rel="stylesheet" href="/css/ccj-productivity.css">

<div id="ccj-dashboard" class="ccj-dashboard-container">
  <div id="ccj-loading" class="ccj-loading"><p>Loading dashboard data...</p></div>
  <div id="ccj-error" class="ccj-error" style="display:none;"></div>
  <div id="ccj-content" style="display:none;">
    <div id="ccj-check" class="ccj-check"></div>
    <div id="ccj-meta" class="ccj-meta"></div>

    <div class="ccj-controls" role="region" aria-label="Dashboard settings">
      <div class="ccj-control-grid">
        <div class="ccj-control">
          <label class="ccj-label" for="ccj-y0">Issue years</label>
          <div class="ccj-years"><select id="ccj-y0" aria-label="First year"></select><span>to</span><select id="ccj-y1" aria-label="Last year"></select></div>
        </div>
        <div class="ccj-control">
          <label class="ccj-label" for="ccj-wt">Weighting</label>
          <select id="ccj-wt"></select>
        </div>
        <div class="ccj-control">
          <label class="ccj-label" for="ccj-meas">Measure</label>
          <select id="ccj-meas">
            <option value="total">Program total</option>
            <option value="pf">Per faculty member</option>
          </select>
        </div>
        <div class="ccj-control">
          <label class="ccj-label" for="ccj-js">Journals</label>
          <select id="ccj-js">
            <option value="all">All refereed journals</option>
            <option value="top">Top journals only (rated above 8.0)</option>
            <option value="rated">Prestige-rated journals only</option>
            <option value="nolaw">Exclude law reviews</option>
          </select>
        </div>
        <div class="ccj-control">
          <label class="ccj-label" for="ccj-byl">Authorships</label>
          <select id="ccj-byl">
            <option value="all">All bylines</option>
            <option value="first">First or sole author only</option>
          </select>
        </div>
      </div>
      <div class="ccj-control">
        <div id="ccj-rk" class="ccj-rank-boxes" aria-label="Faculty ranks included"></div>
      </div>
      <div class="ccj-control-footer">
        <span id="ccj-wt-help"></span>
        <span><a href="#" id="ccj-copy-link">Copy link to this view</a><a href="#" id="ccj-reset">Reset to the paper's settings</a></span>
      </div>
    </div>

    <div id="ccj-paper-note" class="ccj-paper-note">You have changed the paper's settings, so these rankings differ from the published tables by design. "vs. paper" in the table shows how far each program moved.</div>

    <div id="ccj-stats" class="ccj-stats-row"></div>

    <div class="ccj-card" id="rankings">
      <h3>Rankings</h3>
      <div class="ccj-sub" id="ccj-rank-note"></div>
      <div id="chart-rankings" class="ccj-chart"></div>
      <div class="ccj-table-wrap"><table id="ccj-rank-table" class="ccj-table"></table></div>
    </div>

    <div class="ccj-card" id="compare">
      <h3>Compare programs</h3>
      <div class="ccj-sub">Pick up to six programs. They stay highlighted in every chart on the page.</div>
      <div class="ccj-inline"><div><select id="ccj-cmp-add" aria-label="Add a program to compare"></select></div></div>
      <div id="ccj-chips" class="ccj-chips"></div>
      <div id="ccj-compare-charts">
        <h4 class="ccj-note">By issue year</h4>
        <div id="chart-compare-years" class="ccj-chart"></div>
        <div class="ccj-two-col">
          <div>
            <h4 class="ccj-note">Share of each program's credit from the selection's eight biggest journals</h4>
            <div id="chart-compare-journals" class="ccj-chart"></div>
          </div>
          <div>
            <h4 class="ccj-note">Share of faculty authorships by byline position</h4>
            <div id="chart-compare-byline" class="ccj-chart"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="ccj-card" id="scatter">
      <h3>Build your own scatterplot</h3>
      <div class="ccj-sub">Plot any two program-level measures against each other.</div>
      <div class="ccj-inline">
        <div><label class="ccj-label" for="ccj-sx">Horizontal axis</label><select id="ccj-sx"></select></div>
        <div><label class="ccj-label" for="ccj-sy">Vertical axis</label><select id="ccj-sy"></select></div>
      </div>
      <div id="chart-scatter" class="ccj-chart"></div>
      <div class="ccj-note" id="ccj-scatter-note"></div>
    </div>

    <div class="ccj-card" id="trends">
      <h3>Rank trends across waves, 2000&ndash;2004 to now</h3>
      <div id="chart-trends" class="ccj-chart"></div>
      <div class="ccj-note" id="ccj-trends-note"></div>
    </div>

    <div class="ccj-card" id="animations">
      <h3>Two findings, animated</h3>
      <div class="ccj-sub">Short animations of figures from the paper. They show the paper's settings and do not change with the controls above.</div>
      <div class="ccj-two-col">
        <figure class="ccj-video ccj-video-portrait">
          <video controls muted playsinline preload="none" poster="/video/ccj-productivity/animation_rank_change_pf_poster.png" aria-describedby="ccj-anim-pf">
            <source src="/video/ccj-productivity/animation_rank_change_pf.mp4" type="video/mp4">
          </video>
          <figcaption id="ccj-anim-pf" class="ccj-note"><strong>Rank on credit per faculty.</strong> The 36 programs ranked in both 2010&ndash;2014 (Kleck &amp; Mims, 2017) and 2020&ndash;2024 move from their earlier order to their current one. Programs that moved up are blue.</figcaption>
        </figure>
        <figure class="ccj-video ccj-video-portrait">
          <video controls muted playsinline preload="none" poster="/video/ccj-productivity/animation_rank_change_total_poster.png" aria-describedby="ccj-anim-total">
            <source src="/video/ccj-productivity/animation_rank_change_total.mp4" type="video/mp4">
          </video>
          <figcaption id="ccj-anim-total" class="ccj-note"><strong>Rank on total credit.</strong> The same 36 programs on the measure Kleck and Mims ranked by, which does not adjust for program size.</figcaption>
        </figure>
      </div>
      <figure class="ccj-video">
        <video controls muted playsinline preload="none" poster="/video/ccj-productivity/animation_volume_prestige_poster.png" aria-describedby="ccj-anim-vp">
          <source src="/video/ccj-productivity/animation_volume_prestige.mp4" type="video/mp4">
        </video>
        <figcaption id="ccj-anim-vp" class="ccj-note"><strong>Volume vs. prestige depends on which journals count as &ldquo;top.&rdquo;</strong> Each dot is a program: authorships per faculty member (across) against the share of its authorships in eight top journals (up). The animation steps through three definitions of the top eight: Kleck and Mims's list (Sorensen et al., 2006), the DeJong and St. George (2018) survey, and Google Scholar Metrics' Criminology, Criminal Law &amp; Policing category (h5-index). The seven programs highest on each list are labeled.</figcaption>
      </figure>
    </div>

    <div class="ccj-card" id="journals">
      <h3>Journals</h3>
      <div class="ccj-two-col">
        <div>
          <div class="ccj-inline"><div><label class="ccj-label" for="ccj-jr">Which programs publish in…</label>
            <input type="search" id="ccj-jr" list="ccj-journal-list" placeholder="Type a journal name" autocomplete="off">
            <datalist id="ccj-journal-list"></datalist></div></div>
          <div class="ccj-note" id="ccj-journal-info"></div>
          <div id="chart-journal" class="ccj-chart"></div>
        </div>
        <div>
          <div class="ccj-inline"><div><label class="ccj-label" for="ccj-jp">Where does a program publish?</label><select id="ccj-jp"></select></div></div>
          <div id="chart-program-journals" class="ccj-chart"></div>
        </div>
      </div>
    </div>

    <div class="ccj-card" id="articles">
      <h3>Articles</h3>
      <div class="ccj-sub">Every article credited under the current settings. Faculty names are not shown.</div>
      <div class="ccj-inline">
        <div><label class="ccj-label" for="ccj-ap">Program</label><select id="ccj-ap"></select></div>
        <div><label class="ccj-label" for="ccj-q">Search titles, journals, DOIs</label><input type="search" id="ccj-q" placeholder="e.g., body-worn cameras"></div>
        <div style="flex:0 0 auto"><button type="button" class="ccj-button" id="ccj-download">Download CSV</button></div>
      </div>
      <div class="ccj-table-wrap"><table id="ccj-articles" class="ccj-table"></table></div>
      <div id="ccj-pager" class="ccj-pager"></div>
    </div>
  </div>
</div>

<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="/js/ccj-productivity.js"></script>

## How the numbers work

**Who counts.** Regular faculty (assistant, associate, and full professors, plus research professors) listed on each program's website, following Kleck and Mims (2017). Faculty whose principal appointment is in another department are excluded. Credit follows the person: a faculty member's articles count for their current program, even when the work was done elsewhere. Faculty who could not be matched to a publication record stay in their program's denominator with zero credit.

**What counts.** Refereed, English-language articles in journals, assigned to the year of the issue they appear in (not the year they were posted online). Publications come from [OpenAlex](https://openalex.org), with Crossref for issue years and author order. Namesake articles, editorials, book reviews, and similar items were removed by hand review.

**Credit.** Each faculty authorship earns a byline weight (sole author 1.0; first of two .60, second .40; first of three .40, then .35 and .25; with four or more authors, .40 for the first and .60 split among the rest) times a journal weight: the journal's prestige rating from Sorensen, Snell, and Rodriguez (2006), a calibrated rating from Sorensen, Patterson, and Widmayer (1992), or 4 for unrated journals. Two faculty from the same program on one article each earn their own credit.

**How much to trust it.** <span id="ccj-validation"></span> The automated counts miss some articles and include a few that do not belong, so treat gaps of a rank or two between neighboring programs as noise. Credit-per-faculty rankings are especially sensitive for small programs, where one prolific scholar can carry the whole program.

**Updates.** New years are added after each data refresh, and every refresh is reviewed by hand before it appears here. Because rosters are refreshed too, numbers for earlier years can shift when faculty move between programs.

<ul id="ccj-changelog" class="ccj-note"></ul>

The underlying data, code, and paper will be linked here on publication.

## Found a mistake?

With more than 700 faculty and 5,000 articles, there will be some. If you find one, please tell me using the form below. Every report gets a decision, and every correction appears in the release notes above.

**What I will correct:** an article credited to the wrong person (a namesake), a missing article, a credited item that is not a refereed research article (an editorial, book review, review report, or interview), an article assigned to the wrong issue year, or a faculty member wrongly counted or left out under the rules above.

**What I will log but not change on request:** disagreements with the rules themselves, such as counting books, crediting articles to the program where the work was done, or a different authorship weighting. These are fair debates, and the settings above let you see how much they matter. Rule changes, if any, would apply to every program at once in a future release.

**What helps:** a DOI or link for each article, and for faculty questions, a link to a vita or the program's faculty page. Reports are reviewed in batches, usually within two weeks, and corrections appear in the next release.

<form name="ccj-correction" method="POST" data-netlify="true" netlify-honeypot="company" action="/ccj-productivity/?reported=1#correction-form" id="correction-form" class="ccj-card ccj-report-form">
  <input type="hidden" name="form-name" value="ccj-correction">
  <p style="display:none"><label>Leave this empty: <input name="company"></label></p>
  <div class="ccj-inline">
    <div><label class="ccj-label" for="rep-program">Program</label><input type="text" id="rep-program" name="program" required></div>
    <div><label class="ccj-label" for="rep-type">What kind of problem?</label>
      <select id="rep-type" name="claim_type" required>
        <option value="">Choose one…</option>
        <option value="namesake">Article credited to the wrong person</option>
        <option value="missing">Article missing</option>
        <option value="not_article">Not a refereed research article</option>
        <option value="year">Wrong issue year</option>
        <option value="roster">Faculty member wrongly counted or left out</option>
        <option value="other">Something else</option>
      </select></div>
  </div>
  <div class="ccj-inline">
    <div><label class="ccj-label" for="rep-doi">Article DOI or title (if about an article)</label><input type="text" id="rep-doi" name="doi_or_title"></div>
    <div><label class="ccj-label" for="rep-evidence">Evidence link (DOI, vita, faculty page)</label><input type="url" id="rep-evidence" name="evidence_url" placeholder="https://"></div>
  </div>
  <div class="ccj-control"><label class="ccj-label" for="rep-desc">Details</label><textarea id="rep-desc" name="description" rows="4" required style="width:100%"></textarea></div>
  <div class="ccj-inline">
    <div><label class="ccj-label" for="rep-email">Your email (optional, only to follow up)</label><input type="email" id="rep-email" name="email"></div>
    <div style="flex:0 0 auto"><button type="submit" class="ccj-button">Send report</button></div>
  </div>
</form>
