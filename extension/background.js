// Background Service Worker for Vibe AI Extension

const API_BASE = 'http://localhost:8888';

// Handle installation
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Vibe AI Extension installed:', details.reason);
  
  // Set default settings
  chrome.storage.local.set({
    apiEndpoint: API_BASE,
    autoSuggest: true,
    providers: ['tmdb', 'youtube', 'paramount']
  });
});

// Handle messages from content scripts or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_RECOMMENDATIONS':
      getRecommendations(message.query)
        .then(sendResponse)
        .catch(err => sendResponse({ error: err.message }));
      return true; // Keep channel open for async response
      
    case 'GET_TRENDING':
      getTrending(message.provider)
        .then(sendResponse)
        .catch(err => sendResponse({ error: err.message }));
      return true;
      
    case 'DETECT_CONTENT':
      // Future: Detect what user is watching and suggest similar
      detectCurrentContent(sender.tab)
        .then(sendResponse)
        .catch(err => sendResponse({ error: err.message }));
      return true;
      
    default:
      sendResponse({ error: 'Unknown message type' });
  }
});

// Get recommendations from API
async function getRecommendations(query) {
  try {
    const response = await fetch(`${API_BASE}/api/streaming/search?q=${encodeURIComponent(query)}&limit=5`);
    if (!response.ok) throw new Error('API request failed');
    return await response.json();
  } catch (error) {
    console.error('Recommendation error:', error);
    throw error;
  }
}

// Get trending content
async function getTrending(provider = null) {
  try {
    const url = provider 
      ? `${API_BASE}/api/streaming/trending?provider=${provider}&limit=10`
      : `${API_BASE}/api/streaming/trending?limit=10`;
    const response = await fetch(url);
    if (!response.ok) throw new Error('API request failed');
    return await response.json();
  } catch (error) {
    console.error('Trending error:', error);
    throw error;
  }
}

// Detect current content on streaming sites
async function detectCurrentContent(tab) {
  // This would analyze the current page to detect what the user is watching
  // and provide related recommendations
  const url = new URL(tab.url);
  const hostname = url.hostname;
  
  let platform = null;
  let contentInfo = null;
  
  if (hostname.includes('netflix.com')) {
    platform = 'netflix';
  } else if (hostname.includes('youtube.com')) {
    platform = 'youtube';
    // Extract video ID from URL
    const videoId = url.searchParams.get('v');
    if (videoId) {
      contentInfo = { type: 'video', id: videoId };
    }
  } else if (hostname.includes('paramountplus.com')) {
    platform = 'paramount';
  } else if (hostname.includes('hulu.com')) {
    platform = 'hulu';
  } else if (hostname.includes('disneyplus.com')) {
    platform = 'disney';
  } else if (hostname.includes('max.com') || hostname.includes('hbomax.com')) {
    platform = 'hbo';
  }
  
  return { platform, contentInfo, url: tab.url };
}

// Context menu for right-click search
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'vibeai-search',
    title: 'Find similar with Vibe AI',
    contexts: ['selection']
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'vibeai-search' && info.selectionText) {
    // Open popup with search query
    chrome.storage.local.set({ pendingSearch: info.selectionText });
    chrome.action.openPopup();
  }
});
