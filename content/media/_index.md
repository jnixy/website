---
title: "In the Media"
summary: "Media coverage and interviews pertaining to my research"
date: 2026-01-07
type: page
reading_time: false
share: false
profile: false
comments: false
---

This page automatically tracks media coverage, interviews, and mentions of my research.

**Subscribe:** [RSS Feed](/data/media-mentions.xml). Feed began active tracking on January 7, 2026.

---

<link rel="stylesheet" href="/css/news-feed.css">

<div id="media-feed" class="news-feed-container">
  <div class="news-loading">
    <p>Loading media coverage...</p>
  </div>
</div>

<style>
/* News Feed Container */
.news-feed-container {
  margin-top: 2rem;
}

.news-loading {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted, #666);
}

/* Controls Bar */
.news-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: var(--article-bg-color, #f8f9fa);
  border-radius: 8px;
  flex-wrap: wrap;
  gap: 1rem;
}

.news-stats {
  font-size: 0.95rem;
  color: var(--text-muted, #666);
  font-weight: 500;
}

.news-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.4rem 0.8rem;
  border: 1px solid #DC143C;
  background: white;
  color: #DC143C;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
  font-weight: 500;
}

.filter-btn:hover {
  background: #DC143C;
  color: white;
}

.filter-btn.active {
  background: #DC143C;
  color: white;
  border-color: #DC143C;
}

/* Featured Section */
.featured-section {
  margin-bottom: 2rem;
}

.featured-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #DC143C;
}

.featured-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--heading-color, #1a1a1a);
}

.featured-icon {
  color: #DC143C;
  font-size: 1.2rem;
}

/* Card Grid Layout */
.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

@media (min-width: 1200px) {
  .news-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 767px) {
  .news-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}

/* Individual Card Styling */
.news-card {
  display: flex;
  flex-direction: column;
  background: var(--article-bg-color, white);
  border: 1px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  text-decoration: none;
  color: inherit;
  min-height: 180px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.news-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: #DC143C;
}

.news-card.featured {
  border: 2px solid #DC143C;
  box-shadow: 0 2px 8px rgba(220, 20, 60, 0.2);
}

.news-card.featured:hover {
  box-shadow: 0 8px 24px rgba(220, 20, 60, 0.3);
}

.news-card:focus {
  outline: 2px solid #DC143C;
  outline-offset: 2px;
}

/* Card Header - Source */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--card-header-bg, #fafafa);
  border-bottom: 1px solid var(--border-color, #eee);
  font-size: 0.8rem;
  color: var(--text-muted, #666);
}

.card-source {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 600;
  font-size: 0.75rem;
  color: #DC143C;
}

.source-icon {
  width: 16px;
  height: 16px;
  border-radius: 2px;
  background: #DC143C;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: white;
  flex-shrink: 0;
  font-weight: bold;
}

/* Featured Badge */
.featured-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.4rem;
  background: #fff0f5;
  border: 1px solid #DC143C;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 600;
  color: #DC143C;
  text-transform: uppercase;
}

/* Card Body */
.card-body {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.4;
  margin: 0 0 0.75rem 0;
  color: var(--heading-color, #1a1a1a);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* HIDE SUMMARY - DO NOT DISPLAY */
.card-summary {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Topic Tags */
.card-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: auto;
}

.topic-tag {
  display: inline-block;
  padding: 0.15rem 0.4rem;
  background: #fce4ec;
  color: #DC143C;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 500;
}

/* Card Footer */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border-color, #eee);
  font-size: 0.8rem;
  color: var(--text-muted, #666);
  gap: 0.75rem;
  flex-wrap: wrap;
}

.card-date {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
  font-size: 0.75rem;
}

.card-date::before {
  content: "";
  display: inline-block;
  width: 12px;
  height: 12px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23666'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'/%3E%3C/svg%3E");
  background-size: contain;
  opacity: 0.7;
}

/* "Read More" Link */
.card-footer a {
  color: #DC143C !important;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.2s;
  white-space: nowrap;
}

.card-footer a:hover {
  color: white !important;
  background: #DC143C !important;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
}

/* Mention Type Badges */
.mention-type-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.mention-type-badge + .mention-type-badge {
  margin-left: 0.25rem;
}

.mention-type-quoted { 
  background: #e8f5e9; 
  color: #2e7d32; 
}

.mention-type-cited { 
  background: #e3f2fd; 
  color: #1565c0; 
}

.mention-type-referenced { 
  background: #f3e5f5; 
  color: #7b1fa2; 
}

.mention-type-byline { 
  background: #fff3e0; 
  color: #ef6c00; 
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
  margin-top: 2rem;
  padding: 1rem;
  flex-wrap: wrap;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #DC143C;
  background: white;
  color: #DC143C;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}

.pagination-btn:hover:not(:disabled) {
  background: #DC143C;
  color: white;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: #ccc;
  color: #ccc;
}

.pagination-btn.active {
  background: #DC143C;
  color: white;
  border-color: #DC143C;
}

.pagination-info {
  font-size: 0.9rem;
  color: var(--text-muted, #666);
  margin: 0 1rem;
}

/* No Stories Message */
.no-stories {
  text-align: center;
  padding: 3rem;
  color: var(--text-muted, #999);
  font-size: 1.1rem;
  grid-column: 1 / -1;
}

/* Responsive adjustments */
@media (max-width: 480px) {
  .news-controls {
    flex-direction: column;
    align-items: flex-start;
  }

  .pagination {
    gap: 0.25rem;
  }

  .pagination-btn {
    padding: 0.4rem 0.6rem;
    min-width: 40px;
    min-height: 40px;
    font-size: 0.8rem;
  }
}
</style>

<script src="/js/news-feed.js"></script>
<script>
// Media Mentions Feed Configuration
(function() {
  function renderMediaCard(story, isFeatured) {
    // Handle mention_type as either string or array
    var mentionTypes = story.mention_type;
    if (typeof mentionTypes === 'string') {
      mentionTypes = [mentionTypes];
    } else if (!Array.isArray(mentionTypes)) {
      mentionTypes = ['referenced'];
    }

    var sourceInitial = (story.source || 'N')[0].toUpperCase();

    // Build topics HTML
    var topicsHTML = '';
    if (story.topics && story.topics.length > 0) {
      topicsHTML = '<div class="card-topics">';
      var topics = Array.isArray(story.topics) ? story.topics : [story.topics];
      topics.slice(0, 4).forEach(function(topic) {
        topicsHTML += '<span class="topic-tag">' + escapeHtml(topic) + '</span>';
      });
      topicsHTML += '</div>';
    }

    // Build mention type badges HTML (handles multiple types)
    var badgesHTML = '';
    mentionTypes.forEach(function(type) {
      badgesHTML += '<span class="mention-type-badge mention-type-' + escapeHtml(type) + '">' + capitalize(type) + '</span>';
    });

    var cardClass = 'news-card' + (isFeatured ? ' featured' : '');

    var html = '<article class="' + cardClass + '" role="listitem" tabindex="0">' +
      '<div class="card-header">' +
      '<div class="card-source">' +
      '<span class="source-icon" aria-hidden="true">' + sourceInitial + '</span>' +
      '<span>' + escapeHtml(story.source || 'Unknown') + '</span>' +
      '</div>';

    if (isFeatured) {
      html += '<span class="featured-badge">&#9733; Featured</span>';
    }

    html += '</div>' +
      '<div class="card-body">' +
      '<h3 class="card-title">' + escapeHtml(story.title) + '</h3>' +
      topicsHTML +
      '</div>' +
      '<div class="card-footer">' +
      '<span class="card-date">' + formatDate(story.date || story.date_discovered) + '</span>' +
      badgesHTML +
      '<a href="' + escapeHtml(story.url) + '" target="_blank" rel="noopener">Read Full Article →</a>' +
      '</div>' +
      '</article>';

    return html;
  }

  // Helper functions
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

    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  // Initialize the feed
  new NewsFeed({
    containerId: 'media-feed',
    jsonPath: '/data/media-mentions.json',
    cardsPerPage: 12,
    filterField: 'mention_type',
    filterTypes: ['quoted', 'cited', 'referenced', 'byline'],
    dateField: 'date',
    prefix: 'media',
    renderCard: renderMediaCard,
    hasFeatured: true
  });
})();
</script>