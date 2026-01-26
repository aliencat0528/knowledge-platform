/**
 * Content Extractor
 * Extracts page content for Knowledge Collector
 *
 * Uses:
 * - Readability.js for content extraction
 * - Turndown.js for HTML to Markdown conversion
 */

/**
 * Extract main content from current page
 * @returns {object} Extracted content
 */
function extractContent() {
  try {
    // Try using Readability for better extraction
    if (typeof Readability !== 'undefined') {
      return extractWithReadability();
    }
  } catch (e) {
    console.warn('Readability extraction failed, using fallback:', e);
  }

  // Fallback to basic extraction
  return extractBasic();
}

/**
 * Extract content using Readability.js
 * @returns {object}
 */
function extractWithReadability() {
  // Clone document to avoid modifying the original
  const documentClone = document.cloneNode(true);

  // Create Readability instance
  const reader = new Readability(documentClone, {
    charThreshold: 100,
    classesToPreserve: ['highlight', 'code', 'pre'],
  });

  const article = reader.parse();

  if (!article) {
    console.warn('Readability could not parse article, using fallback');
    return extractBasic();
  }

  // Convert HTML to Markdown using Turndown
  let markdown = null;
  if (typeof TurndownService !== 'undefined') {
    markdown = convertToMarkdown(article.content);
  }

  return {
    title: article.title || extractTitle(),
    text: article.textContent || '',
    html: article.content || '',
    markdown: markdown,
    metadata: {
      ...extractMetadata(),
      byline: article.byline,
      siteName: article.siteName,
      excerpt: article.excerpt,
      length: article.length,
    },
  };
}

/**
 * Convert HTML to Markdown using Turndown.js
 * @param {string} html
 * @returns {string}
 */
function convertToMarkdown(html) {
  try {
    const turndownService = new TurndownService({
      headingStyle: 'atx',
      codeBlockStyle: 'fenced',
      emDelimiter: '*',
      bulletListMarker: '-',
      hr: '---',
    });

    // Add custom rules for better code block handling
    turndownService.addRule('codeBlock', {
      filter: function (node) {
        return node.nodeName === 'PRE' && node.querySelector('code');
      },
      replacement: function (content, node) {
        const code = node.querySelector('code');
        const language = code?.className?.match(/language-(\w+)/)?.[1] || '';
        const text = code?.textContent || content;
        return `\n\`\`\`${language}\n${text}\n\`\`\`\n`;
      },
    });

    // Keep inline code
    turndownService.addRule('inlineCode', {
      filter: function (node) {
        return node.nodeName === 'CODE' && node.parentNode.nodeName !== 'PRE';
      },
      replacement: function (content) {
        return '`' + content + '`';
      },
    });

    return turndownService.turndown(html);
  } catch (e) {
    console.error('Markdown conversion failed:', e);
    return null;
  }
}

/**
 * Basic extraction fallback
 * @returns {object}
 */
function extractBasic() {
  return {
    title: extractTitle(),
    text: extractText(),
    html: extractHtml(),
    markdown: null,
    metadata: extractMetadata(),
  };
}

/**
 * Extract page title
 * @returns {string}
 */
function extractTitle() {
  const sources = [
    () => document.querySelector('meta[property="og:title"]')?.content,
    () => document.querySelector('meta[name="twitter:title"]')?.content,
    () => document.querySelector('h1')?.textContent,
    () => document.title,
  ];

  for (const source of sources) {
    const title = source();
    if (title && title.trim()) {
      return title.trim();
    }
  }

  return 'Untitled';
}

/**
 * Extract main text content
 * @returns {string}
 */
function extractText() {
  const mainSelectors = [
    'article',
    'main',
    '[role="main"]',
    '.post-content',
    '.article-content',
    '.entry-content',
    '.content',
    '#content',
    '.notion-page-content',
  ];

  for (const selector of mainSelectors) {
    const element = document.querySelector(selector);
    if (element && element.textContent.trim().length > 100) {
      return cleanText(element.textContent);
    }
  }

  return cleanText(document.body.textContent);
}

/**
 * Extract HTML content
 * @returns {string}
 */
function extractHtml() {
  const mainSelectors = [
    'article',
    'main',
    '[role="main"]',
    '.post-content',
    '.article-content',
    '.entry-content',
    '.content',
    '#content',
    '.notion-page-content',
  ];

  for (const selector of mainSelectors) {
    const element = document.querySelector(selector);
    if (element && element.innerHTML.length > 200) {
      return cleanHtml(element.innerHTML);
    }
  }

  const body = document.body.cloneNode(true);
  const unwanted = body.querySelectorAll(
    'script, style, nav, header, footer, aside, .sidebar, .ads, .advertisement, .comments'
  );
  unwanted.forEach(el => el.remove());

  return cleanHtml(body.innerHTML);
}

/**
 * Extract metadata
 * @returns {object}
 */
function extractMetadata() {
  return {
    url: window.location.href,
    domain: window.location.hostname,
    description: getMetaContent('description') || getMetaContent('og:description'),
    author: getMetaContent('author') || getMetaContent('article:author'),
    publishedAt: getMetaContent('article:published_time') || getMetaContent('datePublished'),
    image: getMetaContent('og:image'),
    siteName: getMetaContent('og:site_name'),
    type: getMetaContent('og:type'),
  };
}

/**
 * Get meta tag content
 * @param {string} name
 * @returns {string|null}
 */
function getMetaContent(name) {
  const selectors = [
    `meta[name="${name}"]`,
    `meta[property="${name}"]`,
    `meta[property="og:${name}"]`,
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element?.content) {
      return element.content;
    }
  }

  return null;
}

/**
 * Clean text content
 * @param {string} text
 * @returns {string}
 */
function cleanText(text) {
  return text
    .replace(/\s+/g, ' ')
    .replace(/\n\s*\n/g, '\n\n')
    .trim();
}

/**
 * Clean HTML content
 * @param {string} html
 * @returns {string}
 */
function cleanHtml(html) {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/on\w+="[^"]*"/gi, '')
    .replace(/javascript:[^"']*/gi, '');
}

/**
 * Check if current page is Notion
 * @returns {boolean}
 */
function isNotionPage() {
  return window.location.hostname.includes('notion.so') ||
         window.location.hostname.includes('notion.site');
}

/**
 * Extract Notion-specific content
 * @returns {object}
 */
function extractNotionContent() {
  // For Notion, we use a combination approach
  const pageContent = document.querySelector('.notion-page-content');
  const pageTitle = document.querySelector('.notion-page-block h1') ||
                    document.querySelector('[data-block-id] [placeholder="Untitled"]');

  let html = pageContent ? cleanHtml(pageContent.innerHTML) : extractHtml();
  let markdown = null;

  // Try to convert to markdown
  if (typeof TurndownService !== 'undefined' && html) {
    markdown = convertToMarkdown(html);
  }

  return {
    title: pageTitle?.textContent?.trim() || extractTitle(),
    text: pageContent ? cleanText(pageContent.textContent) : extractText(),
    html: html,
    markdown: markdown,
    metadata: {
      ...extractMetadata(),
      isNotion: true,
    },
  };
}

/**
 * Listen for messages from popup or background
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'extractContent') {
    try {
      const content = isNotionPage() ? extractNotionContent() : extractContent();
      sendResponse(content);
    } catch (error) {
      console.error('Content extraction error:', error);
      sendResponse({ error: error.message });
    }
  }

  return true;
});

// Log when content script loads
console.log('Knowledge Collector: Content extractor loaded (with Readability & Turndown)');
