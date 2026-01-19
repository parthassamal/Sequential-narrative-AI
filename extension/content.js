// Content Script - Injected into streaming sites
// Adds a floating "Vibe AI" button for quick recommendations

(function() {
  'use strict';
  
  // Only inject once
  if (window.vibeAIInjected) return;
  window.vibeAIInjected = true;
  
  // Create floating button
  const floatingBtn = document.createElement('div');
  floatingBtn.id = 'vibe-ai-floating-btn';
  floatingBtn.innerHTML = `
    <div class="vibe-ai-btn">
      <span class="vibe-ai-icon">🎬</span>
      <span class="vibe-ai-text">What else?</span>
    </div>
  `;
  
  // Add to page
  document.body.appendChild(floatingBtn);
  
  // Click handler
  floatingBtn.addEventListener('click', async () => {
    // Get current page info
    const pageInfo = detectPageContent();
    
    // Send to background script
    chrome.runtime.sendMessage({
      type: 'DETECT_CONTENT',
      pageInfo
    }, (response) => {
      if (response && !response.error) {
        showRecommendationPopup(response);
      }
    });
  });
  
  // Detect what's on the current page
  function detectPageContent() {
    const url = window.location.href;
    const title = document.title;
    const hostname = window.location.hostname;
    
    let contentType = 'unknown';
    let contentId = null;
    let contentTitle = null;
    
    // YouTube
    if (hostname.includes('youtube.com')) {
      const videoId = new URLSearchParams(window.location.search).get('v');
      if (videoId) {
        contentType = 'youtube_video';
        contentId = videoId;
        contentTitle = document.querySelector('h1.ytd-video-primary-info-renderer')?.textContent || title;
      }
    }
    
    // Netflix
    else if (hostname.includes('netflix.com')) {
      contentType = 'netflix';
      // Netflix uses complex SPAs, title detection would need more work
      contentTitle = document.querySelector('.title-title')?.textContent || title;
    }
    
    // Paramount+
    else if (hostname.includes('paramountplus.com')) {
      contentType = 'paramount';
      contentTitle = document.querySelector('h1')?.textContent || title;
    }
    
    return { url, title, contentType, contentId, contentTitle, hostname };
  }
  
  // Show mini recommendation popup
  function showRecommendationPopup(data) {
    // Remove existing popup if any
    const existing = document.getElementById('vibe-ai-popup');
    if (existing) existing.remove();
    
    const popup = document.createElement('div');
    popup.id = 'vibe-ai-popup';
    popup.innerHTML = `
      <div class="vibe-ai-popup-header">
        <span>🎬 Vibe AI Suggestions</span>
        <button class="vibe-ai-close">&times;</button>
      </div>
      <div class="vibe-ai-popup-body">
        <p>Based on what you're watching...</p>
        <div class="vibe-ai-loading">Finding recommendations...</div>
      </div>
    `;
    
    document.body.appendChild(popup);
    
    // Close button
    popup.querySelector('.vibe-ai-close').addEventListener('click', () => {
      popup.remove();
    });
    
    // Fetch recommendations based on current content
    const searchQuery = data.contentInfo?.contentTitle || 'popular trending';
    chrome.runtime.sendMessage({
      type: 'GET_RECOMMENDATIONS',
      query: searchQuery
    }, (response) => {
      if (response && response.results) {
        displayPopupResults(popup, response.results.slice(0, 3));
      } else {
        popup.querySelector('.vibe-ai-popup-body').innerHTML = `
          <p>Could not fetch recommendations</p>
          <small>Make sure the Vibe AI backend is running</small>
        `;
      }
    });
  }
  
  // Display results in popup
  function displayPopupResults(popup, results) {
    const body = popup.querySelector('.vibe-ai-popup-body');
    body.innerHTML = '<p style="margin-bottom: 12px;">You might also like:</p>';
    
    results.forEach(item => {
      const card = document.createElement('div');
      card.className = 'vibe-ai-result-card';
      card.innerHTML = `
        <img src="${item.poster_url || ''}" alt="${item.title}" onerror="this.style.display='none'">
        <div class="vibe-ai-result-info">
          <div class="vibe-ai-result-title">${item.title}</div>
          <div class="vibe-ai-result-meta">${item.provider?.toUpperCase()} • ${item.year || ''}</div>
        </div>
      `;
      card.addEventListener('click', () => {
        const url = item.watch_url || item.streaming_url;
        if (url) window.open(url, '_blank');
      });
      body.appendChild(card);
    });
    
    // Add "Open Full App" link
    const openApp = document.createElement('a');
    openApp.href = 'http://localhost:3000';
    openApp.target = '_blank';
    openApp.className = 'vibe-ai-open-app';
    openApp.textContent = 'Open Full App →';
    body.appendChild(openApp);
  }
  
  console.log('Vibe AI content script loaded');
})();
