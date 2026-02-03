// popup/popup.js

class PopupController {
  constructor() {
    this.currentTab = null;
    this.currentContent = null;
    this.conversationId = null;
    this.messages = [];
    this.init();
  }

  async init() {
    // Get current tab
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      this.currentTab = tab;

      // Load conversation ID and history
      await this.loadConversation();

      // Load page info
      await this.loadPageInfo();

      // Load and display conversation history
      await this.loadHistory();

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
      document
        .getElementById("settingsButton")
        .addEventListener("click", () => {
          chrome.runtime.openOptionsPage();
        });
      document
        .getElementById("clearButton")
        .addEventListener("click", () => this.clearHistory());
    } catch (error) {
      this.showError("Failed to initialize: " + error.message);
    }
  }

  async loadConversation() {
    // Get or create conversation ID
    const { conversationId } = await chrome.storage.local.get(["conversationId"]);
    if (!conversationId) {
      // Create a new conversation
      try {
        const { token } = await chrome.storage.local.get(["token"]);
        if (!token) {
          // Can't create conversation without auth
          return;
        }
        
        const response = await chrome.runtime.sendMessage({
          action: "createConversation",
        });
        if (response && response.success) {
          // Handle different response formats
          const conv = response.conversation;
          this.conversationId = conv?.id || conv || response.conversationId;
          if (this.conversationId) {
            await chrome.storage.local.set({ conversationId: this.conversationId });
          }
        }
      } catch (error) {
        console.error("Failed to create conversation:", error);
      }
    } else {
      this.conversationId = conversationId;
    }
  }

  async loadHistory() {
    if (!this.conversationId) return;

    try {
      // Load messages from storage
      const storageKey = `messages_${this.conversationId}`;
      const { [storageKey]: storedMessages } = await chrome.storage.local.get([storageKey]);

      if (storedMessages && Array.isArray(storedMessages)) {
        this.messages = storedMessages;
        // Display all messages
        const messagesEl = document.getElementById("messages");
        messagesEl.innerHTML = ""; // Clear existing messages
        storedMessages.forEach((msg) => {
          this.displayMessage(msg.role, msg.content, false, msg.id);
        });
        // Scroll to bottom
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }
    } catch (error) {
      console.error("Error loading history:", error);
    }
  }

  async saveMessage(role, content, messageId = null) {
    if (!this.conversationId) return;

    const msg = {
      id: messageId || `msg_${Date.now()}`,
      role: role,
      content: content,
      timestamp: new Date().toISOString(),
    };

    this.messages.push(msg);

    // Save to storage
    const storageKey = `messages_${this.conversationId}`;
    await chrome.storage.local.set({ [storageKey]: this.messages });

    // Limit to last 100 messages to avoid storage issues
    if (this.messages.length > 100) {
      this.messages = this.messages.slice(-100);
      await chrome.storage.local.set({ [storageKey]: this.messages });
    }
  }

  async clearHistory() {
    if (!confirm("Clear conversation history?")) return;

    // Clear conversation ID to force creation of new conversation
    await chrome.storage.local.remove(["conversationId"]);
    this.conversationId = null;

    if (this.conversationId) {
      const storageKey = `messages_${this.conversationId}`;
      await chrome.storage.local.remove([storageKey]);
    }

    this.messages = [];
    const messagesEl = document.getElementById("messages");
    messagesEl.innerHTML = "";
    this.showError("History cleared. New conversation will be created on next question.");
  }

  async loadPageInfo() {
    const titleEl = document.getElementById("pageTitle");
    const urlEl = document.getElementById("pageUrl");

    if (this.currentTab) {
      titleEl.textContent = this.currentTab.title || "Unknown";
      urlEl.textContent = this.currentTab.url || "";
    } else {
      titleEl.textContent = "No active tab";
      urlEl.textContent = "";
    }

    // Load page content
    await this.refreshContent();
  }

  async refreshContent() {
    const statusEl = document.getElementById("status");
    statusEl.textContent = "Loading page content...";
    statusEl.className = "status loading";

    try {
      const response = await chrome.runtime.sendMessage({
        action: "getPageContent",
      });

      if (response && response.success) {
        this.currentContent = response.content;
        const charCount = response.content.text
          ? response.content.text.length
          : 0;
        statusEl.textContent = `Content loaded (${charCount.toLocaleString()} chars)`;
        statusEl.className = "status success";
      } else {
        throw new Error(response?.error || "Failed to load content");
      }
    } catch (error) {
      statusEl.textContent = `Error: ${error.message}`;
      statusEl.className = "status error";
      console.error("Error loading content:", error);
    }
  }

  async askQuestion() {
    const input = document.getElementById("questionInput");
    const question = input.value.trim();

    if (!question) {
      this.showError("Please enter a question");
      return;
    }

    // Check authentication
    const { token } = await chrome.storage.local.get(["token"]);
    if (!token) {
      this.showError("Not authenticated. Please login in settings.");
      chrome.runtime.openOptionsPage();
      return;
    }

    if (!this.currentContent) {
      await this.refreshContent();
      if (!this.currentContent) {
        this.showError("Failed to load page content");
        return;
      }
    }

    // Add user message to UI and save
    const userMsgId = this.addMessage("user", question);
    await this.saveMessage("user", question, userMsgId);
    input.value = "";

    // Show loading
    const loadingId = this.addMessage("assistant", "Thinking...", true);

    try {
      const response = await chrome.runtime.sendMessage({
        action: "askQuestion",
        question: question,
        content: this.currentContent,
      });

      if (response && response.success) {
        const answer = response.answer;
        if (answer && answer.trim()) {
          this.updateMessage(loadingId, "assistant", answer);
          // Save assistant message
          await this.saveMessage("assistant", answer, loadingId);
        } else {
          const errorMsg = "Received empty response. Please try again or check the backend logs.";
          this.updateMessage(loadingId, "assistant", errorMsg);
          await this.saveMessage("assistant", errorMsg, loadingId);
        }
      } else {
        throw new Error(response?.error || "Failed to get answer");
      }
    } catch (error) {
      const errorMsg = `Error: ${error.message}`;
      this.updateMessage(loadingId, "assistant", errorMsg);
      await this.saveMessage("assistant", errorMsg, loadingId);
      console.error("Error asking question:", error);
      console.error("Full error details:", error);
    }
  }

  addMessage(role, content, isLoading = false) {
    return this.displayMessage(role, content, isLoading);
  }

  displayMessage(role, content, isLoading = false, messageId = null) {
    const messagesEl = document.getElementById("messages");
    const id = messageId || `msg_${Date.now()}`;
    const messageEl = document.createElement("div");
    messageEl.id = id;
    messageEl.className = `message ${role}`;

    if (isLoading) {
      messageEl.innerHTML = '<span class="loading-dots">' + content + "</span>";
      messageEl.classList.add("loading");
    } else {
      messageEl.innerHTML = content.replace(/\n/g, "<br>");
    }

    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return id;
  }

  updateMessage(messageId, role, content) {
    const messageEl = document.getElementById(messageId);
    if (messageEl) {
      messageEl.textContent = content;
      messageEl.classList.remove("loading");
      messageEl.innerHTML = content.replace(/\n/g, "<br>");
    }
  }

  showError(message) {
    const statusEl = document.getElementById("status");
    statusEl.textContent = message;
    statusEl.className = "status error";
    setTimeout(() => {
      statusEl.className = "status";
    }, 5000);
  }
}

// Initialize when popup opens
document.addEventListener("DOMContentLoaded", () => {
  new PopupController();
});
