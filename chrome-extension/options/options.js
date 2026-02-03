// options/options.js

class OptionsController {
  constructor() {
    this.init();
  }

  async init() {
    // Load saved settings
    await this.loadSettings();

    // Setup event listeners
    document
      .getElementById("saveButton")
      .addEventListener("click", () => this.saveSettings());
    document
      .getElementById("resetButton")
      .addEventListener("click", () => this.resetSettings());
    document
      .getElementById("loginButton")
      .addEventListener("click", () => this.login());
    document
      .getElementById("logoutButton")
      .addEventListener("click", () => this.logout());
    document
      .getElementById("testConnection")
      .addEventListener("click", () => this.testConnection());

    // Check if already logged in
    await this.checkAuthStatus();
  }

  async loadSettings() {
    const settings = await chrome.storage.local.get([
      "backendUrl",
      "autoCapture",
      "token",
      "username",
    ]);

    document.getElementById("backendUrl").value =
      settings.backendUrl || "http://localhost:8000";
    document.getElementById("autoCapture").checked =
      settings.autoCapture || false;

    if (settings.username) {
      document.getElementById("username").value = settings.username;
    }
  }

  async saveSettings() {
    const backendUrl = document.getElementById("backendUrl").value.trim();
    const autoCapture = document.getElementById("autoCapture").checked;

    if (!backendUrl) {
      this.showStatus("Please enter a backend URL", "error");
      return;
    }

    try {
      await chrome.storage.local.set({
        backendUrl: backendUrl,
        autoCapture: autoCapture,
      });

      this.showStatus("Settings saved successfully!", "success");
    } catch (error) {
      this.showStatus("Failed to save settings: " + error.message, "error");
    }
  }

  async resetSettings() {
    if (confirm("Reset all settings to defaults?")) {
      document.getElementById("backendUrl").value = "http://localhost:8000";
      document.getElementById("autoCapture").checked = false;
      document.getElementById("username").value = "";
      document.getElementById("password").value = "";

      await chrome.storage.local.set({
        backendUrl: "http://localhost:8000",
        autoCapture: false,
      });

      this.showStatus("Settings reset to defaults", "success");
    }
  }

  async login() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();
    const backendUrl =
      document.getElementById("backendUrl").value.trim() ||
      "http://localhost:8000";

    if (!username || !password) {
      this.showStatus("Please enter username and password", "error");
      return;
    }

    const loginButton = document.getElementById("loginButton");
    const authStatus = document.getElementById("authStatus");

    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";
    authStatus.textContent = "";

    try {
      const response = await fetch(`${backendUrl}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username: username,
          password: password,
        }),
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || "Login failed");
      }

      const data = await response.json();
      const token = data.access_token;

      if (!token) {
        throw new Error("No token received from server");
      }

      // Save token and username
      await chrome.storage.local.set({
        token: token,
        username: username,
        backendUrl: backendUrl,
      });

      this.showStatus("Login successful!", "success");
      await this.checkAuthStatus();

      // Clear password field
      document.getElementById("password").value = "";
    } catch (error) {
      this.showStatus("Login failed: " + error.message, "error");
      authStatus.textContent = "❌ Login failed";
      authStatus.className = "error";
    } finally {
      loginButton.disabled = false;
      loginButton.textContent = "Login";
    }
  }

  async logout() {
    await chrome.storage.local.remove(["token", "username"]);
    document.getElementById("password").value = "";
    this.showStatus("Logged out successfully", "success");
    await this.checkAuthStatus();
  }

  async checkAuthStatus() {
    const { token, username } = await chrome.storage.local.get([
      "token",
      "username",
    ]);
    const loginButton = document.getElementById("loginButton");
    const logoutButton = document.getElementById("logoutButton");
    const authStatus = document.getElementById("authStatus");

    if (token) {
      loginButton.style.display = "none";
      logoutButton.style.display = "inline-block";
      authStatus.textContent = `✅ Logged in as ${username || "user"}`;
      authStatus.className = "success";
    } else {
      loginButton.style.display = "inline-block";
      logoutButton.style.display = "none";
      authStatus.textContent = "Not logged in";
      authStatus.className = "";
    }
  }

  async testConnection() {
    const backendUrl =
      document.getElementById("backendUrl").value.trim() ||
      "http://localhost:8000";
    const statusEl = document.getElementById("connectionStatus");
    const testButton = document.getElementById("testConnection");

    testButton.disabled = true;
    testButton.textContent = "Testing...";
    statusEl.textContent = "";

    try {
      const response = await fetch(`${backendUrl}/health`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        statusEl.textContent = "✅ Connected";
        statusEl.className = "success";
        this.showStatus("Connection successful!", "success");
      } else {
        throw new Error(`Server returned ${response.status}`);
      }
    } catch (error) {
      statusEl.textContent = "❌ Connection failed";
      statusEl.className = "error";
      this.showStatus("Connection failed: " + error.message, "error");
    } finally {
      testButton.disabled = false;
      testButton.textContent = "Test Connection";
    }
  }

  showStatus(message, type = "info") {
    const statusEl = document.getElementById("statusMessage");
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.style.display = "block";

    setTimeout(() => {
      statusEl.style.display = "none";
    }, 5000);
  }
}

// Initialize when page loads
document.addEventListener("DOMContentLoaded", () => {
  new OptionsController();
});
