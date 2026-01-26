/**
 * Knowledge Collector Popup
 * Main popup UI logic
 */

import { detectNotionPage } from '../utils/notion-detector.js';

// Configuration
const CONFIG = {
  serverUrl: 'http://localhost:8000',
  healthEndpoint: '/api/v1/health',
  articlesEndpoint: '/api/v1/articles',
};

// DOM Elements
const elements = {
  pageTitle: null,
  pageUrl: null,
  notionBadge: null,
  tagsInput: null,
  saveBtn: null,
  saveWithChildrenBtn: null,
  status: null,
  statusIcon: null,
  statusMessage: null,
  progress: null,
  progressFill: null,
  progressText: null,
  serverDot: null,
  serverStatus: null,
};

// Current page state
let currentPage = {
  url: '',
  title: '',
  isNotion: false,
  notionPageId: null,
};

/**
 * Initialize popup
 */
async function init() {
  // Get DOM elements
  initElements();

  // Get current tab info
  await loadCurrentTab();

  // Check server status
  await checkServerStatus();

  // Setup event listeners
  setupEventListeners();
}

/**
 * Initialize DOM element references
 */
function initElements() {
  elements.pageTitle = document.getElementById('pageTitle');
  elements.pageUrl = document.getElementById('pageUrl');
  elements.notionBadge = document.getElementById('notionBadge');
  elements.tagsInput = document.getElementById('tagsInput');
  elements.saveBtn = document.getElementById('saveBtn');
  elements.saveWithChildrenBtn = document.getElementById('saveWithChildrenBtn');
  elements.status = document.getElementById('status');
  elements.statusIcon = document.getElementById('statusIcon');
  elements.statusMessage = document.getElementById('statusMessage');
  elements.progress = document.getElementById('progress');
  elements.progressFill = document.getElementById('progressFill');
  elements.progressText = document.getElementById('progressText');
  elements.serverDot = document.getElementById('serverDot');
  elements.serverStatus = document.getElementById('serverStatus');
}

/**
 * Load current tab information
 */
async function loadCurrentTab() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      showStatus('error', '無法取得當前頁面資訊');
      return;
    }

    // Detect if Notion page
    const detection = detectNotionPage(tab);

    currentPage = {
      url: tab.url,
      title: detection.title || tab.title,
      isNotion: detection.isNotion,
      notionPageId: detection.formattedId,
    };

    // Update UI
    elements.pageTitle.textContent = currentPage.title || '(無標題)';
    elements.pageUrl.textContent = currentPage.url;

    // Show Notion badge if detected
    if (currentPage.isNotion) {
      elements.notionBadge.style.display = 'inline-flex';
      elements.saveWithChildrenBtn.style.display = 'block';
    }
  } catch (error) {
    console.error('Failed to load tab info:', error);
    showStatus('error', '載入頁面資訊失敗');
  }
}

/**
 * Check server health status
 */
async function checkServerStatus() {
  try {
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.healthEndpoint}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (response.ok) {
      elements.serverDot.classList.add('online');
      elements.serverDot.classList.remove('offline');
      elements.serverStatus.textContent = '伺服器連線中';
      elements.saveBtn.disabled = false;
      elements.saveWithChildrenBtn.disabled = false;
    } else {
      throw new Error('Server unhealthy');
    }
  } catch (error) {
    elements.serverDot.classList.add('offline');
    elements.serverDot.classList.remove('online');
    elements.serverStatus.textContent = '伺服器離線';
    elements.saveBtn.disabled = true;
    elements.saveWithChildrenBtn.disabled = true;
  }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  elements.saveBtn.addEventListener('click', () => savePage(false));
  elements.saveWithChildrenBtn.addEventListener('click', () => savePage(true));

  // Enter key in tags input triggers save
  elements.tagsInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      savePage(false);
    }
  });
}

/**
 * Save current page
 * @param {boolean} withChildren - Include sub-pages (Notion only)
 */
async function savePage(withChildren = false) {
  // Disable buttons during save
  elements.saveBtn.disabled = true;
  elements.saveWithChildrenBtn.disabled = true;

  showStatus('loading', '正在擷取內容...');

  try {
    // Get tags
    const tags = parseTags(elements.tagsInput.value);

    // Extract content from page via content script
    const content = await extractPageContent();

    if (!content) {
      throw new Error('無法擷取頁面內容');
    }

    showStatus('loading', '正在儲存...');

    // Determine source type
    const sourceType = currentPage.isNotion ? 'notion' : 'web';

    // Build article payload
    const article = {
      source_type: sourceType,
      source_id: currentPage.isNotion
        ? currentPage.notionPageId
        : generateSourceId(currentPage.url),
      title: currentPage.title,
      content: content.markdown || content.text,
      url: currentPage.url,
      tags: tags,
      notion_page_id: currentPage.notionPageId || null,
    };

    // Save to server
    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.articlesEndpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(article),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || '儲存失敗');
    }

    const result = await response.json();

    // Show success with status
    const status = result.results?.[0]?.status || 'new';
    const statusMessages = {
      new: '✨ 新文章已收藏！',
      updated: '🔄 文章已更新！',
      skipped: '⏭️ 文章內容相同，已跳過',
    };

    showStatus('success', statusMessages[status] || '儲存成功！');
  } catch (error) {
    console.error('Save failed:', error);
    showStatus('error', error.message || '儲存失敗');
  } finally {
    // Re-enable buttons
    elements.saveBtn.disabled = false;
    elements.saveWithChildrenBtn.disabled = false;
  }
}

/**
 * Extract page content via content script
 * @returns {Promise<object|null>}
 */
async function extractPageContent() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Send message to content script
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'extractContent',
    });

    return response;
  } catch (error) {
    console.error('Content extraction failed:', error);

    // Fallback: try to inject and extract
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
          return {
            text: document.body.innerText,
            html: document.body.innerHTML,
          };
        },
      });

      return results[0]?.result || null;
    } catch (fallbackError) {
      console.error('Fallback extraction failed:', fallbackError);
      return null;
    }
  }
}

/**
 * Parse tags from comma-separated string
 * @param {string} input
 * @returns {string[]}
 */
function parseTags(input) {
  if (!input) return [];

  return input
    .split(/[,，]/) // Support both English and Chinese comma
    .map(tag => tag.trim())
    .filter(tag => tag.length > 0);
}

/**
 * Generate source ID from URL
 * @param {string} url
 * @returns {string}
 */
function generateSourceId(url) {
  // Use URL hash as source ID for non-Notion pages
  const encoder = new TextEncoder();
  const data = encoder.encode(url);

  // Simple hash (for deduplication)
  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    const char = data[i];
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }

  return `web-${Math.abs(hash).toString(16)}`;
}

/**
 * Show status message
 * @param {'success'|'error'|'loading'} type
 * @param {string} message
 */
function showStatus(type, message) {
  elements.status.style.display = 'flex';
  elements.status.className = `status ${type}`;

  const icons = {
    success: '✅',
    error: '❌',
    loading: '⏳',
  };

  elements.statusIcon.textContent = icons[type] || '';
  elements.statusMessage.textContent = message;

  // Auto-hide success after 3s
  if (type === 'success') {
    setTimeout(() => {
      elements.status.style.display = 'none';
    }, 3000);
  }
}

/**
 * Update progress bar
 * @param {number} current
 * @param {number} total
 */
function updateProgress(current, total) {
  const percentage = total > 0 ? (current / total) * 100 : 0;
  elements.progress.style.display = 'block';
  elements.progressFill.style.width = `${percentage}%`;
  elements.progressText.textContent = `${current}/${total}`;
}

/**
 * Hide progress bar
 */
function hideProgress() {
  elements.progress.style.display = 'none';
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
