# Chrome Extension Conversion Guide

## Overview

This guide explains how to convert the Agentic-AI project into a Chrome extension that reads screen data and uses an LLM to answer questions.

## Architecture Approach

### Option 1: Hybrid Architecture (Recommended)

- **Extension (Frontend)**: UI, screen capture, DOM reading
- **Local Backend Service**: LLM processing, vector storage, tool execution
- **Communication**: Chrome Native Messaging or HTTP API

### Option 2: Fully Self-Contained Extension

- Everything runs in the extension
- Uses Chrome's background service workers
- Limited by extension runtime constraints

**We'll use Option 1** as it maintains your existing backend architecture.

## Project Structure

```
chrome-extension/
├── manifest.json              # Extension configuration
├── background/
│   └── service-worker.js      # Background script
├── content/
│   └── content-script.js      # Injected into web pages
├── popup/
│   ├── popup.html             # Extension popup UI
│   ├── popup.js               # Popup logic
│   └── popup.css              # Popup styles
├── options/
│   ├── options.html           # Settings page
│   └── options.js             # Settings logic
└── icons/                     # Extension icons
```

## Implementation Steps

### Step 1: Create Extension Manifest

```json
{
  "manifest_version": 3,
  "name": "AI Agent Assistant",
  "version": "1.0.0",
  "description": "AI assistant that reads screen content and answers questions",
  "permissions": [
    "activeTab",
    "storage",
    "scripting",
    "tabs",
    "nativeMessaging"
  ],
  "host_permissions": ["http://localhost:8000/*", "https://*/*"],
  "background": {
    "service_worker": "background/service-worker.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content/content-script.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "options_page": "options/options.html",
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

### Step 2: Content Script - Screen Data Extraction

```javascript
// content/content-script.js

class PageContentExtractor {
  constructor() {
    this.setupMessageListener();
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === "extractPageContent") {
        this.extractContent().then(sendResponse);
        return true; // Keep channel open for async response
      }
    });
  }

  async extractContent() {
    const content = {
      url: window.location.href,
      title: document.title,
      text: this.extractText(),
      links: this.extractLinks(),
      images: this.extractImages(),
      forms: this.extractForms(),
      tables: this.extractTables(),
      metadata: this.extractMetadata(),
      timestamp: new Date().toISOString(),
    };

    return content;
  }

  extractText() {
    // Remove script and style elements
    const clone = document.cloneNode(true);
    const scripts = clone.querySelectorAll(
      "script, style, nav, footer, header, aside"
    );
    scripts.forEach((el) => el.remove());

    // Try to find main content
    const mainSelectors = [
      "main",
      "article",
      '[role="main"]',
      ".main-content",
      ".content",
      "#main",
      "#content",
    ];

    let mainContent = null;
    for (const selector of mainSelectors) {
      mainContent = clone.querySelector(selector);
      if (mainContent) break;
    }

    const textElement = mainContent || clone.body || clone.documentElement;
    return textElement.innerText || textElement.textContent || "";
  }

  extractLinks() {
    const links = [];
    document.querySelectorAll("a[href]").forEach((link) => {
      links.push({
        text: link.innerText.trim(),
        url: link.href,
        title: link.title || "",
      });
    });
    return links.slice(0, 50); // Limit to 50 links
  }

  extractImages() {
    const images = [];
    document.querySelectorAll("img[src]").forEach((img) => {
      images.push({
        src: img.src,
        alt: img.alt || "",
        title: img.title || "",
      });
    });
    return images.slice(0, 20); // Limit to 20 images
  }

  extractForms() {
    const forms = [];
    document.querySelectorAll("form").forEach((form) => {
      const inputs = [];
      form.querySelectorAll("input, textarea, select").forEach((input) => {
        inputs.push({
          type: input.type || input.tagName.toLowerCase(),
          name: input.name || "",
          placeholder: input.placeholder || "",
          label: this.getLabelFor(input),
        });
      });
      forms.push({
        action: form.action || "",
        method: form.method || "get",
        inputs: inputs,
      });
    });
    return forms;
  }

  getLabelFor(input) {
    const id = input.id;
    if (id) {
      const label = document.querySelector(`label[for="${id}"]`);
      if (label) return label.innerText.trim();
    }
    // Try to find parent label
    const parentLabel = input.closest("label");
    if (parentLabel) return parentLabel.innerText.trim();
    return "";
  }

  extractTables() {
    const tables = [];
    document.querySelectorAll("table").forEach((table) => {
      const rows = [];
      table.querySelectorAll("tr").forEach((tr) => {
        const cells = [];
        tr.querySelectorAll("td, th").forEach((cell) => {
          cells.push(cell.innerText.trim());
        });
        if (cells.length > 0) rows.push(cells);
      });
      if (rows.length > 0) tables.push(rows);
    });
    return tables.slice(0, 10); // Limit to 10 tables
  }

  extractMetadata() {
    const meta = {};

    // Extract meta tags
    document.querySelectorAll("meta").forEach((metaTag) => {
      const name =
        metaTag.getAttribute("name") ||
        metaTag.getAttribute("property") ||
        metaTag.getAttribute("itemprop");
      const content = metaTag.getAttribute("content");
      if (name && content) {
        meta[name] = content;
      }
    });

    // Extract structured data (JSON-LD)
    document
      .querySelectorAll('script[type="application/ld+json"]')
      .forEach((script) => {
        try {
          const data = JSON.parse(script.textContent);
          meta.structuredData = data;
        } catch (e) {
          // Ignore parse errors
        }
      });

    return meta;
  }
}

// Initialize when script loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    new PageContentExtractor();
  });
} else {
  new PageContentExtractor();
}
```

### Step 3: Background Service Worker

```javascript
// background/service-worker.js

class AIAgentExtension {
  constructor() {
    this.backendUrl = "http://localhost:8000";
    this.setupListeners();
  }

  setupListeners() {
    // Listen for messages from content script and popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender, sendResponse);
      return true; // Keep channel open for async
    });

    // Listen for tab updates to capture page changes
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === "complete" && tab.url) {
        this.onPageLoaded(tabId, tab);
      }
    });
  }

  async handleMessage(request, sender, sendResponse) {
    try {
      switch (request.action) {
        case "getPageContent":
          const content = await this.getPageContent(sender.tab.id);
          sendResponse({ success: true, content });
          break;

        case "askQuestion":
          const answer = await this.askQuestion(
            request.question,
            request.content
          );
          sendResponse({ success: true, answer });
          break;

        case "getConversationHistory":
          const history = await this.getConversationHistory();
          sendResponse({ success: true, history });
          break;

        default:
          sendResponse({ success: false, error: "Unknown action" });
      }
    } catch (error) {
      sendResponse({ success: false, error: error.message });
    }
  }

  async getPageContent(tabId) {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: this.extractPageContent,
      });
      return results[0].result;
    } catch (error) {
      console.error("Error extracting page content:", error);
      throw error;
    }

    // Function to inject into page
    function extractPageContent() {
      // Same extraction logic as content script
      // (injected function runs in page context)
      const clone = document.cloneNode(true);
      const scripts = clone.querySelectorAll(
        "script, style, nav, footer, header"
      );
      scripts.forEach((el) => el.remove());

      const mainSelectors = [
        "main",
        "article",
        '[role="main"]',
        ".main-content",
        "#main",
      ];
      let mainContent = null;
      for (const selector of mainSelectors) {
        mainContent = clone.querySelector(selector);
        if (mainContent) break;
      }

      const textElement = mainContent || clone.body || clone.documentElement;
      const text = textElement.innerText || textElement.textContent || "";

      return {
        url: window.location.href,
        title: document.title,
        text: text.substring(0, 50000), // Limit text size
        timestamp: new Date().toISOString(),
      };
    }
  }

  async askQuestion(question, pageContent) {
    try {
      // Get auth token from storage
      const { token } = await chrome.storage.local.get(["token"]);

      if (!token) {
        throw new Error("Not authenticated. Please login in options page.");
      }

      // Prepare request to backend
      const response = await fetch(
        `${this.backendUrl}/api/chat/conversations/current/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            content: question,
            stream: false,
            page_context: pageContent, // Include page content as context
            selected_tools: [],
            use_deepagent: false,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const data = await response.json();
      return data.final_answer || data.content || "No answer received";
    } catch (error) {
      console.error("Error asking question:", error);
      throw error;
    }
  }

  async getConversationHistory() {
    // Implementation to fetch conversation history
    // Similar to askQuestion but GET request
  }

  async onPageLoaded(tabId, tab) {
    // Optional: Auto-capture page content when page loads
    // Can be enabled/disabled in options
    const { autoCapture } = await chrome.storage.local.get(["autoCapture"]);
    if (autoCapture) {
      const content = await this.getPageContent(tabId);
      await this.storePageContent(tab.url, content);
    }
  }

  async storePageContent(url, content) {
    // Store in chrome.storage.local for offline access
    const key = `page_content_${url}`;
    await chrome.storage.local.set({ [key]: content });
  }
}

// Initialize
const aiAgent = new AIAgentExtension();
```

### Step 4: Popup UI

```html
<!-- popup/popup.html -->
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>AI Agent</title>
    <link rel="stylesheet" href="popup.css" />
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h2>AI Agent Assistant</h2>
        <div class="status" id="status">Ready</div>
      </div>

      <div class="page-info" id="pageInfo">
        <div class="page-title" id="pageTitle">Loading...</div>
        <div class="page-url" id="pageUrl"></div>
      </div>

      <div class="chat-container">
        <div class="messages" id="messages"></div>
        <div class="input-container">
          <textarea
            id="questionInput"
            placeholder="Ask a question about this page..."
            rows="3"
          ></textarea>
          <button id="askButton">Ask</button>
        </div>
      </div>

      <div class="actions">
        <button id="refreshButton">Refresh Page Content</button>
        <button id="settingsButton">Settings</button>
      </div>
    </div>
    <script src="popup.js"></script>
  </body>
</html>
```

```javascript
// popup/popup.js

class PopupController {
  constructor() {
    this.currentTab = null;
    this.currentContent = null;
    this.init();
  }

  async init() {
    // Get current tab
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    this.currentTab = tab;

    // Load page info
    await this.loadPageInfo();

    // Setup event listeners
    document
      .getElementById("askButton")
      .addEventListener("click", () => this.askQuestion());
    document
      .getElementById("questionInput")
      .addEventListener("keypress", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.askQuestion();
        }
      });
    document
      .getElementById("refreshButton")
      .addEventListener("click", () => this.refreshContent());
    document.getElementById("settingsButton").addEventListener("click", () => {
      chrome.runtime.openOptionsPage();
    });
  }

  async loadPageInfo() {
    const titleEl = document.getElementById("pageTitle");
    const urlEl = document.getElementById("pageUrl");

    titleEl.textContent = this.currentTab.title || "Unknown";
    urlEl.textContent = this.currentTab.url || "";

    // Load page content
    await this.refreshContent();
  }

  async refreshContent() {
    const statusEl = document.getElementById("status");
    statusEl.textContent = "Loading page content...";

    try {
      const response = await chrome.runtime.sendMessage({
        action: "getPageContent",
      });

      if (response.success) {
        this.currentContent = response.content;
        statusEl.textContent = `Content loaded (${response.content.text.length} chars)`;
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      statusEl.textContent = `Error: ${error.message}`;
      console.error("Error loading content:", error);
    }
  }

  async askQuestion() {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();

    if (!question) return;
    if (!this.currentContent) {
      await this.refreshContent();
    }

    // Add user message to UI
    this.addMessage("user", question);
    input.value = "";

    // Show loading
    const loadingId = this.addMessage("assistant", "Thinking...", true);

    try {
      const response = await chrome.runtime.sendMessage({
        action: "askQuestion",
        question: question,
        content: this.currentContent,
      });

      if (response.success) {
        this.updateMessage(loadingId, "assistant", response.answer);
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      this.updateMessage(loadingId, "assistant", `Error: ${error.message}`);
    }
  }

  addMessage(role, content, isLoading = false) {
    const messagesEl = document.getElementById("messages");
    const messageId = `msg_${Date.now()}`;
    const messageEl = document.createElement("div");
    messageEl.id = messageId;
    messageEl.className = `message ${role}`;
    messageEl.textContent = content;
    if (isLoading) messageEl.classList.add("loading");
    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return messageId;
  }

  updateMessage(messageId, role, content) {
    const messageEl = document.getElementById(messageId);
    if (messageEl) {
      messageEl.textContent = content;
      messageEl.classList.remove("loading");
    }
  }
}

// Initialize when popup opens
document.addEventListener("DOMContentLoaded", () => {
  new PopupController();
});
```

### Step 5: Backend API Modification

You need to modify your backend to accept page context:

```python
# backend/api/chat.py - Add page_context parameter

class MessageCreate(BaseModel):
    content: str
    stream: bool = True
    selected_tools: List[str] = []
    use_deepagent: bool = False
    file_contents: List[Dict] = []
    page_context: Optional[Dict] = None  # NEW: Page content from extension

@router.post("/conversations/{conversation_id}/messages")
async def create_message(
    conversation_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Include page_context in the agent execution
    if message.page_context:
        # Add page context to the conversation context
        context_text = f"""
Page Context:
URL: {message.page_context.get('url', 'Unknown')}
Title: {message.page_context.get('title', 'Unknown')}
Content: {message.page_context.get('text', '')[:5000]}  # Limit context size
"""
        # Prepend context to user message
        enhanced_content = f"{context_text}\n\nUser Question: {message.content}"
        message.content = enhanced_content

    # Continue with existing agent execution...
```

## Key Features

1. **Screen Reading**: Content script extracts text, links, images, forms, tables
2. **Context-Aware**: LLM receives page content as context
3. **Offline Support**: Can cache page content in chrome.storage
4. **Privacy**: All processing happens locally (backend on localhost)

## Challenges & Solutions

### Challenge 1: CORS Issues

**Solution**: Use Chrome extension's host_permissions or run backend with CORS enabled

### Challenge 2: Authentication

**Solution**: Store JWT token in chrome.storage.local, refresh as needed

### Challenge 3: Large Page Content

**Solution**: Truncate content, use summarization, or chunk processing

### Challenge 4: Dynamic Content

**Solution**: Re-extract content on demand, use MutationObserver for changes

## Next Steps

1. Create the extension directory structure
2. Implement content extraction
3. Modify backend to accept page context
4. Test with various websites
5. Add error handling and user feedback
6. Package for Chrome Web Store (optional)

## Testing

1. Load extension in Chrome (chrome://extensions, Developer mode)
2. Navigate to any website
3. Click extension icon
4. Ask questions about the page content
5. Verify LLM responses use page context

## Deployment

- **Development**: Load unpacked extension
- **Production**: Package as .crx file
- **Distribution**: Chrome Web Store or enterprise distribution
