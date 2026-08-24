---
title: "U.S. Police Shooting News Tracker"
summary: "Automatically tracking news and developments on police-involved shootings in the United States"
type: page
reading_time: false
share: false
profile: false
comments: false
---

**Automatically updated daily** | [RSS Feed](/data/police-shooting-news.xml)

This page automatically tracks news, research, and developments related to police-involved shootings in the United States. The feed is updated daily and includes incident reports, investigations, policy decisions, court proceedings, and accountability measures.

The news aggregator monitors multiple sources including law enforcement agencies, news outlets, civil rights organizations, investigative journalism, and academic research. Stories are automatically filtered for relevance to police use of deadly force.

## Feed includes:

* **Incidents**: Reports of police-involved shootings
* **Investigations**: Department reviews, external investigations, and federal inquiries
* **Accountability**: Disciplinary actions, policy changes, and reforms
* **Legal proceedings**: Criminal charges, civil lawsuits, and court rulings
* **Research & analysis**: Academic studies and data-driven reporting
* **Community impact**: Public response and advocacy efforts

**Subscribe**: [RSS Feed](/data/police-shooting-news.xml)

{{% alert note %}}
Looking for the latest academic research on police shootings? Check out my [research tracker](https://jnix.netlify.app/police-shooting-research/).
{{% /alert %}}

---

<link rel="stylesheet" href="/css/news-feed.css">

<div id="news-feed" class="news-feed-container">
  <div class="news-loading">
    <p>Loading latest stories...</p>
  </div>
</div>

<script src="/js/news-feed.js"></script>
<script>
// Police Shooting News Feed Configuration
(function() {
  var CATEGORY_LABELS = {
    incident: 'Incident',
    investigation: 'Investigation',
    accountability: 'Accountability',
    legal: 'Legal Proceedings',
    research: 'Research'
  };

  function renderNewsCard(story, isFeatured) {
    var sourceInitial = (story.source || 'N')[0].toUpperCase();
    var category = story.category || 'incident';
    var categoryLabel = CATEGORY_LABELS[category] || capitalize(category);

    return '<article class="news-card" role="listitem" tabindex="0">' +
      '<div class="card-header">' +
        '<div class="card-source">' +
          '<span class="source-icon" aria-hidden="true">' + escapeHtml(sourceInitial) + '</span>' +
          '<span>' + escapeHtml(story.source || 'News Source') + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="card-body">' +
        '<h3 class="card-title">' + escapeHtml(story.title) + '</h3>' +
      '</div>' +
      '<div class="card-footer">' +
        '<span class="card-date">' + formatDate(story.date) + '</span>' +
        '<span class="mention-type-badge mention-type-' + escapeHtml(category) + '">' + escapeHtml(categoryLabel) + '</span>' +
        '<a href="' + escapeHtml(story.url) + '" target="_blank" rel="noopener">Read Full Article →</a>' +
      '</div>' +
    '</article>';
  }

  function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
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
    if (diffDays < 7) return (diffDays - 1) + ' days ago';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  new NewsFeed({
    containerId: 'news-feed',
    jsonPath: '/data/police-shooting-news.json',
    cardsPerPage: 12,
    filterField: 'category',
    filterTypes: ['incident', 'investigation', 'accountability', 'legal', 'research'],
    dateField: 'date',
    renderCard: renderNewsCard,
    hasFeatured: false
  });
})();
</script>
