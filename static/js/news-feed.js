/**
 * News Feed JavaScript Component
 * Version: 2.0.0 - January 2025 Update
 * - Removed card summaries
 * - Added topic tags, mention badges, article links
 * - Crimson Red (#DC143C) theme
 */

class NewsFeed {
  constructor(config) {
    this.config = config;
    this.allStories = [];
    this.filteredStories = [];
    this.currentPage = 1;
    this.cardsPerPage = config.cardsPerPage || 12;
    this.filterField = config.filterField || 'mention_type';
    this.filterTypes = config.filterTypes || [];
    this.dateField = config.dateField || 'date';
    this.renderCard = config.renderCard || this.defaultRenderCard.bind(this);
    this.hasFeatured = config.hasFeatured !== false;
    
    // Log version to console for debugging
    console.log('NewsFeed v2.0.0 loaded');
    
    this.init();
  }

  async init() {
    try {
      const response = await fetch(this.config.jsonPath);
      if (!response.ok) {
        throw new Error(`Failed to load ${this.config.jsonPath}: ${response.statusText}`);
      }
      
      const data = await response.json();
      this.allStories = data.stories || [];
      
      if (this.allStories.length === 0) {
        this.showNoStories();
        return;
      }
      
      // Sort by date (newest first)
      this.allStories.sort((a, b) => {
        const dateA = new Date(a[this.dateField]);
        const dateB = new Date(b[this.dateField]);
        return dateB - dateA;
      });
      
      this.filteredStories = [...this.allStories];
      this.render();
      
    } catch (error) {
      console.error('Error loading news feed:', error);
      this.showError(error.message);
    }
  }

  render() {
    const container = document.getElementById(this.config.containerId);
    if (!container) {
      console.error(`Container ${this.config.containerId} not found`);
      return;
    }

    const featured = this.filteredStories.filter(s => s.featured);
    const regular = this.filteredStories.filter(s => !s.featured);

    let html = '';

    // Featured section
    if (this.hasFeatured && featured.length > 0) {
      html += '<div class="featured-section">';
      html += '<div class="featured-header">';
      html += '<span class="featured-icon">★</span>';
      html += '<h3>Featured Coverage</h3>';
      html += '</div>';
      html += '<div class="news-grid">';
      featured.forEach(story => {
        html += this.renderCard(story, true);
      });
      html += '</div>';
      html += '</div>';
    }

    // Stats and filters bar
    html += '<div class="news-controls">';
    html += `<div class="news-stats">${this.filteredStories.length} stories found</div>`;
    
    if (this.filterTypes.length > 0) {
      html += '<div class="news-filters">';
      html += '<button class="filter-btn active" data-filter="all">All</button>';
      this.filterTypes.forEach(type => {
        html += `<button class="filter-btn" data-filter="${type}">${this.capitalize(type)}</button>`;
      });
      html += '</div>';
    }
    html += '</div>';

    // Regular stories grid with pagination
    const startIdx = (this.currentPage - 1) * this.cardsPerPage;
    const endIdx = startIdx + this.cardsPerPage;
    const paginated = regular.slice(startIdx, endIdx);

    html += '<div class="news-grid" role="list">';
    if (paginated.length > 0) {
      paginated.forEach(story => {
        html += this.renderCard(story, false);
      });
    } else if (regular.length === 0 && featured.length === 0) {
      html += '<div class="no-stories">No stories found</div>';
    }
    html += '</div>';

    // Pagination
    const totalPages = Math.ceil(regular.length / this.cardsPerPage);
    if (totalPages > 1) {
      html += this.renderPagination(totalPages);
    }

    container.innerHTML = html;
    this.attachEventListeners();
  }

  renderPagination(totalPages) {
    let html = '<div class="pagination">';
    
    html += `<button class="pagination-btn pagination-prev" ${this.currentPage === 1 ? 'disabled' : ''}>← Previous</button>`;

    for (let i = 1; i <= Math.min(totalPages, 7); i++) {
      const activeClass = i === this.currentPage ? ' active' : '';
      html += `<button class="pagination-btn pagination-page${activeClass}" data-page="${i}">${i}</button>`;
    }

    if (totalPages > 7) {
      html += '<span class="pagination-info">...</span>';
      html += `<button class="pagination-btn pagination-page" data-page="${totalPages}">${totalPages}</button>`;
    }

    html += `<span class="pagination-info">Page ${this.currentPage} of ${totalPages}</span>`;
    html += `<button class="pagination-btn pagination-next" ${this.currentPage === totalPages ? 'disabled' : ''}>Next →</button>`;

    html += '</div>';
    return html;
  }

  attachEventListeners() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const filter = e.target.getAttribute('data-filter');
        this.applyFilter(filter, e.target);
      });
    });

    // Pagination buttons
    const prevBtn = document.querySelector('.pagination-prev');
    if (prevBtn) {
      prevBtn.addEventListener('click', () => this.previousPage());
    }

    const nextBtn = document.querySelector('.pagination-next');
    if (nextBtn) {
      nextBtn.addEventListener('click', () => this.nextPage());
    }

    document.querySelectorAll('.pagination-page').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const pageNum = parseInt(e.target.getAttribute('data-page'));
        this.goToPage(pageNum);
      });
    });
  }

  applyFilter(filterValue, clickedBtn) {
    if (filterValue === 'all') {
      this.filteredStories = [...this.allStories];
    } else {
      this.filteredStories = this.allStories.filter(story => {
        return story[this.filterField] === filterValue;
      });
    }

    this.currentPage = 1;
    this.render();

    // Update active state after re-render
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.classList.remove('active');
      if (btn.getAttribute('data-filter') === filterValue) {
        btn.classList.add('active');
      }
    });
  }

  goToPage(pageNum) {
    this.currentPage = pageNum;
    this.render();
    this.scrollToTop();
  }

  nextPage() {
    const regular = this.filteredStories.filter(s => !s.featured);
    const totalPages = Math.ceil(regular.length / this.cardsPerPage);
    if (this.currentPage < totalPages) {
      this.currentPage++;
      this.render();
      this.scrollToTop();
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.render();
      this.scrollToTop();
    }
  }

  scrollToTop() {
    const container = document.getElementById(this.config.containerId);
    if (container) {
      container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  showNoStories() {
    const container = document.getElementById(this.config.containerId);
    if (container) {
      container.innerHTML = '<div class="no-stories">No media mentions found.</div>';
    }
  }

  showError(message) {
    const container = document.getElementById(this.config.containerId);
    if (container) {
      container.innerHTML = `<div class="no-stories">Error loading media feed: ${message}</div>`;
    }
  }

  capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  formatDate(dateStr) {
    if (!dateStr) return 'Unknown';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }

  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  defaultRenderCard(story, isFeatured = false) {
    const cardClass = isFeatured ? 'news-card featured' : 'news-card';
    
    // Source icon (first letter)
    const sourceInitial = (story.source || 'N')[0].toUpperCase();
    const sourceName = this.escapeHtml(story.source || 'Unknown');
    
    // Title
    const title = this.escapeHtml(story.title || 'Untitled');
    
    // Topic tags (up to 4)
    let topicsHTML = '';
    if (story.topics && story.topics.length > 0) {
      const topics = Array.isArray(story.topics) ? story.topics : [story.topics];
      topicsHTML = '<div class="card-topics">';
      topics.slice(0, 4).forEach(topic => {
        topicsHTML += `<span class="topic-tag">${this.escapeHtml(topic)}</span>`;
      });
      topicsHTML += '</div>';
    }
    
    // Date
    const formattedDate = this.formatDate(story.date);
    
    // Mention type badge
    const mentionType = story.mention_type || 'referenced';
    const mentionBadge = `<span class="mention-type-badge mention-type-${mentionType}">${this.capitalize(mentionType)}</span>`;
    
    // Article URL
    const articleUrl = this.escapeHtml(story.url || '#');

    return `
      <article class="${cardClass}" role="listitem" tabindex="0">
        <div class="card-header">
          <div class="card-source">
            <span class="source-icon">${sourceInitial}</span>
            <span>${sourceName}</span>
          </div>
        </div>
        <div class="card-body">
          <h3 class="card-title">${title}</h3>
          ${topicsHTML}
        </div>
        <div class="card-footer">
          <span class="card-date">${formattedDate}</span>
          ${mentionBadge}
          <a href="${articleUrl}" target="_blank" rel="noopener noreferrer">Read Full Article →</a>
        </div>
      </article>
    `;
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // NewsFeed will be instantiated by inline script in media_index.md
  console.log('NewsFeed script loaded and ready');
});