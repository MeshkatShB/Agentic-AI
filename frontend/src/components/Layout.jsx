import React, { useState, useEffect } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessageSquare,
  Settings,
  Wrench,
  LogOut,
  Menu,
  X,
  Moon,
  Sun,
  User,
  ChevronLeft,
  ChevronRight,
  FileText,
  Globe,
  Server,
} from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useThemeStore } from "../stores/themeStore";
import clsx from "clsx";
import Logo from "./Logo";
import axios from "axios";

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const [sidebarWidth, setSidebarWidth] = useState(256); // Default width
  const [isDragging, setIsDragging] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentModel, setCurrentModel] = useState(null);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  useEffect(() => {
    // Load current model configuration
    const loadCurrentModel = async () => {
      try {
        const response = await axios.get("/settings/api-config");
        const apiConfig = response.data;
        const provider = apiConfig.llm_provider || "ollama";

        let modelName = "Unknown";
        if (provider === "ollama") {
          // For Ollama, get from user settings
          try {
            const userSettingsRes = await axios.get("/settings/user");
            modelName = userSettingsRes.data.model || "ollama";
          } catch {
            modelName = "ollama";
          }
        } else if (provider === "openai") {
          modelName = apiConfig.openai_model || "gpt-4o-mini";
        } else if (provider === "deepseek") {
          modelName = apiConfig.deepseek_model || "deepseek-chat";
        } else if (provider === "mistral") {
          modelName = apiConfig.mistral_model || "mistral-small";
        } else if (provider === "gemini") {
          modelName = apiConfig.gemini_model || "gemini-pro";
        }

        setCurrentModel({
          provider: provider.charAt(0).toUpperCase() + provider.slice(1),
          model: modelName,
        });
      } catch (error) {
        console.error("Failed to load current model:", error);
        setCurrentModel({ provider: "Ollama", model: "Unknown" });
      }
    };

    loadCurrentModel();
  }, []);

  const navItems = [
    { path: "/chat", icon: MessageSquare, label: "Chat" },
    { path: "/documents", icon: FileText, label: "Documents" },
    { path: "/tools", icon: Wrench, label: "Tools" },
    { path: "/mcp-servers", icon: Server, label: "MCP Servers" },
    { path: "/browser-use", icon: Globe, label: "Browser Automation" },
  ];

  const handleDragStart = (e) => {
    e.preventDefault();
    setIsDragging(true);
    document.addEventListener("mousemove", handleDrag);
    document.addEventListener("mouseup", handleDragEnd);
  };

  const handleDrag = (e) => {
    if (!isDragging) return;
    const newWidth = e.clientX;
    setSidebarWidth(Math.max(64, Math.min(400, newWidth))); // Min 64px, max 400px
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    document.removeEventListener("mousemove", handleDrag);
    document.removeEventListener("mouseup", handleDragEnd);
  };

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar */}
      <div
        className={clsx(
          "glass-dark border-r border-gray-700/50 flex flex-col transition-all duration-300 overflow-hidden",
          sidebarCollapsed ? "w-16" : `w-[${sidebarWidth}px]`
        )}
        style={{ width: sidebarCollapsed ? 64 : sidebarWidth }}
      >
        {/* Logo */}
        <div className="p-4 border-b border-gray-700/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0">
              <Logo className="w-6 h-6" color="white" />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-xl font-bold text-white">AI Agent</h1>
                <p className="text-xs text-gray-400">
                  Privacy First, Locality Second
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  "flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200",
                  isActive
                    ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                )}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && (
                  <span className="font-medium">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Settings link */}
        <Link
          to="/settings"
          className={clsx(
            "flex items-center space-x-3 px-3 py-2 rounded-lg transition-all duration-200",
            location.pathname.startsWith("/settings")
              ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
              : "text-gray-400 hover:bg-white/5 hover:text-white"
          )}
          title={sidebarCollapsed ? "Settings" : undefined}
        >
          <Settings className="w-5 h-5 flex-shrink-0" />
          {!sidebarCollapsed && <span className="font-medium">Settings</span>}
        </Link>

        {/* User section */}
        <div className="p-4 border-t border-gray-700/50">
          {!sidebarCollapsed ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">
                      {user?.username || "User"}
                    </p>
                    <p className="text-xs text-gray-400">
                      {user?.email || "user@example.com"}
                    </p>
                  </div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all duration-200"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all duration-200"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Resize handle */}
        {!sidebarCollapsed && (
          <div
            className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary-500/50 transition-colors"
            onMouseDown={handleDragStart}
          />
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-5 h-10 bg-gray-800 border border-gray-700/50 rounded-r-md flex items-center justify-center text-gray-400 hover:text-white transition-colors z-10"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 glass-dark border-b border-gray-700/50 flex items-center justify-end px-6 flex-shrink-0">
          <div className="flex items-center space-x-4">
            {/* Current Model Display */}
            {currentModel && (
              <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/30">
                <span className="text-xs font-medium text-blue-400">{currentModel.provider}</span>
                <span className="text-xs text-gray-400">/</span>
                <span className="text-xs text-blue-300">{currentModel.model}</span>
              </div>
            )}

            {/* Status indicator */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-green-500/20 border border-green-500/30">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs text-green-400">Online</span>
            </div>

            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              {theme === "dark" ? (
                <Sun className="w-5 h-5 text-yellow-400" />
              ) : (
                <Moon className="w-5 h-5 text-gray-600" />
              )}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
