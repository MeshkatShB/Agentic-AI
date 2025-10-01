import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Settings as SettingsIcon,
  User,
  Moon,
  Sun,
  Sliders,
  FolderOpen,
  Lock,
  Save,
  RefreshCw,
  Server,
  CheckCircle,
  XCircle,
  AlertCircle,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";
import { useThemeStore } from "../stores/themeStore";

const Settings = () => {
  const { user, updateProfile, changePassword } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  const [activeTab, setActiveTab] = useState("profile");
  const [systemInfo, setSystemInfo] = useState(null);
  const [userSettings, setUserSettings] = useState({
    theme: "dark",
    model: "qwen3:latest",
    temperature: 0.7,
    max_steps: 10,
    max_tokens: 2000,
    require_confirmation: true,
    reasoning_mode: "simple",
    agent_type: "simple",
  });
  const [pathSettings, setPathSettings] = useState({
    allowed_paths: [],
    blocked_paths: [],
  });
  const [passwordForm, setPasswordForm] = useState({
    oldPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState("checking");

  useEffect(() => {
    loadSettings();
    checkOllamaStatus();
  }, []);

  const loadSettings = async () => {
    try {
      // Load user settings
      const userSettingsRes = await axios.get("/settings/user");
      setUserSettings(userSettingsRes.data);

      // Load system info
      const systemRes = await axios.get("/settings/system");
      setSystemInfo(systemRes.data);

      // Load path settings
      const pathsRes = await axios.get("/settings/paths");
      setPathSettings(pathsRes.data);
    } catch (error) {
      toast.error("Failed to load settings");
    }
  };

  const checkOllamaStatus = async () => {
    try {
      const response = await axios.post("/settings/test-ollama");
      setOllamaStatus(response.data.status);
    } catch (error) {
      setOllamaStatus("error");
    }
  };

  const saveUserSettings = async () => {
    setIsLoading(true);
    try {
      await axios.put("/settings/user", userSettings);
      toast.success("Settings saved successfully");
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setIsLoading(false);
    }
  };

  const savePathSettings = async () => {
    setIsLoading(true);
    try {
      await axios.put("/settings/paths", pathSettings);
      toast.success("Path settings saved");
    } catch (error) {
      toast.error("Failed to save path settings");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (passwordForm.newPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    const success = await changePassword(
      passwordForm.oldPassword,
      passwordForm.newPassword
    );

    if (success) {
      setPasswordForm({
        oldPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "preferences", label: "Preferences", icon: Sliders },
    { id: "paths", label: "File Access", icon: FolderOpen },
    { id: "security", label: "Security", icon: Lock },
    { id: "system", label: "System", icon: Server },
  ];

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">
            Manage your profile, preferences, and system configuration
          </p>
        </div>

        {/* Tabs */}
        <div className="flex space-x-2 mb-6 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Profile tab */}
          {activeTab === "profile" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Profile Information
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={user?.username || ""}
                    disabled
                    className="input-glass text-white opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={user?.email || ""}
                    disabled
                    className="input-glass text-white opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={user?.full_name || ""}
                    disabled
                    className="input-glass text-white opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Account Created
                  </label>
                  <input
                    type="text"
                    value={
                      user?.created_at
                        ? new Date(user.created_at).toLocaleDateString()
                        : ""
                    }
                    disabled
                    className="input-glass text-white opacity-50"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Preferences tab */}
          {activeTab === "preferences" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                AI Preferences
              </h2>

              <div className="space-y-6">
                {/* Theme */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Theme
                  </label>
                  <button
                    onClick={toggleTheme}
                    className="flex items-center space-x-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-800/70 transition-colors"
                  >
                    {theme === "dark" ? (
                      <>
                        <Moon className="w-5 h-5 text-primary-400" />
                        <span className="text-white">Dark Mode</span>
                      </>
                    ) : (
                      <>
                        <Sun className="w-5 h-5 text-yellow-400" />
                        <span className="text-white">Light Mode</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Model selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    AI Model
                  </label>
                  <select
                    value={userSettings.model}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        model: e.target.value,
                      })
                    }
                    className="input-glass text-white"
                  >
                    {systemInfo?.models_available?.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Agent Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Agent Type
                  </label>
                  <select
                    value={userSettings.agent_type || "simple"}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        agent_type: e.target.value,
                      })
                    }
                    className="input-glass text-white"
                  >
                    <option value="simple">
                      Simple Agent - Basic responses
                    </option>
                    {/* Reasoning agent removed */}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">
                    LangGraph provides the most advanced reasoning and tool
                    integration
                  </p>
                </div>

                {/* Reasoning Mode (only show for reasoning agent) */}
                {userSettings.agent_type === "reasoning" && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Reasoning Mode
                    </label>
                    <select
                      value={userSettings.reasoning_mode || "chain_of_thought"}
                      onChange={(e) =>
                        setUserSettings({
                          ...userSettings,
                          reasoning_mode: e.target.value,
                        })
                      }
                      className="input-glass text-white"
                    >
                      <option value="simple">
                        Simple - Fast, direct responses
                      </option>
                      <option value="chain_of_thought">
                        Chain of Thought - Detailed reasoning process
                      </option>
                      <option value="react">
                        ReAct - Reason and Act iteratively
                      </option>
                    </select>
                    <p className="text-xs text-gray-400 mt-1">
                      Chain of Thought provides step-by-step reasoning but takes
                      longer
                    </p>
                  </div>
                )}

                {/* Temperature */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Temperature: {userSettings.temperature}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={userSettings.temperature}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        temperature: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>Precise</span>
                    <span>Creative</span>
                  </div>
                </div>

                {/* Max steps */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max Steps: {userSettings.max_steps}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    step="1"
                    value={userSettings.max_steps}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        max_steps: parseInt(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>

                {/* Max tokens */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max Tokens: {userSettings.max_tokens}
                  </label>
                  <input
                    type="range"
                    min="100"
                    max="4000"
                    step="100"
                    value={userSettings.max_tokens}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        max_tokens: parseInt(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>

                {/* Require confirmation */}
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="require_confirmation"
                    checked={userSettings.require_confirmation}
                    onChange={(e) =>
                      setUserSettings({
                        ...userSettings,
                        require_confirmation: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-primary-500 rounded"
                  />
                  <label
                    htmlFor="require_confirmation"
                    className="text-sm text-gray-300"
                  >
                    Require confirmation for tool execution
                  </label>
                </div>

                <button
                  onClick={saveUserSettings}
                  disabled={isLoading}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            </div>
          )}

          {/* File access tab */}
          {activeTab === "paths" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                File Access Paths
              </h2>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Allowed Paths
                  </label>
                  <textarea
                    value={pathSettings.allowed_paths.join("\n")}
                    onChange={(e) =>
                      setPathSettings({
                        ...pathSettings,
                        allowed_paths: e.target.value
                          .split("\n")
                          .filter((p) => p),
                      })
                    }
                    rows={4}
                    className="input-glass text-white font-mono text-sm"
                    placeholder="One path per line"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Blocked Paths
                  </label>
                  <textarea
                    value={pathSettings.blocked_paths.join("\n")}
                    onChange={(e) =>
                      setPathSettings({
                        ...pathSettings,
                        blocked_paths: e.target.value
                          .split("\n")
                          .filter((p) => p),
                      })
                    }
                    rows={4}
                    className="input-glass text-white font-mono text-sm"
                    placeholder="One path per line"
                  />
                </div>

                <button
                  onClick={savePathSettings}
                  disabled={isLoading}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? "Saving..." : "Save Path Settings"}
                </button>
              </div>
            </div>
          )}

          {/* Security tab */}
          {activeTab === "security" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Change Password
              </h2>

              <form
                onSubmit={handlePasswordChange}
                className="space-y-4 max-w-md"
              >
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Current Password
                  </label>
                  <input
                    type="password"
                    value={passwordForm.oldPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        oldPassword: e.target.value,
                      })
                    }
                    className="input-glass text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={passwordForm.newPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        newPassword: e.target.value,
                      })
                    }
                    className="input-glass text-white"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={passwordForm.confirmPassword}
                    onChange={(e) =>
                      setPasswordForm({
                        ...passwordForm,
                        confirmPassword: e.target.value,
                      })
                    }
                    className="input-glass text-white"
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                >
                  Change Password
                </button>
              </form>
            </div>
          )}

          {/* System tab */}
          {activeTab === "system" && (
            <div className="space-y-6">
              <div className="glass-dark rounded-xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4">
                  System Information
                </h2>

                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-300">Application</span>
                    <span className="text-white font-medium">
                      {systemInfo?.app_name} v{systemInfo?.app_version}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-300">Vector Store</span>
                    <span className="text-white font-medium">
                      {systemInfo?.vector_store}
                    </span>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-300">Ollama Status</span>
                    <div className="flex items-center space-x-2">
                      {ollamaStatus === "success" ? (
                        <>
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          <span className="text-green-400">Connected</span>
                        </>
                      ) : ollamaStatus === "error" ? (
                        <>
                          <XCircle className="w-4 h-4 text-red-400" />
                          <span className="text-red-400">Disconnected</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
                          <span className="text-yellow-400">Checking...</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-300">Ollama URL</span>
                    <span className="text-white font-mono text-sm">
                      {systemInfo?.ollama_url}
                    </span>
                  </div>

                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <span className="text-gray-300 block mb-2">
                      Available Models
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {systemInfo?.models_available?.map((model) => (
                        <span
                          key={model}
                          className="px-2 py-1 bg-primary-500/20 text-primary-400 rounded text-sm"
                        >
                          {model}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  onClick={checkOllamaStatus}
                  className="mt-4 px-4 py-2 bg-primary-500/20 text-primary-400 rounded-lg hover:bg-primary-500/30 transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <RefreshCw className="w-4 h-4" />
                    <span>Refresh Status</span>
                  </div>
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default Settings;
