/**
 * Notion Sub-Page Scanner
 * Scans Notion pages for sub-page links and extracts metadata
 */

/**
 * Notion page ID pattern (32 hex chars or UUID format)
 */
const PAGE_ID_PATTERN = /([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/i;

/**
 * Get current page title
 * @returns {string}
 */
export function getPageTitle() {
  // Try Notion-specific title
  const notionTitle = document.querySelector('.notion-page-block .notranslate');
  if (notionTitle) {
    return notionTitle.textContent.trim();
  }

  // Try header element
  const header = document.querySelector('[data-block-id] [contenteditable="true"]');
  if (header) {
    const text = header.textContent.trim();
    if (text) return text;
  }

  // Try document title
  const title = document.title.replace(/\s*[-|]\s*Notion\s*$/, '').trim();
  return title || 'Untitled';
}

/**
 * Get current page ID from URL
 * @returns {string|null}
 */
export function getPageId() {
  const url = window.location.href;
  const match = url.match(PAGE_ID_PATTERN);
  if (match) {
    return match[1].replace(/-/g, '');
  }
  return null;
}

/**
 * Format page ID as UUID
 * @param {string} id - 32-char page ID
 * @returns {string}
 */
export function formatPageIdAsUuid(id) {
  if (!id || id.length !== 32) return id;
  return `${id.slice(0, 8)}-${id.slice(8, 12)}-${id.slice(12, 16)}-${id.slice(16, 20)}-${id.slice(20)}`;
}

/**
 * Scan for sub-pages in current Notion page
 * @returns {Array<{url: string, title: string, id: string}>}
 */
export function scanSubPages() {
  const subPages = [];
  const seenIds = new Set();
  const currentPageId = getPageId();

  // Method 1: Find page blocks (child pages within content)
  const pageBlocks = document.querySelectorAll('[class*="notion-page-block"], [class*="notion-child_page-block"]');
  pageBlocks.forEach(block => {
    const pageInfo = extractPageFromBlock(block);
    if (pageInfo && pageInfo.id !== currentPageId && !seenIds.has(pageInfo.id)) {
      seenIds.add(pageInfo.id);
      subPages.push(pageInfo);
    }
  });

  // Method 2: Find links to Notion pages
  const links = document.querySelectorAll('a[href*="notion.so"], a[href*="notion.site"]');
  links.forEach(link => {
    const pageInfo = extractPageFromLink(link);
    if (pageInfo && pageInfo.id !== currentPageId && !seenIds.has(pageInfo.id)) {
      seenIds.add(pageInfo.id);
      subPages.push(pageInfo);
    }
  });

  // Method 3: Find page mentions/references
  const pageMentions = document.querySelectorAll('[data-token-index][href*="/"]');
  pageMentions.forEach(mention => {
    const pageInfo = extractPageFromMention(mention);
    if (pageInfo && pageInfo.id !== currentPageId && !seenIds.has(pageInfo.id)) {
      seenIds.add(pageInfo.id);
      subPages.push(pageInfo);
    }
  });

  // Method 4: Check sidebar for sub-pages (if visible)
  const sidebarLinks = document.querySelectorAll('.notion-sidebar a[href*="/"]');
  sidebarLinks.forEach(link => {
    const pageInfo = extractPageFromLink(link);
    if (pageInfo && pageInfo.id !== currentPageId && !seenIds.has(pageInfo.id)) {
      seenIds.add(pageInfo.id);
      subPages.push(pageInfo);
    }
  });

  return subPages;
}

/**
 * Extract page info from a page block element
 * @param {Element} block
 * @returns {{url: string, title: string, id: string}|null}
 */
function extractPageFromBlock(block) {
  // Try to get the link inside the block
  const link = block.querySelector('a[href]');
  if (link) {
    return extractPageFromLink(link);
  }

  // Try to extract from block ID
  const blockId = block.getAttribute('data-block-id');
  if (blockId) {
    const id = blockId.replace(/-/g, '');
    if (id.length === 32) {
      const title = block.textContent.trim() || 'Untitled';
      return {
        url: `https://notion.so/${id}`,
        title: cleanTitle(title),
        id: id,
      };
    }
  }

  return null;
}

/**
 * Extract page info from a link element
 * @param {HTMLAnchorElement} link
 * @returns {{url: string, title: string, id: string}|null}
 */
function extractPageFromLink(link) {
  const href = link.href || link.getAttribute('href');
  if (!href) return null;

  // Check if it's a Notion page link
  if (!href.includes('notion.so') && !href.includes('notion.site')) {
    // Check for relative links
    if (!href.startsWith('/')) return null;
  }

  // Extract page ID
  const match = href.match(PAGE_ID_PATTERN);
  if (!match) return null;

  const id = match[1].replace(/-/g, '');

  // Get title
  let title = link.textContent.trim();
  if (!title) {
    title = link.getAttribute('aria-label') || link.getAttribute('title') || 'Untitled';
  }

  // Build full URL
  let url = href;
  if (href.startsWith('/')) {
    url = `https://notion.so${href}`;
  }

  return {
    url: url,
    title: cleanTitle(title),
    id: id,
  };
}

/**
 * Extract page info from a page mention
 * @param {Element} mention
 * @returns {{url: string, title: string, id: string}|null}
 */
function extractPageFromMention(mention) {
  const href = mention.getAttribute('href');
  if (!href) return null;

  const match = href.match(PAGE_ID_PATTERN);
  if (!match) return null;

  const id = match[1].replace(/-/g, '');
  const title = mention.textContent.trim() || 'Untitled';

  return {
    url: `https://notion.so/${id}`,
    title: cleanTitle(title),
    id: id,
  };
}

/**
 * Clean title text
 * @param {string} title
 * @returns {string}
 */
function cleanTitle(title) {
  return title
    .replace(/^\s*[-•]\s*/, '') // Remove list markers
    .replace(/\s+/g, ' ')        // Normalize whitespace
    .trim()
    .slice(0, 200);              // Limit length
}

/**
 * Extract content from current Notion page
 * @returns {{title: string, content: string, markdown: string}}
 */
export function extractNotionContent() {
  const title = getPageTitle();

  // Get main content area
  const contentArea = document.querySelector('.notion-page-content') ||
                      document.querySelector('.notion-scroller') ||
                      document.querySelector('main') ||
                      document.body;

  // Extract text content
  const content = contentArea.innerText || '';

  // Try to build markdown (simplified)
  const markdown = buildMarkdownFromNotion(contentArea);

  return {
    title,
    content,
    markdown: markdown || content,
  };
}

/**
 * Build markdown from Notion DOM structure
 * @param {Element} container
 * @returns {string}
 */
function buildMarkdownFromNotion(container) {
  const parts = [];

  // Find all content blocks
  const blocks = container.querySelectorAll('[data-block-id]');

  blocks.forEach(block => {
    const markdown = blockToMarkdown(block);
    if (markdown) {
      parts.push(markdown);
    }
  });

  // If no blocks found, fallback to basic extraction
  if (parts.length === 0) {
    return container.innerText || '';
  }

  return parts.join('\n\n');
}

/**
 * Convert a Notion block to markdown
 * @param {Element} block
 * @returns {string}
 */
function blockToMarkdown(block) {
  const classList = Array.from(block.classList || []).join(' ');
  const text = block.innerText?.trim() || '';

  // Header blocks
  if (classList.includes('notion-header-block') || classList.includes('notion-h1')) {
    return `# ${text}`;
  }
  if (classList.includes('notion-sub_header-block') || classList.includes('notion-h2')) {
    return `## ${text}`;
  }
  if (classList.includes('notion-sub_sub_header-block') || classList.includes('notion-h3')) {
    return `### ${text}`;
  }

  // Code block
  if (classList.includes('notion-code-block')) {
    const code = block.querySelector('code')?.innerText || text;
    return '```\n' + code + '\n```';
  }

  // Quote/Callout
  if (classList.includes('notion-quote-block') || classList.includes('notion-callout-block')) {
    return text.split('\n').map(line => `> ${line}`).join('\n');
  }

  // Bulleted list
  if (classList.includes('notion-bulleted_list-block')) {
    return `- ${text}`;
  }

  // Numbered list
  if (classList.includes('notion-numbered_list-block')) {
    return `1. ${text}`;
  }

  // Toggle
  if (classList.includes('notion-toggle-block')) {
    return `<details>\n<summary>${text}</summary>\n</details>`;
  }

  // Divider
  if (classList.includes('notion-divider-block')) {
    return '---';
  }

  // Default: text block
  if (text) {
    return text;
  }

  return '';
}

/**
 * Message handler for content script
 */
if (typeof chrome !== 'undefined' && chrome.runtime) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    try {
      switch (message.action) {
        case 'scanSubPages':
          const subPages = scanSubPages();
          sendResponse({ success: true, subPages });
          break;

        case 'getPageInfo':
          sendResponse({
            success: true,
            pageInfo: {
              title: getPageTitle(),
              id: getPageId(),
              url: window.location.href,
            },
          });
          break;

        case 'extractNotionContent':
          const content = extractNotionContent();
          sendResponse({ success: true, ...content });
          break;

        default:
          // Let other handlers process
          return false;
      }
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
    return true;
  });
}
