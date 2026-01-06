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

---

<div id="news-feed">
  <div style="text-align: center; padding: 40px;">
    <div class="spinner" style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
    <p style="margin-top: 20px; color: #666;">Loading latest stories...</p>
  </div>
</div>

<style>
/* Minimal custom styles - inherits from Hugo Academic theme */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.news-item {
  background: var(--article-bg-color, #f8f9fa);
  border-left: 4px solid #4caf50;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border-radius: 3px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.news-item h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1.3rem;
  line-height: 1.4;
}

.news-item h3 a {
  text-decoration: none;
  color: inherit;
}

.news-item h3 a:hover {
  color: #4caf50;
  text-decoration: underline;
}

.news-meta {
  font-size: 0.9rem;
  color: var(--text-muted, #6c757d);
  margin-bottom: 0.75rem;
}

.news-description {
  line-height: 1.6;
  margin-bottom: 0.75rem;
}

.news-category {
  display: inline-block;
  background: #4caf50;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 3px;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.filter-buttons {
  margin: 2rem 0;
  text-align: center;
}

.filter-btn {
  background: var(--btn-default-bg, #e9ecef);
  border: 1px solid var(--btn-default-border, #dee2e6);
  color: var(--btn-default-color, #495057);
  padding: 0.5rem 1rem;
  margin: 0.25rem;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.9rem;
}

.filter-btn:hover {
  background: #e8f5e9;
  border-color: #4caf50;
}

.filter-btn.active {
  background: #4caf50;
  color: white;
  border-color: #4caf50;
}
</style>

<script>
// RSS Feed URL
const RSS_FEED_URL = '/data/police-shooting-news.xml';

// Filter buttons HTML
const filters = `
  <div class="filter-buttons">
    <button class="filter-btn active" onclick="filterNews('all')">All Stories</button>
    <button class="filter-btn" onclick="filterNews('incident')">Incidents</button>
    <button class="filter-btn" onclick="filterNews('investigation')">Investigations</button>
    <button class="filter-btn" onclick="filterNews('accountability')">Accountability</button>
    <button class="filter-btn" onclick="filterNews('legal')">Legal Proceedings</button>
    <button class="filter-btn" onclick="filterNews('research')">Research</button>
  </div>
`;

let allNews = [];
let currentFilter = 'all';

async function loadNews() {
  try {
    const response = await fetch(RSS_FEED_URL);
    
    // Check if the file actually exists
    if (!response.ok) {
      console.log('RSS feed not found yet, showing sample data');
      displaySampleNews();
      return;
    }
    
    const text = await response.text();
    const parser = new DOMParser();
    const xml = parser.parseFromString(text, 'text/xml');
    
    const items = xml.querySelectorAll('item');
    
    // If no items found, show sample data
    if (items.length === 0) {
      console.log('RSS feed is empty, showing sample data');
      displaySampleNews();
      return;
    }
    
    allNews = Array.from(items).map(item => ({
      title: item.querySelector('title')?.textContent || '',
      link: item.querySelector('link')?.textContent || '',
      description: item.querySelector('description')?.textContent || '',
      pubDate: item.querySelector('pubDate')?.textContent || '',
      category: item.querySelector('category')?.textContent || 'general',
      source: item.querySelector('source')?.textContent || 'News Source'
    }));
    
    displayNews(allNews);
  } catch (error) {
    console.error('Error loading news feed:', error);
    displaySampleNews();
  }
}

function displaySampleNews() {
  // Sample data for demonstration purposes
  allNews = [
    {
      title: "Federal Investigation Opened Into Department Use-of-Force Practices",
      link: "#",
      description: "The Department of Justice has initiated a pattern-or-practice investigation following multiple incidents of officer-involved shootings over the past 18 months. Investigators will examine training protocols, supervision, and accountability systems.",
      pubDate: new Date(Date.now() - 86400000).toDateString(),
      category: "investigation",
      source: "DOJ Press Release"
    },
    {
      title: "Body Camera Footage Released in Fatal Officer-Involved Shooting",
      link: "#",
      description: "Police department releases video evidence following public records request. The footage shows the moments leading up to and during the confrontation. Community groups have called for independent review of the incident.",
      pubDate: new Date(Date.now() - 2 * 86400000).toDateString(),
      category: "incident",
      source: "Local News"
    },
    {
      title: "City Council Adopts Comprehensive Police Reform Package",
      link: "#",
      description: "New policies include mandatory de-escalation training, revised use-of-force continuum, enhanced accountability measures, and increased transparency requirements for critical incidents.",
      pubDate: new Date(Date.now() - 3 * 86400000).toDateString(),
      category: "accountability",
      source: "Municipal Government"
    },
    {
      title: "Federal Jury Awards Damages in Police Shooting Civil Rights Case",
      link: "#",
      description: "After a two-week trial, jurors found that officers violated the Fourth Amendment when they used deadly force. The verdict may influence similar pending cases around the country.",
      pubDate: new Date(Date.now() - 4 * 86400000).toDateString(),
      category: "legal",
      source: "Federal Court"
    },
    {
      title: "New Study Documents Racial Disparities in Police Use of Deadly Force",
      link: "#",
      description: "Researchers analyzed five years of data from 50 major cities, finding significant disparities in fatal police shootings. The study recommends specific policy interventions and enhanced data collection.",
      pubDate: new Date(Date.now() - 5 * 86400000).toDateString(),
      category: "research",
      source: "Academic Journal"
    },
    {
      title: "Officer Criminally Charged Following Review of Shooting Incident",
      link: "#",
      description: "State prosecutors have filed criminal charges after reviewing evidence and witness statements. This marks a significant development in the ongoing accountability debate surrounding police use of force.",
      pubDate: new Date(Date.now() - 6 * 86400000).toDateString(),
      category: "legal",
      source: "District Attorney"
    }
  ];
  
  displayNews(allNews);
}

function displayNews(newsArray) {
  const container = document.getElementById('news-feed');
  
  if (newsArray.length === 0) {
    container.innerHTML = filters + '<p style="text-align: center; padding: 40px; color: #666;">No stories found matching your criteria.</p>';
    return;
  }
  
  const newsHTML = newsArray.map(item => `
    <div class="news-item">
      <h3><a href="${item.link}" target="_blank" rel="noopener">${item.title}</a></h3>
      <div class="news-meta">
        <strong>${item.source}</strong> • ${formatDate(item.pubDate)}
      </div>
      <div class="news-description">${item.description}</div>
      <span class="news-category">${capitalize(item.category)}</span>
    </div>
  `).join('');
  
  container.innerHTML = filters + newsHTML;
}

function filterNews(category) {
  currentFilter = category;
  
  // Update button states
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.textContent.toLowerCase().includes(category) || (category === 'all' && btn.textContent === 'All Stories')) {
      btn.classList.add('active');
    }
  });
  
  // Filter news
  if (category === 'all') {
    displayNews(allNews);
  } else {
    const filtered = allNews.filter(item => item.category === category);
    displayNews(filtered);
  }
}

function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now - date);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 1) return 'Today';
  if (diffDays === 2) return 'Yesterday';
  if (diffDays < 7) return `${diffDays - 1} days ago`;
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadNews);
} else {
  loadNews();
}
</script>