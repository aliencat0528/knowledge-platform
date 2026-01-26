/**
 * Knowledge Collector Popup
 * Main popup UI logic with Notion tree support
 */

import { detectNotionPage } from '../utils/notion-detector.js';

// Configuration
const CONFIG = {
  serverUrl: 'http://localhost:8000',
  healthEndpoint: '/api/v1/health',
  articlesEndpoint: '/api/v1/articles',
  batchEndpoint: '/api/v1/articles/batch',
  treeEndpoint: '/api/v1/articles/tree',
};

// DOM Elements
const elements = {
  pageTitle: null,
  pageUrl: null,
  notionBadge: null,
  tagsInput: null,
  saveBtn: null,
  saveWithChildrenBtn: null,
  cancelBtn: null,
  status: null,
  statusIcon: null,
  statusMessage: null,
  progress: null,
  progressFill: null,
  progressText: null,
  serverDot: null,
  serverStatus: null,
  // Sub-pages elements
  subpagesSection: null,
  subpagesList: null,
  subpagesCount: null,
  selectAllBtn: null,
  deselectAllBtn: null,
  // Mode elements
  singleMode: null,
  batchMode: null,
  modeTabs: null,
  // Batch mode elements
  batchTagsInput: null,
  tabsList: null,
  tabsCount: null,
  selectAllTabsBtn: null,
  deselectAllTabsBtn: null,
  batchSaveBtn: null,
  batchStatus: null,
  batchStatusIcon: null,
  batchStatusMessage: null,
  batchProgress: null,
  batchProgressFill: null,
  batchProgressText: null,
};

// Current page state
let currentPage = {
  url: '',
  title: '',
  isNotion: false,
  notionPageId: null,
};

// Sub-pages state
let subPages = [];
let isCrawling = false;

// Batch mode state
let currentMode = 'single'; // 'single' or 'batch'
let allTabs = [];
let isBatchSaving = false;

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

  // If Notion page, scan for sub-pages
  if (currentPage.isNotion) {
    await scanForSubPages();
  }
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
  elements.cancelBtn = document.getElementById('cancelBtn');
  elements.status = document.getElementById('status');
  elements.statusIcon = document.getElementById('statusIcon');
  elements.statusMessage = document.getElementById('statusMessage');
  elements.progress = document.getElementById('progress');
  elements.progressFill = document.getElementById('progressFill');
  elements.progressText = document.getElementById('progressText');
  elements.serverDot = document.getElementById('serverDot');
  elements.serverStatus = document.getElementById('serverStatus');
  // Sub-pages elements
  elements.subpagesSection = document.getElementById('subpagesSection');
  elements.subpagesList = document.getElementById('subpagesList');
  elements.subpagesCount = document.getElementById('subpagesCount');
  elements.selectAllBtn = document.getElementById('selectAllBtn');
  elements.deselectAllBtn = document.getElementById('deselectAllBtn');
  // Mode elements
  elements.singleMode = document.getElementById('singleMode');
  elements.batchMode = document.getElementById('batchMode');
  elements.modeTabs = document.querySelectorAll('.mode-tab');
  // Batch mode elements
  elements.batchTagsInput = document.getElementById('batchTagsInput');
  elements.tabsList = document.getElementById('tabsList');
  elements.tabsCount = document.getElementById('tabsCount');
  elements.selectAllTabsBtn = document.getElementById('selectAllTabsBtn');
  elements.deselectAllTabsBtn = document.getElementById('deselectAllTabsBtn');
  elements.batchSaveBtn = document.getElementById('batchSaveBtn');
  elements.batchStatus = document.getElementById('batchStatus');
  elements.batchStatusIcon = document.getElementById('batchStatusIcon');
  elements.batchStatusMessage = document.getElementById('batchStatusMessage');
  elements.batchProgress = document.getElementById('batchProgress');
  elements.batchProgressFill = document.getElementById('batchProgressFill');
  elements.batchProgressText = document.getElementById('batchProgressText');
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

    // Show Notion badge and sub-pages button if detected
    if (currentPage.isNotion) {
      elements.notionBadge.style.display = 'inline-flex';
      elements.saveWithChildrenBtn.style.display = 'block';
      elements.subpagesSection.style.display = 'block';
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
  elements.cancelBtn.addEventListener('click', cancelCrawling);

  // Enter key in tags input triggers save
  elements.tagsInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      savePage(false);
    }
  });

  // Sub-pages selection
  elements.selectAllBtn?.addEventListener('click', selectAllSubPages);
  elements.deselectAllBtn?.addEventListener('click', deselectAllSubPages);

  // Mode tabs
  elements.modeTabs.forEach(tab => {
    tab.addEventListener('click', () => switchMode(tab.dataset.mode));
  });

  // Batch mode events
  elements.selectAllTabsBtn?.addEventListener('click', selectAllTabs);
  elements.deselectAllTabsBtn?.addEventListener('click', deselectAllTabs);
  elements.batchSaveBtn?.addEventListener('click', saveBatchTabs);
}

/**
 * Scan for sub-pages in Notion page
 */
async function scanForSubPages() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Send message to content script to scan
    const response = await chrome.tabs.sendMessage(tab.id, {
      action: 'scanSubPages',
    });

    if (response?.success && response.subPages) {
      subPages = response.subPages;
      renderSubPagesList();
    } else {
      elements.subpagesList.innerHTML = '<div class="subpages-empty">未發現子頁面</div>';
    }
  } catch (error) {
    console.error('Failed to scan sub-pages:', error);
    elements.subpagesList.innerHTML = '<div class="subpages-empty">無法掃描子頁面</div>';
  }
}

/**
 * Render sub-pages list
 */
function renderSubPagesList() {
  if (subPages.length === 0) {
    elements.subpagesList.innerHTML = '<div class="subpages-empty">未發現子頁面</div>';
    elements.subpagesCount.textContent = '';
    return;
  }

  const html = subPages.map((page, index) => `
    <div class="subpage-item">
      <input type="checkbox" id="subpage-${index}" data-index="${index}" checked>
      <label for="subpage-${index}" title="${page.title}">${page.title}</label>
    </div>
  `).join('');

  elements.subpagesList.innerHTML = html;
  updateSubPagesCount();
}

/**
 * Update sub-pages count display
 */
function updateSubPagesCount() {
  const checkboxes = elements.subpagesList.querySelectorAll('input[type="checkbox"]');
  const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
  elements.subpagesCount.textContent = `已選擇 ${checkedCount} / ${subPages.length} 個子頁面`;

  // Update button text
  if (checkedCount > 0) {
    elements.saveWithChildrenBtn.textContent = `📂 收藏此頁 + ${checkedCount} 個子頁面`;
  } else {
    elements.saveWithChildrenBtn.textContent = '📂 收藏選中的頁面';
  }
}

/**
 * Select all sub-pages
 */
function selectAllSubPages() {
  const checkboxes = elements.subpagesList.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = true);
  updateSubPagesCount();
}

/**
 * Deselect all sub-pages
 */
function deselectAllSubPages() {
  const checkboxes = elements.subpagesList.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = false);
  updateSubPagesCount();
}

/**
 * Get selected sub-pages
 * @returns {Array}
 */
function getSelectedSubPages() {
  const checkboxes = elements.subpagesList.querySelectorAll('input[type="checkbox"]:checked');
  return Array.from(checkboxes).map(cb => {
    const index = parseInt(cb.dataset.index);
    return subPages[index];
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

    // Determine source type
    const sourceType = currentPage.isNotion ? 'notion' : 'web';

    if (withChildren && currentPage.isNotion) {
      // Save with sub-pages (tree structure)
      await saveWithSubPages(content, tags, sourceType);
    } else {
      // Save single page
      await saveSinglePage(content, tags, sourceType);
    }
  } catch (error) {
    console.error('Save failed:', error);
    showStatus('error', error.message || '儲存失敗');
  } finally {
    if (!isCrawling) {
      // Re-enable buttons
      elements.saveBtn.disabled = false;
      elements.saveWithChildrenBtn.disabled = false;
    }
  }
}

/**
 * Save single page
 */
async function saveSinglePage(content, tags, sourceType) {
  showStatus('loading', '正在儲存...');

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
  const status = result.results?.[0]?.status || 'new';
  const statusMessages = {
    new: '✨ 新文章已收藏！',
    updated: '🔄 文章已更新！',
    skipped: '⏭️ 文章內容相同，已跳過',
  };

  showStatus('success', statusMessages[status] || '儲存成功！');
}

/**
 * Save with sub-pages (tree structure)
 */
async function saveWithSubPages(rootContent, tags, sourceType) {
  const selectedSubPages = getSelectedSubPages();

  if (selectedSubPages.length === 0) {
    // No sub-pages selected, save only root
    await saveSinglePage(rootContent, tags, sourceType);
    return;
  }

  isCrawling = true;
  elements.cancelBtn.style.display = 'block';

  const totalPages = selectedSubPages.length + 1; // +1 for root
  let processedCount = 0;

  showStatus('loading', '正在抓取子頁面...');
  updateProgress(0, totalPages);

  try {
    // Build tree structure
    const tree = {
      source_type: sourceType,
      source_id: currentPage.notionPageId || generateSourceId(currentPage.url),
      title: currentPage.title,
      content: rootContent.markdown || rootContent.text,
      url: currentPage.url,
      tags: tags,
      children: [],
    };

    processedCount++;
    updateProgress(processedCount, totalPages);

    // Crawl each selected sub-page
    for (const subPage of selectedSubPages) {
      if (!isCrawling) {
        throw new Error('使用者取消操作');
      }

      showStatus('loading', `正在抓取: ${subPage.title.slice(0, 30)}...`);

      try {
        // Fetch sub-page content
        const subContent = await fetchPageContent(subPage.url);

        tree.children.push({
          source_type: sourceType,
          source_id: subPage.id,
          title: subPage.title,
          content: subContent.markdown || subContent.text || '',
          url: subPage.url,
          tags: tags,
          children: [],
        });
      } catch (error) {
        console.error(`Failed to fetch ${subPage.url}:`, error);
        // Continue with other pages
      }

      processedCount++;
      updateProgress(processedCount, totalPages);
    }

    // Save tree to server
    showStatus('loading', '正在儲存...');

    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.treeEndpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root: tree }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || '儲存失敗');
    }

    const result = await response.json();
    const summary = result.summary || {};
    const total = (summary.new || 0) + (summary.updated || 0) + (summary.skipped || 0);

    showStatus('success', `✨ 已收藏 ${total} 個頁面！`);
  } finally {
    isCrawling = false;
    elements.cancelBtn.style.display = 'none';
    hideProgress();
  }
}

/**
 * Cancel crawling operation
 */
function cancelCrawling() {
  isCrawling = false;
  showStatus('error', '已取消');
  elements.cancelBtn.style.display = 'none';
  elements.saveBtn.disabled = false;
  elements.saveWithChildrenBtn.disabled = false;
  hideProgress();
}

/**
 * Fetch content from a URL
 * @param {string} url
 * @returns {Promise<object>}
 */
async function fetchPageContent(url) {
  // We need to open the page and extract content
  // For now, return placeholder - this will be improved with background script
  return new Promise((resolve) => {
    // Create a temporary tab to fetch content
    chrome.tabs.create({ url, active: false }, async (tab) => {
      // Wait for page to load
      const checkLoaded = () => {
        chrome.tabs.get(tab.id, async (tabInfo) => {
          if (tabInfo.status === 'complete') {
            try {
              // Extract content
              const response = await chrome.tabs.sendMessage(tab.id, {
                action: 'extractNotionContent',
              });

              // Close the tab
              chrome.tabs.remove(tab.id);

              resolve(response || { text: '', markdown: '' });
            } catch (error) {
              chrome.tabs.remove(tab.id);
              resolve({ text: '', markdown: '' });
            }
          } else {
            setTimeout(checkLoaded, 500);
          }
        });
      };

      setTimeout(checkLoaded, 1000);
    });
  });
}

/**
 * Extract page content via content script
 * @returns {Promise<object|null>}
 */
async function extractPageContent() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Try Notion-specific extraction first
    if (currentPage.isNotion) {
      try {
        const response = await chrome.tabs.sendMessage(tab.id, {
          action: 'extractNotionContent',
        });
        if (response?.success) {
          return response;
        }
      } catch (e) {
        // Fall through to generic extraction
      }
    }

    // Generic extraction
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
  const encoder = new TextEncoder();
  const data = encoder.encode(url);

  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    const char = data[i];
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
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

// Listen for checkbox changes to update count
document.addEventListener('change', (e) => {
  if (e.target.matches('.subpage-item input[type="checkbox"]')) {
    updateSubPagesCount();
  }
  if (e.target.matches('.tab-item input[type="checkbox"]')) {
    updateTabsCount();
  }
});

/**
 * Switch between single and batch mode
 * @param {string} mode - 'single' or 'batch'
 */
function switchMode(mode) {
  currentMode = mode;

  // Update tab styles
  elements.modeTabs.forEach(tab => {
    tab.classList.toggle('active', tab.dataset.mode === mode);
  });

  // Show/hide mode sections
  if (mode === 'single') {
    elements.singleMode.style.display = 'block';
    elements.batchMode.style.display = 'none';
  } else {
    elements.singleMode.style.display = 'none';
    elements.batchMode.style.display = 'block';
    // Load tabs when switching to batch mode
    loadAllTabs();
  }
}

/**
 * Load all tabs in the current window
 */
async function loadAllTabs() {
  try {
    elements.tabsList.innerHTML = '<div class="tabs-loading">載入中...</div>';

    // Get all tabs in current window
    const tabs = await chrome.tabs.query({ currentWindow: true });

    // Filter out extension pages and empty tabs
    allTabs = tabs.filter(tab => {
      const url = tab.url || '';
      return (
        url.startsWith('http://') ||
        url.startsWith('https://')
      ) && !url.startsWith('chrome://') && !url.startsWith('chrome-extension://');
    });

    renderTabsList();
  } catch (error) {
    console.error('Failed to load tabs:', error);
    elements.tabsList.innerHTML = '<div class="tabs-empty">無法載入分頁</div>';
  }
}

/**
 * Render tabs list
 */
function renderTabsList() {
  if (allTabs.length === 0) {
    elements.tabsList.innerHTML = '<div class="tabs-empty">沒有可收藏的分頁</div>';
    elements.tabsCount.textContent = '';
    elements.batchSaveBtn.disabled = true;
    return;
  }

  const html = allTabs.map((tab, index) => {
    const favicon = tab.favIconUrl || 'icons/icon16.png';
    const title = tab.title || '(無標題)';
    const url = tab.url || '';
    const hostname = new URL(url).hostname;

    return `
      <div class="tab-item">
        <input type="checkbox" id="tab-${index}" data-index="${index}" checked>
        <img class="tab-item-favicon" src="${favicon}" onerror="this.src='icons/icon16.png'">
        <label for="tab-${index}" class="tab-item-content">
          <div class="tab-item-title" title="${title}">${title}</div>
          <div class="tab-item-url" title="${url}">${hostname}</div>
        </label>
      </div>
    `;
  }).join('');

  elements.tabsList.innerHTML = html;
  updateTabsCount();
}

/**
 * Update tabs count display
 */
function updateTabsCount() {
  const checkboxes = elements.tabsList.querySelectorAll('input[type="checkbox"]');
  const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
  elements.tabsCount.textContent = `已選擇 ${checkedCount} / ${allTabs.length} 個分頁`;

  // Update button state
  elements.batchSaveBtn.disabled = checkedCount === 0;
  elements.batchSaveBtn.textContent = checkedCount > 0
    ? `📚 收藏 ${checkedCount} 個分頁`
    : '📚 收藏選中的分頁';
}

/**
 * Select all tabs
 */
function selectAllTabs() {
  const checkboxes = elements.tabsList.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = true);
  updateTabsCount();
}

/**
 * Deselect all tabs
 */
function deselectAllTabs() {
  const checkboxes = elements.tabsList.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = false);
  updateTabsCount();
}

/**
 * Get selected tabs
 * @returns {Array}
 */
function getSelectedTabs() {
  const checkboxes = elements.tabsList.querySelectorAll('input[type="checkbox"]:checked');
  return Array.from(checkboxes).map(cb => {
    const index = parseInt(cb.dataset.index);
    return allTabs[index];
  });
}

/**
 * Show batch status
 * @param {'success'|'error'|'loading'} type
 * @param {string} message
 */
function showBatchStatus(type, message) {
  elements.batchStatus.style.display = 'flex';
  elements.batchStatus.className = `status ${type}`;

  const icons = {
    success: '✅',
    error: '❌',
    loading: '⏳',
  };

  elements.batchStatusIcon.textContent = icons[type] || '';
  elements.batchStatusMessage.textContent = message;

  // Auto-hide success after 3s
  if (type === 'success') {
    setTimeout(() => {
      elements.batchStatus.style.display = 'none';
    }, 3000);
  }
}

/**
 * Update batch progress
 * @param {number} current
 * @param {number} total
 */
function updateBatchProgress(current, total) {
  const percentage = total > 0 ? (current / total) * 100 : 0;
  elements.batchProgress.style.display = 'block';
  elements.batchProgressFill.style.width = `${percentage}%`;
  elements.batchProgressText.textContent = `${current}/${total}`;
}

/**
 * Save batch tabs
 */
async function saveBatchTabs() {
  const selectedTabs = getSelectedTabs();

  if (selectedTabs.length === 0) {
    showBatchStatus('error', '請至少選擇一個分頁');
    return;
  }

  isBatchSaving = true;
  elements.batchSaveBtn.disabled = true;

  const tags = parseTags(elements.batchTagsInput.value);
  const totalTabs = selectedTabs.length;
  let processedCount = 0;
  const articles = [];

  showBatchStatus('loading', '正在擷取頁面內容...');
  updateBatchProgress(0, totalTabs);

  try {
    // Extract content from each tab
    for (const tab of selectedTabs) {
      showBatchStatus('loading', `擷取中: ${tab.title?.slice(0, 30) || ''}...`);

      try {
        // Try to extract content via content script
        let content = null;
        try {
          content = await chrome.tabs.sendMessage(tab.id, {
            action: 'extractContent',
          });
        } catch (e) {
          // Content script might not be loaded, try injecting
          try {
            const results = await chrome.scripting.executeScript({
              target: { tabId: tab.id },
              func: () => {
                return {
                  text: document.body.innerText,
                  html: document.body.innerHTML,
                };
              },
            });
            content = results[0]?.result || null;
          } catch (injectError) {
            console.error(`Failed to inject script for ${tab.url}:`, injectError);
          }
        }

        // Detect if Notion page
        const isNotion = tab.url?.includes('notion.so') || tab.url?.includes('notion.site');
        const notionMatch = tab.url?.match(/([a-f0-9]{32})/i);

        articles.push({
          source_type: isNotion ? 'notion' : 'web',
          source_id: isNotion && notionMatch
            ? notionMatch[1].toLowerCase()
            : generateSourceId(tab.url),
          title: tab.title || '(無標題)',
          content: content?.markdown || content?.text || content?.html || '',
          url: tab.url,
          tags: tags,
          notion_page_id: isNotion && notionMatch ? notionMatch[1].toLowerCase() : null,
        });
      } catch (error) {
        console.error(`Failed to extract content from ${tab.url}:`, error);
      }

      processedCount++;
      updateBatchProgress(processedCount, totalTabs);
    }

    if (articles.length === 0) {
      throw new Error('無法擷取任何頁面內容');
    }

    // Send batch to server
    showBatchStatus('loading', '正在儲存...');

    const response = await fetch(`${CONFIG.serverUrl}${CONFIG.batchEndpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ articles }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || '儲存失敗');
    }

    const result = await response.json();
    const summary = result.summary || {};
    const newCount = summary.new || 0;
    const updatedCount = summary.updated || 0;
    const skippedCount = summary.skipped || 0;

    showBatchStatus('success', `✨ 完成！新增 ${newCount}，更新 ${updatedCount}，跳過 ${skippedCount}`);
  } catch (error) {
    console.error('Batch save failed:', error);
    showBatchStatus('error', error.message || '批量儲存失敗');
  } finally {
    isBatchSaving = false;
    elements.batchSaveBtn.disabled = false;
    elements.batchProgress.style.display = 'none';
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
