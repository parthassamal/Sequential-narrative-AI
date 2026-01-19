// API Configuration
const API_BASE = 'http://localhost:8888';

// DOM Elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const statusEl = document.getElementById('status');
const loadingEl = document.getElementById('loading');
const resultsContainer = document.getElementById('resultsContainer');
const emptyState = document.getElementById('emptyState');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await checkConnection();
  setupEventListeners();
});

// Check API connection
async function checkConnection() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (response.ok) {
      setStatus('connected', 'Connected');
    } else {
      setStatus('error', 'API Error');
    }
  } catch (error) {
    setStatus('error', 'Offline');
    console.error('Connection error:', error);
  }
}

// Set status indicator
function setStatus(state, text) {
  statusEl.className = `status ${state}`;
  statusEl.querySelector('.status-text').textContent = text;
}

// Setup event listeners
function setupEventListeners() {
  // Search button
  searchBtn.addEventListener('click', () => performSearch());
  
  // Enter key
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
  
  // Quick prompts
  document.querySelectorAll('.prompt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.dataset.query;
      searchInput.value = query;
      performSearch();
    });
  });
}

// Perform search
async function performSearch() {
  const query = searchInput.value.trim();
  if (!query) return;
  
  showLoading(true);
  hideEmptyState();
  
  try {
    const response = await fetch(`${API_BASE}/api/streaming/search?q=${encodeURIComponent(query)}&limit=8`);
    const data = await response.json();
    
    if (data.results && data.results.length > 0) {
      displayResults(data.results);
    } else {
      showEmptyResults();
    }
  } catch (error) {
    console.error('Search error:', error);
    showError('Failed to fetch results. Is the backend running?');
  } finally {
    showLoading(false);
  }
}

// Display results
function displayResults(results) {
  resultsContainer.innerHTML = '';
  
  results.forEach(item => {
    const card = createResultCard(item);
    resultsContainer.appendChild(card);
  });
}

// Create result card
function createResultCard(item) {
  const card = document.createElement('div');
  card.className = 'result-card';
  
  const posterUrl = item.poster_url || 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 90"><rect fill="%2316213e" width="60" height="90"/><text x="30" y="50" text-anchor="middle" fill="%23666" font-size="10">No Image</text></svg>';
  
  const provider = item.provider || 'unknown';
  const rating = item.rating ? `⭐ ${item.rating.toFixed(1)}` : '';
  const year = item.year || '';
  const type = item.type || '';
  
  card.innerHTML = `
    <img class="result-poster" src="${posterUrl}" alt="${item.title}" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 60 90%22><rect fill=%22%2316213e%22 width=%2260%22 height=%2290%22/></svg>'">
    <div class="result-info">
      <div class="result-title">${escapeHtml(item.title)}</div>
      <div class="result-meta">
        <span class="result-provider ${provider}">${provider.toUpperCase()}</span>
        ${year ? `<span>${year}</span>` : ''}
        ${type ? `<span>${type}</span>` : ''}
      </div>
      <div class="result-description">${escapeHtml(item.description || 'No description available.')}</div>
      ${rating ? `<div class="result-rating">${rating}</div>` : ''}
    </div>
  `;
  
  // Click to open
  card.addEventListener('click', () => {
    const url = item.watch_url || item.streaming_url || getDefaultUrl(item);
    if (url) {
      chrome.tabs.create({ url });
    }
  });
  
  return card;
}

// Get default URL based on provider
function getDefaultUrl(item) {
  switch (item.provider) {
    case 'tmdb':
      const mediaType = item.type === 'movie' ? 'movie' : 'tv';
      const tmdbId = item.external_id || item.id.replace('tmdb_movie_', '').replace('tmdb_tv_', '');
      return `https://www.themoviedb.org/${mediaType}/${tmdbId}`;
    case 'youtube':
      const videoId = item.external_id || item.id.replace('youtube_', '');
      return `https://www.youtube.com/watch?v=${videoId}`;
    case 'paramount':
      return 'https://www.paramountplus.com';
    default:
      return null;
  }
}

// Show/hide loading
function showLoading(show) {
  loadingEl.classList.toggle('active', show);
  if (show) {
    resultsContainer.innerHTML = '';
  }
}

// Hide empty state
function hideEmptyState() {
  emptyState.classList.add('hidden');
}

// Show empty results
function showEmptyResults() {
  resultsContainer.innerHTML = `
    <div class="empty-state">
      <span class="empty-icon">🔍</span>
      <p>No results found</p>
      <small>Try a different search term</small>
    </div>
  `;
}

// Show error
function showError(message) {
  resultsContainer.innerHTML = `
    <div class="empty-state">
      <span class="empty-icon">⚠️</span>
      <p>${escapeHtml(message)}</p>
      <small>Check if backend is running at localhost:8888</small>
    </div>
  `;
}

// Escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
