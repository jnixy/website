---
title: "Police Shooting Research Tracker"
summary: "Recent academic publications on police shootings and use of deadly force"
type: page
reading_time: false
share: false
profile: false
comments: false
---

**Updated weekly** | [RSS Feed](/data/police-shooting-research.xml)

This page tracks recent academic publications on police-involved shootings and use of deadly force. Articles are automatically gathered from academic databases including Crossref and PubMed, and restricted to a whitelist of criminology, public policy, sociology, and public-health journals.

## Research areas covered:

* **Incident patterns**: Frequency, circumstances, and trends in police shootings
* **Racial disparities**: Demographic patterns in police use of deadly force
* **Policy interventions**: Training, de-escalation, and reform effectiveness
* **Legal outcomes**: Criminal prosecutions and civil litigation
* **Public health**: Community impacts and trauma
* **Officer behavior**: Decision-making and use-of-force determinants

**Subscribe**: [RSS Feed](/data/police-shooting-research.xml)

---

<link rel="stylesheet" href="/css/news-feed.css">

<div id="research-feed" class="news-feed-container">
  <div class="news-loading">
    <p>Loading latest research...</p>
  </div>
</div>

<script src="/js/news-feed.js"></script>
<script>
// Police Shooting Research Feed Configuration
(function() {
  function renderResearchCard(story, isFeatured) {
    var cardClass = 'news-card' + (story.priority ? ' featured' : '');
    var abstract = story.abstract || '';
    if (abstract.length > 220) {
      abstract = abstract.slice(0, 220) + '…';
    }

    var html = '<article class="' + cardClass + '" role="listitem" tabindex="0">' +
      '<div class="card-header">' +
        '<div class="card-source">' + escapeHtml(story.journal || 'Academic Journal') + '</div>';

    if (story.priority) {
      html += '<span class="featured-badge">★ Key Journal</span>';
    }

    html += '</div>' +
      '<div class="card-body">' +
        '<h3 class="card-title">' + escapeHtml(story.title) + '</h3>' +
        (story.authors ? '<p style="font-style:italic;font-size:0.85rem;color:var(--text-muted,#666);margin:0 0 0.5rem 0;">' + escapeHtml(story.authors) + '</p>' : '') +
        (abstract ? '<p style="font-size:0.85rem;line-height:1.5;margin:0;">' + escapeHtml(abstract) + '</p>' : '') +
      '</div>' +
      '<div class="card-footer">' +
        '<span class="card-date">' + formatDate(story.date) + '</span>' +
        '<a href="' + escapeHtml(story.url) + '" target="_blank" rel="noopener">Read Article →</a>' +
      '</div>' +
    '</article>';

    return html;
  }

  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, '&#39;').replace(/"/g, '&quot;');
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    var date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    var diffDays = Math.ceil(Math.abs(new Date() - date) / (1000 * 60 * 60 * 24));
    if (diffDays <= 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays < 30) return Math.floor(diffDays) + ' days ago';
    if (diffDays < 60) return 'About a month ago';
    if (diffDays < 90) return 'About 2 months ago';
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  new NewsFeed({
    containerId: 'research-feed',
    jsonPath: '/data/police-shooting-research.json',
    cardsPerPage: 12,
    filterField: null,
    filterTypes: [],
    dateField: 'date',
    renderCard: renderResearchCard,
    hasFeatured: false
  });
})();
</script>
