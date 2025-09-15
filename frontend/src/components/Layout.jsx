import React, { useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
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
  Shield,
} from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useThemeStore } from "../stores/themeStore";
import clsx from "clsx";

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = [
    { path: "/chat", icon: MessageSquare, label: "Chat" },
    { path: "/tools", icon: Wrench, label: "Tools" },
    { path: "/settings", icon: Settings, label: "Settings" },
  ];

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="w-64 glass-dark border-r border-gray-700/50 flex flex-col"
          >
            {/* Logo */}
            <div className="p-6 border-b border-gray-700/50">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">AI Agent</h1>
                  <p className="text-xs text-gray-400">Privacy First</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname.startsWith(item.path);

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={clsx(
                      "flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200",
                      isActive
                        ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
                        : "text-gray-400 hover:bg-white/5 hover:text-white"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* User section */}
            <div className="p-4 border-t border-gray-700/50">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center">
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
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 glass-dark border-b border-gray-700/50 flex items-center justify-between px-6">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5 text-gray-400" />
            ) : (
              <Menu className="w-5 h-5 text-gray-400" />
            )}
          </button>

          <div className="flex items-center space-x-4">
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

            {/* Status indicator */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-green-500/20 border border-green-500/30">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-xs text-green-400">Online</span>
            </div>
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
