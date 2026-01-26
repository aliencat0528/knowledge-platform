/**
 * Notion Page Detector
 * Detects if current page is a Notion page and extracts metadata
 */

/**
 * Check if URL is a Notion page
 * @param {string} url - URL to check
 * @returns {boolean}
 */
export function isNotionUrl(url) {
  if (!url) return false;

  const notionPatterns = [
    /^https?:\/\/(?:www\.)?notion\.so\//,
    /^https?:\/\/(?:www\.)?notion\.site\//,
    /^https?:\/\/[^/]+\.notion\.site\//,
  ];

  return notionPatterns.some(pattern => pattern.test(url));
}

/**
 * Extract Notion page ID from URL
 * @param {string} url - Notion URL
 * @returns {string|null} - Page ID or null
 */
export function extractNotionPageId(url) {
  if (!isNotionUrl(url)) return null;

  // Pattern 1: notion.so/username/Page-Title-<id>
  // Pattern 2: notion.so/<id>
  // Pattern 3: custom.notion.site/Page-Title-<id>

  const urlObj = new URL(url);
  const pathname = urlObj.pathname;

  // Try to extract 32-char hex ID (with or without dashes)
  // Notion IDs are UUIDs without dashes (32 hex chars)
  const idMatch = pathname.match(/([a-f0-9]{32})(?:\?|$)/i);
  if (idMatch) {
    return idMatch[1];
  }

  // Try to extract from end of path (Page-Title-<id> format)
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length > 0) {
    const lastSegment = segments[segments.length - 1];
    // ID is usually the last 32 chars after the last dash
    const dashParts = lastSegment.split('-');
    if (dashParts.length > 0) {
      const possibleId = dashParts[dashParts.length - 1];
      if (/^[a-f0-9]{32}$/i.test(possibleId)) {
        return possibleId;
      }
    }
  }

  return null;
}

/**
 * Format Notion page ID to UUID format
 * @param {string} id - 32-char hex ID
 * @returns {string} - UUID format (8-4-4-4-12)
 */
export function formatNotionIdAsUuid(id) {
  if (!id || id.length !== 32) return id;

  return [
    id.slice(0, 8),
    id.slice(8, 12),
    id.slice(12, 16),
    id.slice(16, 20),
    id.slice(20, 32),
  ].join('-');
}

/**
 * Detect Notion page info from current tab
 * @param {object} tab - Chrome tab object
 * @returns {object} - Detection result
 */
export function detectNotionPage(tab) {
  const url = tab?.url || '';
  const title = tab?.title || '';

  const isNotion = isNotionUrl(url);
  const pageId = extractNotionPageId(url);

  return {
    isNotion,
    pageId,
    formattedId: pageId ? formatNotionIdAsUuid(pageId) : null,
    url,
    title: title.replace(' | Notion', '').trim(), // Clean Notion suffix
  };
}

/**
 * Check if Notion page has sub-pages (requires content script)
 * This is a heuristic check based on DOM structure
 * @returns {Promise<boolean>}
 */
export async function hasNotionSubPages() {
  // This should be called from content script context
  // Checks for sidebar or page links indicating sub-pages

  const indicators = [
    // Sub-page links in sidebar
    '.notion-sidebar-container a[href*="notion.so"]',
    // Toggle blocks that might contain sub-pages
    '.notion-toggle-block',
    // Page links within content
    '.notion-page-block',
    // Child page mentions
    '[data-block-id] .notion-link-token',
  ];

  for (const selector of indicators) {
    const elements = document.querySelectorAll(selector);
    if (elements.length > 0) {
      return true;
    }
  }

  return false;
}
