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
  Key,
  Eye,
  EyeOff,
  Send,
  Copy,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";
import { useThemeStore } from "../stores/themeStore";

const Settings = () => {
  const { user, updateProfile, changePassword, refreshUserData } =
    useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  const [activeTab, setActiveTab] = useState("profile");
  const [activeSubTab, setActiveSubTab] = useState("preferences"); // "preferences" or "api-config"
  const [systemInfo, setSystemInfo] = useState(null);
  const [userSettings, setUserSettings] = useState({
    theme: "dark",
    model: "qwen3:latest",
    embedding_model: "Qwen/Qwen3-Embedding-0.6B",
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
  const [apiConfig, setApiConfig] = useState({
    llm_provider: "ollama",
    openai_api_key: "",
    openai_api_endpoint: "https://api.openai.com/v1",
    openai_model: "gpt-4o-mini",
    deepseek_api_key: "",
    deepseek_api_endpoint: "https://api.deepseek.com/v1",
    deepseek_model: "deepseek-chat",
    mistral_api_key: "",
    mistral_api_endpoint: "https://api.mistral.ai/v1",
    mistral_model: "mistral-small",
    gemini_api_key: "",
    gemini_api_endpoint: "https://generativelanguage.googleapis.com/v1",
    gemini_model: "gemini-pro",
  });
  const [showApiKeys, setShowApiKeys] = useState({
    openai: false,
    deepseek: false,
    mistral: false,
    gemini: false,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState("checking");
  const [availableModels, setAvailableModels] = useState({
    openai: [],
    deepseek: [],
    mistral: [],
    gemini: [],
  });
  const [modelLoading, setModelLoading] = useState({
    openai: false,
    deepseek: false,
    mistral: false,
    gemini: false,
  });
  const [telegramSettings, setTelegramSettings] = useState({
    enabled: false,
    has_token: false,
    pairing_code: null,
    is_paired: false,
    telegram_username: null,
    telegram_tools: null,
    telegram_use_mcp: true,
    telegram_mcp_server_ids: null,
    telegram_simple_agent: false,
    available_tools: [],
    mcp_servers: [],
  });

  useEffect(() => {
    loadSettings();
    loadApiConfig();
    checkOllamaStatus();
    loadTelegramSettings();
  }, []);

  // Fetch available models when API config changes or when provider is selected
  useEffect(() => {
    if (apiConfig.llm_provider && apiConfig.llm_provider !== "ollama") {
      fetchProviderModels(apiConfig.llm_provider);
    }
  }, [
    apiConfig.llm_provider,
    apiConfig.openai_api_key,
    apiConfig.deepseek_api_key,
    apiConfig.mistral_api_key,
    apiConfig.gemini_api_key,
  ]);

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

  const loadApiConfig = async () => {
    try {
      const response = await axios.get("/settings/api-config");
      setApiConfig(response.data);
    } catch (error) {
      console.error("Failed to load API config:", error);
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

  const loadTelegramSettings = async () => {
    try {
      const response = await axios.get("/settings/telegram");
      setTelegramSettings(response.data);
    } catch (error) {
      console.error("Failed to load Telegram settings:", error);
    }
  };

  const regeneratePairingCode = async () => {
    try {
      const response = await axios.post("/settings/telegram/pairing-code");
      setTelegramSettings((prev) => ({
        ...prev,
        pairing_code: response.data.pairing_code,
        is_paired: false,
        telegram_username: null,
      }));
      toast.success("New pairing code generated");
    } catch (error) {
      toast.error("Failed to generate pairing code");
    }
  };

  const copyPairingCode = () => {
    if (telegramSettings.pairing_code) {
      navigator.clipboard.writeText(telegramSettings.pairing_code);
      toast.success("Pairing code copied");
    }
  };

  const saveTelegramConfig = async () => {
    try {
      await axios.put("/settings/telegram/config", {
        telegram_tools: telegramSettings.telegram_tools,
        telegram_use_mcp: telegramSettings.telegram_use_mcp,
        telegram_mcp_server_ids: telegramSettings.telegram_mcp_server_ids,
        telegram_simple_agent: telegramSettings.telegram_simple_agent,
      });
      toast.success("Telegram chat environment saved");
      await loadTelegramSettings();
    } catch (error) {
      toast.error("Failed to save Telegram config");
    }
  };

  const toggleTelegramTool = (tool) => {
    const current =
      telegramSettings.telegram_tools || telegramSettings.available_tools || [];
    const next = current.includes(tool)
      ? current.filter((t) => t !== tool)
      : [...current, tool];
    setTelegramSettings((prev) => ({ ...prev, telegram_tools: next }));
  };

  const toggleTelegramMcpServer = (id) => {
    const allIds = (telegramSettings.mcp_servers || []).map((s) => s.id);
    const current = telegramSettings.telegram_mcp_server_ids;
    let next;
    if (current == null) {
      next = allIds.filter((i) => i !== id);
    } else {
      next = current.includes(id)
        ? current.filter((i) => i !== id)
        : [...current, id];
    }
    if (next.length === allIds.length) next = null;
    setTelegramSettings((prev) => ({ ...prev, telegram_mcp_server_ids: next }));
  };

  const fetchProviderModels = async (provider) => {
    // Check if API key is available for this provider
    const apiKeyField = `${provider}_api_key`;
    if (!apiConfig[apiKeyField]) {
      setAvailableModels((prev) => ({ ...prev, [provider]: [] }));
      return;
    }

    setModelLoading((prev) => ({ ...prev, [provider]: true }));
    try {
      const response = await axios.get(`/settings/api-models/${provider}`);
      if (response.data.models && response.data.models.length > 0) {
        setAvailableModels((prev) => ({
          ...prev,
          [provider]: response.data.models,
        }));
      } else {
        setAvailableModels((prev) => ({ ...prev, [provider]: [] }));
        if (response.data.error) {
          console.warn(
            `Failed to fetch ${provider} models:`,
            response.data.error
          );
        }
      }
    } catch (error) {
      console.error(`Error fetching ${provider} models:`, error);
      setAvailableModels((prev) => ({ ...prev, [provider]: [] }));
    } finally {
      setModelLoading((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const saveUserSettings = async () => {
    setIsLoading(true);
    try {
      await axios.put("/settings/user", userSettings);
      // Refresh user data to get updated preferences
      if (refreshUserData) {
        await refreshUserData();
      }
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

  const saveApiConfig = async () => {
    setIsLoading(true);
    try {
      // Only send API keys if they were actually changed (not masked values)
      const configToSave = { ...apiConfig };

      // If key starts with "***", it means it's masked from backend - don't send it
      if (configToSave.openai_api_key?.startsWith("***")) {
        delete configToSave.openai_api_key;
      }
      if (configToSave.deepseek_api_key?.startsWith("***")) {
        delete configToSave.deepseek_api_key;
      }
      if (configToSave.mistral_api_key?.startsWith("***")) {
        delete configToSave.mistral_api_key;
      }

      // If key is empty string, send null to clear it
      if (configToSave.openai_api_key === "") {
        configToSave.openai_api_key = null;
      }
      if (configToSave.deepseek_api_key === "") {
        configToSave.deepseek_api_key = null;
      }
      if (configToSave.mistral_api_key === "") {
        configToSave.mistral_api_key = null;
      }
      if (configToSave.gemini_api_key?.startsWith("***")) {
        delete configToSave.gemini_api_key;
      }
      if (configToSave.gemini_api_key === "") {
        configToSave.gemini_api_key = null;
      }

      await axios.put("/settings/api-config", configToSave);
      toast.success("API configuration saved successfully");
      // Reload to get masked keys
      await loadApiConfig();
      // Reset show keys
      setShowApiKeys({
        openai: false,
        deepseek: false,
        mistral: false,
        gemini: false,
      });
    } catch (error) {
      toast.error("Failed to save API configuration");
    } finally {
      setIsLoading(false);
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "preferences", label: "AI Settings", icon: Sliders },
    { id: "paths", label: "File Access", icon: FolderOpen },
    { id: "telegram", label: "Telegram", icon: Send },
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
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id === "preferences") {
                    setActiveSubTab("preferences"); // Reset to first sub-tab when switching to preferences tab
                  }
                }}
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

          {/* Preferences tab with sub-tabs */}
          {activeTab === "preferences" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                AI Settings
              </h2>

              {/* Sub-tabs */}
              <div className="flex space-x-2 mb-6 border-b border-gray-700/50">
                <button
                  onClick={() => setActiveSubTab("preferences")}
                  className={`px-4 py-2 text-sm font-medium transition-all duration-200 border-b-2 ${
                    activeSubTab === "preferences"
                      ? "border-primary-400 text-primary-400"
                      : "border-transparent text-gray-400 hover:text-white"
                  }`}
                >
                  AI Preferences
                </button>
                <button
                  onClick={() => setActiveSubTab("api-config")}
                  className={`px-4 py-2 text-sm font-medium transition-all duration-200 border-b-2 ${
                    activeSubTab === "api-config"
                      ? "border-primary-400 text-primary-400"
                      : "border-transparent text-gray-400 hover:text-white"
                  }`}
                >
                  API Configuration
                </button>
              </div>

              {/* Sub-tab content */}
              {activeSubTab === "api-config" && (
                <div className="space-y-6">
                  {/* Provider Selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      LLM Provider
                    </label>
                    <select
                      value={apiConfig.llm_provider}
                      onChange={(e) =>
                        setApiConfig({
                          ...apiConfig,
                          llm_provider: e.target.value,
                        })
                      }
                      className="input-glass text-white w-full"
                    >
                      <option value="ollama" className="bg-gray-800 text-white">
                        Ollama (Local - Default)
                      </option>
                      <option value="openai" className="bg-gray-800 text-white">
                        OpenAI
                      </option>
                      <option
                        value="deepseek"
                        className="bg-gray-800 text-white"
                      >
                        DeepSeek
                      </option>
                      <option
                        value="mistral"
                        className="bg-gray-800 text-white"
                      >
                        Mistral AI
                      </option>
                      <option value="gemini" className="bg-gray-800 text-white">
                        Google Gemini
                      </option>
                    </select>
                    <p className="text-xs text-gray-400 mt-1">
                      Select which provider to use for AI model inference
                    </p>
                  </div>

                  {/* OpenAI Configuration */}
                  {apiConfig.llm_provider === "openai" && (
                    <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                      <h3 className="text-lg font-semibold text-white">
                        OpenAI Configuration
                      </h3>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type={showApiKeys.openai ? "text" : "password"}
                            value={
                              apiConfig.openai_api_key?.startsWith("***")
                                ? ""
                                : apiConfig.openai_api_key || ""
                            }
                            onChange={(e) =>
                              setApiConfig({
                                ...apiConfig,
                                openai_api_key: e.target.value,
                              })
                            }
                            placeholder={
                              apiConfig.openai_api_key?.startsWith("***")
                                ? "API key is set (enter new key to change)"
                                : "Enter OpenAI API key"
                            }
                            className="input-glass text-white w-full pr-10"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowApiKeys({
                                ...showApiKeys,
                                openai: !showApiKeys.openai,
                              })
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                          >
                            {showApiKeys.openai ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Endpoint
                        </label>
                        <input
                          type="text"
                          value={apiConfig.openai_api_endpoint}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              openai_api_endpoint: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          placeholder="https://api.openai.com/v1"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-gray-300">
                            Model
                          </label>
                          <button
                            type="button"
                            onClick={() => fetchProviderModels("openai")}
                            disabled={
                              modelLoading.openai || !apiConfig.openai_api_key
                            }
                            className="text-xs text-primary-400 hover:text-primary-300 disabled:text-gray-500 disabled:cursor-not-allowed"
                            title="Refresh available models"
                          >
                            {modelLoading.openai ? "Loading..." : "🔄 Refresh"}
                          </button>
                        </div>
                        <select
                          value={apiConfig.openai_model}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              openai_model: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          disabled={modelLoading.openai}
                        >
                          {availableModels.openai.length > 0 ? (
                            availableModels.openai.map((model) => (
                              <option
                                key={model}
                                value={model}
                                className="bg-gray-800 text-white"
                              >
                                {model}
                              </option>
                            ))
                          ) : (
                            <>
                              <option
                                value="gpt-4o-mini"
                                className="bg-gray-800 text-white"
                              >
                                gpt-4o-mini (default)
                              </option>
                              <option
                                value="gpt-4o"
                                className="bg-gray-800 text-white"
                              >
                                gpt-4o
                              </option>
                              <option
                                value="gpt-4-turbo"
                                className="bg-gray-800 text-white"
                              >
                                gpt-4-turbo
                              </option>
                              <option
                                value="gpt-4"
                                className="bg-gray-800 text-white"
                              >
                                gpt-4
                              </option>
                              <option
                                value="gpt-3.5-turbo"
                                className="bg-gray-800 text-white"
                              >
                                gpt-3.5-turbo
                              </option>
                            </>
                          )}
                        </select>
                        {availableModels.openai.length === 0 &&
                          apiConfig.openai_api_key && (
                            <p className="text-xs text-gray-400 mt-1">
                              Click "Refresh" to load available models from
                              OpenAI
                            </p>
                          )}
                      </div>
                    </div>
                  )}

                  {/* DeepSeek Configuration */}
                  {apiConfig.llm_provider === "deepseek" && (
                    <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                      <h3 className="text-lg font-semibold text-white">
                        DeepSeek Configuration
                      </h3>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type={showApiKeys.deepseek ? "text" : "password"}
                            value={
                              apiConfig.deepseek_api_key?.startsWith("***")
                                ? ""
                                : apiConfig.deepseek_api_key || ""
                            }
                            onChange={(e) =>
                              setApiConfig({
                                ...apiConfig,
                                deepseek_api_key: e.target.value,
                              })
                            }
                            placeholder={
                              apiConfig.deepseek_api_key?.startsWith("***")
                                ? "API key is set (enter new key to change)"
                                : "Enter DeepSeek API key"
                            }
                            className="input-glass text-white w-full pr-10"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowApiKeys({
                                ...showApiKeys,
                                deepseek: !showApiKeys.deepseek,
                              })
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                          >
                            {showApiKeys.deepseek ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Endpoint
                        </label>
                        <input
                          type="text"
                          value={apiConfig.deepseek_api_endpoint}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              deepseek_api_endpoint: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          placeholder="https://api.deepseek.com/v1"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-gray-300">
                            Model
                          </label>
                          <button
                            type="button"
                            onClick={() => fetchProviderModels("deepseek")}
                            disabled={
                              modelLoading.deepseek ||
                              !apiConfig.deepseek_api_key
                            }
                            className="text-xs text-primary-400 hover:text-primary-300 disabled:text-gray-500 disabled:cursor-not-allowed"
                            title="Refresh available models"
                          >
                            {modelLoading.deepseek
                              ? "Loading..."
                              : "🔄 Refresh"}
                          </button>
                        </div>
                        <select
                          value={apiConfig.deepseek_model}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              deepseek_model: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          disabled={modelLoading.deepseek}
                        >
                          {availableModels.deepseek.length > 0 ? (
                            availableModels.deepseek.map((model) => (
                              <option
                                key={model}
                                value={model}
                                className="bg-gray-800 text-white"
                              >
                                {model}
                              </option>
                            ))
                          ) : (
                            <>
                              <option
                                value="deepseek-chat"
                                className="bg-gray-800 text-white"
                              >
                                deepseek-chat (default)
                              </option>
                              <option
                                value="deepseek-coder"
                                className="bg-gray-800 text-white"
                              >
                                deepseek-coder
                              </option>
                            </>
                          )}
                        </select>
                        {availableModels.deepseek.length === 0 &&
                          apiConfig.deepseek_api_key && (
                            <p className="text-xs text-gray-400 mt-1">
                              Click "Refresh" to load available models from
                              DeepSeek
                            </p>
                          )}
                      </div>
                    </div>
                  )}

                  {/* Mistral Configuration */}
                  {apiConfig.llm_provider === "mistral" && (
                    <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                      <h3 className="text-lg font-semibold text-white">
                        Mistral AI Configuration
                      </h3>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type={showApiKeys.mistral ? "text" : "password"}
                            value={
                              apiConfig.mistral_api_key?.startsWith("***")
                                ? ""
                                : apiConfig.mistral_api_key || ""
                            }
                            onChange={(e) =>
                              setApiConfig({
                                ...apiConfig,
                                mistral_api_key: e.target.value,
                              })
                            }
                            placeholder={
                              apiConfig.mistral_api_key?.startsWith("***")
                                ? "API key is set (enter new key to change)"
                                : "Enter Mistral API key"
                            }
                            className="input-glass text-white w-full pr-10"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowApiKeys({
                                ...showApiKeys,
                                mistral: !showApiKeys.mistral,
                              })
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                          >
                            {showApiKeys.mistral ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Endpoint
                        </label>
                        <input
                          type="text"
                          value={apiConfig.mistral_api_endpoint}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              mistral_api_endpoint: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          placeholder="https://api.mistral.ai/v1"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-gray-300">
                            Model
                          </label>
                          <button
                            type="button"
                            onClick={() => fetchProviderModels("mistral")}
                            disabled={
                              modelLoading.mistral || !apiConfig.mistral_api_key
                            }
                            className="text-xs text-primary-400 hover:text-primary-300 disabled:text-gray-500 disabled:cursor-not-allowed"
                            title="Refresh available models"
                          >
                            {modelLoading.mistral ? "Loading..." : "🔄 Refresh"}
                          </button>
                        </div>
                        <select
                          value={apiConfig.mistral_model}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              mistral_model: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          disabled={modelLoading.mistral}
                        >
                          {availableModels.mistral.length > 0 ? (
                            availableModels.mistral.map((model) => (
                              <option
                                key={model}
                                value={model}
                                className="bg-gray-800 text-white"
                              >
                                {model}
                              </option>
                            ))
                          ) : (
                            <>
                              <option
                                value="mistral-small"
                                className="bg-gray-800 text-white"
                              >
                                mistral-small (default)
                              </option>
                              <option
                                value="mistral-medium"
                                className="bg-gray-800 text-white"
                              >
                                mistral-medium
                              </option>
                              <option
                                value="mistral-large"
                                className="bg-gray-800 text-white"
                              >
                                mistral-large
                              </option>
                              <option
                                value="mistral-tiny"
                                className="bg-gray-800 text-white"
                              >
                                mistral-tiny
                              </option>
                            </>
                          )}
                        </select>
                        {availableModels.mistral.length === 0 &&
                          apiConfig.mistral_api_key && (
                            <p className="text-xs text-gray-400 mt-1">
                              Click "Refresh" to load available models from
                              Mistral
                            </p>
                          )}
                      </div>
                    </div>
                  )}

                  {/* Gemini Configuration */}
                  {apiConfig.llm_provider === "gemini" && (
                    <div className="space-y-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/50">
                      <h3 className="text-lg font-semibold text-white">
                        Google Gemini Configuration
                      </h3>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type={showApiKeys.gemini ? "text" : "password"}
                            value={
                              apiConfig.gemini_api_key?.startsWith("***")
                                ? ""
                                : apiConfig.gemini_api_key || ""
                            }
                            onChange={(e) =>
                              setApiConfig({
                                ...apiConfig,
                                gemini_api_key: e.target.value,
                              })
                            }
                            placeholder={
                              apiConfig.gemini_api_key?.startsWith("***")
                                ? "API key is set (enter new key to change)"
                                : "Enter Gemini API key"
                            }
                            className="input-glass text-white w-full pr-10"
                          />
                          <button
                            type="button"
                            onClick={() =>
                              setShowApiKeys({
                                ...showApiKeys,
                                gemini: !showApiKeys.gemini,
                              })
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                          >
                            {showApiKeys.gemini ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          API Endpoint
                        </label>
                        <input
                          type="text"
                          value={apiConfig.gemini_api_endpoint}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              gemini_api_endpoint: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          placeholder="https://generativelanguage.googleapis.com/v1"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-gray-300">
                            Model
                          </label>
                          <button
                            type="button"
                            onClick={() => fetchProviderModels("gemini")}
                            disabled={
                              modelLoading.gemini || !apiConfig.gemini_api_key
                            }
                            className="text-xs text-primary-400 hover:text-primary-300 disabled:text-gray-500 disabled:cursor-not-allowed"
                            title="Refresh available models"
                          >
                            {modelLoading.gemini ? "Loading..." : "🔄 Refresh"}
                          </button>
                        </div>
                        <select
                          value={apiConfig.gemini_model}
                          onChange={(e) =>
                            setApiConfig({
                              ...apiConfig,
                              gemini_model: e.target.value,
                            })
                          }
                          className="input-glass text-white w-full"
                          disabled={modelLoading.gemini}
                        >
                          {availableModels.gemini.length > 0 ? (
                            availableModels.gemini.map((model) => (
                              <option
                                key={model}
                                value={model}
                                className="bg-gray-800 text-white"
                              >
                                {model}
                              </option>
                            ))
                          ) : (
                            <>
                              <option
                                value="gemini-pro"
                                className="bg-gray-800 text-white"
                              >
                                gemini-pro (default)
                              </option>
                              <option
                                value="gemini-pro-vision"
                                className="bg-gray-800 text-white"
                              >
                                gemini-pro-vision
                              </option>
                              <option
                                value="gemini-1.5-pro"
                                className="bg-gray-800 text-white"
                              >
                                gemini-1.5-pro
                              </option>
                              <option
                                value="gemini-1.5-flash"
                                className="bg-gray-800 text-white"
                              >
                                gemini-1.5-flash
                              </option>
                            </>
                          )}
                        </select>
                        {availableModels.gemini.length === 0 &&
                          apiConfig.gemini_api_key && (
                            <p className="text-xs text-gray-400 mt-1">
                              Click "Refresh" to load available models from
                              Gemini
                            </p>
                          )}
                      </div>
                    </div>
                  )}

                  {/* Ollama Info */}
                  {apiConfig.llm_provider === "ollama" && (
                    <div className="p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
                      <p className="text-sm text-blue-400">
                        Using local Ollama models. Configure Ollama settings in
                        the System tab.
                      </p>
                    </div>
                  )}

                  <button
                    onClick={saveApiConfig}
                    disabled={isLoading}
                    className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? "Saving..." : "Save API Configuration"}
                  </button>
                </div>
              )}

              {/* AI Preferences sub-tab */}
              {activeSubTab === "preferences" && (
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

                  {/* AI Model selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      AI Model
                    </label>
                    <div className="flex space-x-2">
                      <select
                        value={userSettings.model}
                        onChange={(e) =>
                          setUserSettings({
                            ...userSettings,
                            model: e.target.value,
                          })
                        }
                        className="input-glass text-white flex-1"
                      >
                        {systemInfo?.models_available?.map((model) => (
                          <option
                            key={model}
                            value={model}
                            className="bg-gray-800 text-white"
                          >
                            {model}
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        value={userSettings.model}
                        onChange={(e) =>
                          setUserSettings({
                            ...userSettings,
                            model: e.target.value,
                          })
                        }
                        placeholder="Or type custom model"
                        className="input-glass text-white flex-1"
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Select from available models or type a custom model name
                    </p>
                  </div>

                  {/* Embedding Model selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Embedding Model
                    </label>
                    <div className="space-y-2">
                      <select
                        value={
                          userSettings.embedding_model ||
                          "Qwen/Qwen3-Embedding-0.6B"
                        }
                        onChange={(e) => {
                          const value = e.target.value;
                          setUserSettings({
                            ...userSettings,
                            embedding_model: value === "custom" ? "" : value,
                          });
                        }}
                        className="input-glass text-white w-full"
                      >
                        <option
                          value="Qwen/Qwen3-Embedding-0.6B"
                          className="bg-gray-800 text-white"
                        >
                          Qwen/Qwen3-Embedding-0.6B (Default - Best for Persian)
                        </option>
                        <option
                          value="sentence-transformers/all-MiniLM-L6-v2"
                          className="bg-gray-800 text-white"
                        >
                          all-MiniLM-L6-v2 (Fast, English-focused)
                        </option>
                        <option
                          value="sentence-transformers/all-mpnet-base-v2"
                          className="bg-gray-800 text-white"
                        >
                          all-mpnet-base-v2 (High quality, English)
                        </option>
                        <option
                          value="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                          className="bg-gray-800 text-white"
                        >
                          paraphrase-multilingual-MiniLM-L12-v2 (Multilingual)
                        </option>
                        <option
                          value="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                          className="bg-gray-800 text-white"
                        >
                          paraphrase-multilingual-mpnet-base-v2 (Multilingual,
                          High quality)
                        </option>
                        <option
                          value="custom"
                          className="bg-gray-800 text-white"
                        >
                          Custom Model...
                        </option>
                      </select>
                      {userSettings.embedding_model === "" ||
                      ![
                        "Qwen/Qwen3-Embedding-0.6B",
                        "sentence-transformers/all-MiniLM-L6-v2",
                        "sentence-transformers/all-mpnet-base-v2",
                        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                      ].includes(userSettings.embedding_model || "") ? (
                        <input
                          type="text"
                          value={userSettings.embedding_model || ""}
                          onChange={(e) =>
                            setUserSettings({
                              ...userSettings,
                              embedding_model: e.target.value,
                            })
                          }
                          placeholder="Enter embedding model name (e.g., sentence-transformers/model-name)"
                          className="input-glass text-white w-full"
                        />
                      ) : null}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Model used for document embeddings. Changing this requires
                      re-indexing documents.
                    </p>
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
                      <option value="simple" className="bg-gray-800 text-white">
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
                        value={
                          userSettings.reasoning_mode || "chain_of_thought"
                        }
                        onChange={(e) =>
                          setUserSettings({
                            ...userSettings,
                            reasoning_mode: e.target.value,
                          })
                        }
                        className="input-glass text-white"
                      >
                        <option
                          value="simple"
                          className="bg-gray-800 text-white"
                        >
                          Simple - Fast, direct responses
                        </option>
                        <option
                          value="chain_of_thought"
                          className="bg-gray-800 text-white"
                        >
                          Chain of Thought - Detailed reasoning process
                        </option>
                        <option
                          value="react"
                          className="bg-gray-800 text-white"
                        >
                          ReAct - Reason and Act iteratively
                        </option>
                      </select>
                      <p className="text-xs text-gray-400 mt-1">
                        Chain of Thought provides step-by-step reasoning but
                        takes longer
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
              )}
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

          {/* Telegram tab */}
          {activeTab === "telegram" && (
            <div className="glass-dark rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Telegram Bot
              </h2>
              <p className="text-gray-400 mb-6">
                Pair your Telegram account with this app. Only registered users
                can use the bot after pairing with a code.
              </p>

              {!telegramSettings.has_token ? (
                <div className="p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
                  <p className="text-amber-400 text-sm">
                    Telegram bot is not configured. Set{" "}
                    <code className="bg-black/30 px-1 rounded">
                      TELEGRAM_BOT_TOKEN
                    </code>{" "}
                    and{" "}
                    <code className="bg-black/30 px-1 rounded">
                      ENABLE_TELEGRAM_BOT=true
                    </code>{" "}
                    in the server environment (e.g.{" "}
                    <code className="bg-black/30 px-1 rounded">.env</code>) to
                    enable it. Create a bot via @BotFather on Telegram to get a
                    token.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {telegramSettings.is_paired ? (
                    <div className="flex items-center space-x-2 p-3 bg-green-500/10 rounded-lg border border-green-500/30">
                      <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                      <span className="text-green-400">
                        Paired with Telegram
                        {telegramSettings.telegram_username
                          ? ` as @${telegramSettings.telegram_username}`
                          : ""}
                        . You can message the bot to chat with the AI.
                      </span>
                    </div>
                  ) : (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Your pairing code
                        </label>
                        <div className="flex items-center space-x-2">
                          <code className="flex-1 px-4 py-3 bg-gray-800/70 text-primary-400 font-mono text-lg tracking-widest rounded-lg border border-gray-700">
                            {telegramSettings.pairing_code || "—"}
                          </code>
                          <button
                            type="button"
                            onClick={copyPairingCode}
                            disabled={!telegramSettings.pairing_code}
                            className="p-3 rounded-lg bg-gray-800/70 hover:bg-gray-700/70 text-gray-300 hover:text-white border border-gray-700 disabled:opacity-50"
                            title="Copy code"
                          >
                            <Copy className="w-5 h-5" />
                          </button>
                          <button
                            type="button"
                            onClick={regeneratePairingCode}
                            className="px-4 py-2 rounded-lg bg-primary-500/20 text-primary-400 hover:bg-primary-500/30 border border-primary-500/30"
                          >
                            Regenerate
                          </button>
                        </div>
                      </div>
                      <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700/50 text-sm text-gray-300 space-y-2">
                        <p className="font-medium text-white">How to pair</p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>
                            Open Telegram and find your bot (from the token
                            creator).
                          </li>
                          <li>
                            Send:{" "}
                            <code className="bg-black/30 px-1 rounded">
                              /start pair YOUR_CODE
                            </code>{" "}
                            (replace YOUR_CODE with the code above).
                          </li>
                          <li>
                            Or send:{" "}
                            <code className="bg-black/30 px-1 rounded">
                              /pair YOUR_CODE
                            </code>
                            .
                          </li>
                          <li>
                            After pairing, send any message to chat with the AI.
                          </li>
                        </ol>
                      </div>
                    </>
                  )}
                  {/* Chat environment: tools and MCP */}
                  <div className="border-t border-gray-700/50 pt-6 mt-6">
                    <h3 className="text-lg font-semibold text-white mb-3">
                      Telegram chat environment
                    </h3>
                    <p className="text-gray-400 text-sm mb-4">
                      Choose which tools and MCP servers the bot can use. You
                      can turn off MCP or use a simpler agent if you get model
                      errors.
                    </p>

                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium text-gray-300">
                            Tools for Telegram
                          </label>
                          <label className="flex items-center gap-2 text-sm text-gray-400">
                            <input
                              type="checkbox"
                              checked={
                                telegramSettings.telegram_tools === null ||
                                telegramSettings.telegram_tools === undefined
                              }
                              onChange={(e) =>
                                setTelegramSettings((prev) => ({
                                  ...prev,
                                  telegram_tools: e.target.checked
                                    ? null
                                    : prev.available_tools || [],
                                }))
                              }
                              className="rounded text-primary-500"
                            />
                            Use same as web
                          </label>
                        </div>
                        {telegramSettings.telegram_tools !== null &&
                          telegramSettings.telegram_tools !== undefined && (
                            <div className="flex flex-wrap gap-2 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 max-h-32 overflow-y-auto">
                              {(telegramSettings.available_tools || []).map(
                                (tool) => (
                                  <label
                                    key={tool}
                                    className="flex items-center gap-1.5 text-sm text-gray-300 cursor-pointer"
                                  >
                                    <input
                                      type="checkbox"
                                      checked={(
                                        telegramSettings.telegram_tools || []
                                      ).includes(tool)}
                                      onChange={() => toggleTelegramTool(tool)}
                                      className="rounded text-primary-500"
                                    />
                                    {tool}
                                  </label>
                                )
                              )}
                            </div>
                          )}
                      </div>

                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="telegram_use_mcp"
                          checked={telegramSettings.telegram_use_mcp}
                          onChange={(e) =>
                            setTelegramSettings((prev) => ({
                              ...prev,
                              telegram_use_mcp: e.target.checked,
                            }))
                          }
                          className="w-4 h-4 text-primary-500 rounded"
                        />
                        <label
                          htmlFor="telegram_use_mcp"
                          className="text-sm text-gray-300"
                        >
                          Use MCP servers in Telegram
                        </label>
                      </div>
                      {telegramSettings.telegram_use_mcp &&
                        (telegramSettings.mcp_servers || []).length > 0 && (
                          <div className="pl-6">
                            <p className="text-xs text-gray-400 mb-2">
                              Select servers (leave all = use all)
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {(telegramSettings.mcp_servers || []).map((s) => (
                                <label
                                  key={s.id}
                                  className="flex items-center gap-1.5 text-sm text-gray-300 cursor-pointer"
                                >
                                  <input
                                    type="checkbox"
                                    checked={
                                      telegramSettings.telegram_mcp_server_ids ==
                                      null
                                        ? true
                                        : (
                                            telegramSettings.telegram_mcp_server_ids ||
                                            []
                                          ).includes(s.id)
                                    }
                                    onChange={() =>
                                      toggleTelegramMcpServer(s.id)
                                    }
                                    className="rounded text-primary-500"
                                  />
                                  {s.name}
                                </label>
                              ))}
                            </div>
                          </div>
                        )}

                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="telegram_simple_agent"
                          checked={telegramSettings.telegram_simple_agent}
                          onChange={(e) =>
                            setTelegramSettings((prev) => ({
                              ...prev,
                              telegram_simple_agent: e.target.checked,
                            }))
                          }
                          className="w-4 h-4 text-primary-500 rounded"
                        />
                        <label
                          htmlFor="telegram_simple_agent"
                          className="text-sm text-gray-300"
                        >
                          Use simple agent (recommended if you get
                          &quot;Expected dict response&quot; or model errors)
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={saveTelegramConfig}
                        className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                      >
                        Save Telegram environment
                      </button>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={loadTelegramSettings}
                    className="px-4 py-2 rounded-lg bg-gray-800/50 text-gray-300 hover:text-white border border-gray-700"
                  >
                    Refresh status
                  </button>
                </div>
              )}
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
