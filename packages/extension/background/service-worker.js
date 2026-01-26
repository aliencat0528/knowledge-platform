/**
 * Knowledge Collector Background Service Worker
 * Handles background tasks and message passing
 */

// Configuration
const CONFIG = {
  serverUrl: 'http://localhost:8000',
  healthEndpoint: '/api/v1/health',
  articlesEndpoint: '/api/v1/articles',
};

/**
 * Handle extension installation
 */
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Knowledge Collector installed:', details.reason);

  if (details.reason === 'install') {
    // First install
    console.log('Welcome to Knowledge Collector!');
  } else if (details.reason === 'update') {
    // Extension updated
    console.log('Knowledge Collector updated to version:', chrome.runtime.getManifest().version);
  }
});

/**
 * Handle messages from popup or content scripts
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Handle async responses
  const handleMessage = async () => {
    try {
      switch (message.action) {
        case 'checkHealth':
          return await checkServerHealth();

        case 'saveArticle':
          return await saveArticle(message.data);

        case 'saveArticleBatch':
          return await saveArticleBatch(message.data);

        case 'saveArticleTree':
          return await saveArticleTree(message.data);

        default:
          return { success: false, error: 'Unknown action' };
      }
    } catch (error) {
      console.error('Message handler error:', error);
      return { success: false, error: error.message };
    }
  };

  // Return true to indicate async response
  handleMessage().then(sendResponse);
  return true;
});

/**
 * Check server health
 * @returns {Promise<object>}
 */
async function checkServerHealth() {
  try {
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.healthEndpoint}`);

    if (!response.ok) {
      throw new Error('Server unhealthy');
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Save a single article
 * @param {object} article
 * @returns {Promise<object>}
 */
async function saveArticle(article) {
  try {
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.articlesEndpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(article),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Save failed');
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Save multiple articles in batch
 * @param {object[]} articles
 * @returns {Promise<object>}
 */
async function saveArticleBatch(articles) {
  try {
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.articlesEndpoint}/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ articles }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Batch save failed');
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Save article tree (Notion hierarchy)
 * @param {object} tree
 * @returns {Promise<object>}
 */
async function saveArticleTree(tree) {
  try {
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.articlesEndpoint}/tree`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root: tree }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Tree save failed');
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Context menu setup (optional feature for quick save)
 */
function setupContextMenu() {
  chrome.contextMenus.create({
    id: 'save-page',
    title: '收藏此頁面到知識庫',
    contexts: ['page'],
  });

  chrome.contextMenus.create({
    id: 'save-selection',
    title: '收藏選取內容',
    contexts: ['selection'],
  });
}

/**
 * Handle context menu clicks
 */
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'save-page') {
    // Open popup or directly save
    chrome.action.openPopup();
  } else if (info.menuItemId === 'save-selection') {
    // Save selected text (future feature)
    console.log('Selection save not yet implemented');
  }
});

// Setup context menu on install
chrome.runtime.onInstalled.addListener(() => {
  setupContextMenu();
});
