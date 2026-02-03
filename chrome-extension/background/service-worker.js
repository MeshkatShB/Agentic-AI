// background/service-worker.js

class AIAgentExtension {
  constructor() {
    this.setupListeners();
    this.loadConfig();
  }

  async loadConfig() {
    const config = await chrome.storage.local.get(["backendUrl"]);
    this.backendUrl = config.backendUrl || "http://localhost:8000";
  }

  setupListeners() {
    // Listen for messages from content script and popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleMessage(request, sender, sendResponse);
      return true; // Keep channel open for async
    });

    // Listen for tab updates to capture page changes (optional)
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === "complete" && tab.url) {
        this.onPageLoaded(tabId, tab);
      }
    });

    // Listen for storage changes to update backend URL
    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName === "local" && changes.backendUrl) {
        this.backendUrl =
          changes.backendUrl.newValue || "http://localhost:8000";
      }
    });
  }

  async handleMessage(request, sender, sendResponse) {
    try {
      await this.loadConfig(); // Ensure config is up to date

      switch (request.action) {
        case "getPageContent":
          const content = await this.getPageContent(sender.tab?.id);
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
          const history = await this.getConversationHistory(
            request.conversationId
          );
          sendResponse({ success: true, history });
          break;

        case "createConversation":
          const conversation = await this.createConversation();
          sendResponse({ success: true, conversation });
          break;

        case "getCurrentConversation":
          const currentConv = await this.getCurrentConversation();
          sendResponse({ success: true, conversation: currentConv });
          break;

        default:
          sendResponse({ success: false, error: "Unknown action" });
      }
    } catch (error) {
      console.error("Error handling message:", error);
      sendResponse({ success: false, error: error.message });
    }
  }

  async getPageContent(tabId) {
    try {
      if (!tabId) {
        // Get current active tab
        const [tab] = await chrome.tabs.query({
          active: true,
          currentWindow: true,
        });
        tabId = tab?.id;
      }

      if (!tabId) {
        throw new Error("No active tab found");
      }

      // Try to get content from content script first
      try {
        const response = await chrome.tabs.sendMessage(tabId, {
          action: "extractPageContent",
        });
        if (response) return response;
      } catch (e) {
        console.log("Content script not available, using injected script");
      }

      // Fallback: inject script to extract content
      const results = await chrome.scripting.executeScript({
        target: { tabId },
        func: this.extractPageContent,
      });

      if (!results || !results[0] || !results[0].result) {
        throw new Error("Failed to extract page content");
      }

      return results[0].result;
    } catch (error) {
      console.error("Error extracting page content:", error);
      throw error;
    }
  }

  // Function to inject into page (runs in page context)
  extractPageContent() {
    const clone = document.cloneNode(true);
    const scripts = clone.querySelectorAll(
      "script, style, nav, footer, header, aside"
    );
    scripts.forEach((el) => el.remove());

    const mainSelectors = [
      "main",
      "article",
      '[role="main"]',
      ".main-content",
      ".content",
      "#main",
      "#content",
      ".post-content",
      ".entry-content",
    ];

    let mainContent = null;
    for (const selector of mainSelectors) {
      mainContent = clone.querySelector(selector);
      if (mainContent) break;
    }

    const textElement = mainContent || clone.body || clone.documentElement;
    const text = (
      textElement.innerText ||
      textElement.textContent ||
      ""
    ).substring(0, 50000);

    // Extract links
    const links = [];
    document.querySelectorAll("a[href]").forEach((link) => {
      if (links.length < 50) {
        links.push({
          text: link.innerText.trim(),
          url: link.href,
          title: link.title || "",
        });
      }
    });

    // Extract metadata
    const meta = {};
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

    return {
      url: window.location.href,
      title: document.title,
      text: text,
      links: links,
      metadata: meta,
      timestamp: new Date().toISOString(),
    };
  }

  async askQuestion(question, pageContent) {
    try {
      // Get auth token and conversation ID from storage
      const { token, conversationId } = await chrome.storage.local.get([
        "token",
        "conversationId",
      ]);

      if (!token) {
        throw new Error("Not authenticated. Please login in the options page.");
      }

      // Get or create conversation
      let convId = conversationId;
      if (!convId) {
        const conv = await this.createConversation();
        convId = conv.id;
        await chrome.storage.local.set({ conversationId: convId });
      }

      // Prepare request to backend
      const response = await fetch(
        `${this.backendUrl}/api/chat/conversations/${convId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            content: question,
            stream: false,
            page_context: pageContent,
            selected_tools: [],
            use_deepagent: false,
          }),
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired, clear it
          await chrome.storage.local.remove(["token"]);
          throw new Error("Session expired. Please login again.");
        }
        if (response.status === 404) {
          // Conversation not found - clear it and create a new one
          console.log("Conversation not found, creating new conversation...");
          await chrome.storage.local.remove(["conversationId"]);
          const newConv = await this.createConversation();
          convId = newConv.id;
          await chrome.storage.local.set({ conversationId: convId });
          
          // Retry the request with the new conversation ID
          const retryResponse = await fetch(
            `${this.backendUrl}/api/chat/conversations/${convId}/messages`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                content: question,
                stream: false,
                page_context: pageContent,
                selected_tools: [],
                use_deepagent: false,
              }),
            }
          );
          
          if (!retryResponse.ok) {
            const errorText = await retryResponse.text();
            throw new Error(`Backend error: ${retryResponse.status} ${errorText}`);
          }
          
          const retryData = await retryResponse.json();
          
          // Extract answer using same logic as below
          if (retryData.type === "complete" && retryData.response) {
            const answer = retryData.response.final_answer;
            if (answer && answer.trim()) {
              return answer.trim();
            }
          }
          if (retryData.final_answer && retryData.final_answer.trim()) {
            return retryData.final_answer.trim();
          }
          if (retryData.response && retryData.response.final_answer) {
            const answer = retryData.response.final_answer;
            if (answer && answer.trim()) {
              return answer.trim();
            }
          }
          if (retryData.content && retryData.content.trim()) {
            return retryData.content.trim();
          }
          if (retryData.output && retryData.output.trim()) {
            return retryData.output.trim();
          }
          return "No answer received.";
        }
        const errorText = await response.text();
        throw new Error(`Backend error: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      
      console.log("Backend response:", data); // Debug log
      
      // Handle different response formats
      // Format 1: { type: "complete", response: { final_answer: "..." } }
      if (data.type === "complete" && data.response) {
        const answer = data.response.final_answer;
        if (answer && answer.trim()) {
          return answer.trim();
        }
      }
      
      // Format 2: Direct response with final_answer
      if (data.final_answer && data.final_answer.trim()) {
        return data.final_answer.trim();
      }
      
      // Format 3: Nested response object
      if (data.response && data.response.final_answer) {
        const answer = data.response.final_answer;
        if (answer && answer.trim()) {
          return answer.trim();
        }
      }
      
      // Format 4: Fallback to content or output
      if (data.content && data.content.trim()) {
        return data.content.trim();
      }
      
      if (data.output && data.output.trim()) {
        return data.output.trim();
      }
      
      // If we get here, log the full response for debugging
      console.warn("Could not extract answer from response:", JSON.stringify(data, null, 2));
      return "No answer received. Please check the console for details.";
    } catch (error) {
      console.error("Error asking question:", error);
      throw error;
    }
  }

  async createConversation() {
    try {
      const { token } = await chrome.storage.local.get(["token"]);

      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(
        `${this.backendUrl}/api/chat/conversations`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            title: "Chrome Extension Chat",
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to create conversation: ${response.statusText}`
        );
      }

      const data = await response.json();
      return data.conversation || data;
    } catch (error) {
      console.error("Error creating conversation:", error);
      throw error;
    }
  }

  async getCurrentConversation() {
    const { conversationId } = await chrome.storage.local.get([
      "conversationId",
    ]);
    return conversationId;
  }

  async getConversationHistory(conversationId) {
    try {
      const { token } = await chrome.storage.local.get(["token"]);

      if (!token) {
        throw new Error("Not authenticated");
      }

      const convId = conversationId || (await this.getCurrentConversation());
      if (!convId) {
        return { messages: [] };
      }

      const response = await fetch(
        `${this.backendUrl}/api/chat/conversations/${convId}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to get conversation: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error getting conversation history:", error);
      throw error;
    }
  }

  async onPageLoaded(tabId, tab) {
    // Optional: Auto-capture page content when page loads
    // Can be enabled/disabled in options
    const { autoCapture } = await chrome.storage.local.get(["autoCapture"]);
    if (
      autoCapture &&
      tab.url &&
      !tab.url.startsWith("chrome://") &&
      !tab.url.startsWith("chrome-extension://")
    ) {
      try {
        const content = await this.getPageContent(tabId);
        await this.storePageContent(tab.url, content);
      } catch (error) {
        console.log("Auto-capture failed:", error);
      }
    }
  }

  async storePageContent(url, content) {
    // Store in chrome.storage.local for offline access
    const key = `page_content_${url}`;
    await chrome.storage.local.set({ [key]: content });

    // Limit stored pages to last 50
    const allKeys = Object.keys(await chrome.storage.local.get(null));
    const pageKeys = allKeys.filter((k) => k.startsWith("page_content_"));
    if (pageKeys.length > 50) {
      // Remove oldest (simple approach: remove first)
      await chrome.storage.local.remove(pageKeys[0]);
    }
  }
}

// Initialize
const aiAgent = new AIAgentExtension();
