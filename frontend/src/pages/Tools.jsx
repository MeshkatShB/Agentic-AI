import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Wrench,
  Shield,
  FileText,
  Globe,
  Database,
  Calculator,
  Search,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info,
  Plus,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";
import { useNavigate } from "react-router-dom";
import { Pencil } from "lucide-react";

const Tools = () => {
  const navigate = useNavigate();
  const { user, refreshUserData } = useAuthStore((state) => ({
    user: state.user,
    refreshUserData: state.refreshUserData,
  }));
  const [tools, setTools] = useState([]);
  const [customTools, setCustomTools] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCustomTools, setIsLoadingCustomTools] = useState(true);
  const [togglingTool, setTogglingTool] = useState(null);
  const [deletingToolId, setDeletingToolId] = useState(null);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [localAllowedTools, setLocalAllowedTools] = useState(
    user?.allowed_tools || []
  );

  // Use local state that we control directly
  const userAllowedTools = localAllowedTools;

  console.log("Tools component render:", {
    user: user?.username,
    userAllowedTools,
    authStoreAllowedTools: user?.allowed_tools,
    userObjectId: user?.id,
    userObjectRef: user,
    forceUpdate,
    timestamp: Date.now(),
  });

  useEffect(() => {
    loadTools();
    loadPermissions();
    loadCustomTools();
  }, []);

  // Sync local state with auth store
  useEffect(() => {
    if (user?.allowed_tools) {
      console.log(
        "Syncing localAllowedTools with auth store:",
        user.allowed_tools
      );
      setLocalAllowedTools([...user.allowed_tools]);
    }
  }, [user?.allowed_tools]);

  const loadTools = async () => {
    try {
      const response = await axios.get("/tools/available");
      setTools(response.data);
    } catch (error) {
      console.error("Failed to load tools:", error);
      toast.error("Failed to load tools");
    } finally {
      setIsLoading(false);
    }
  };

  const loadPermissions = async () => {
    try {
      const response = await axios.get("/tools/permissions/list");
      setPermissions(response.data);
    } catch (error) {
      console.error("Failed to load permissions:", error);
    }
  };

  const loadCustomTools = async () => {
    try {
      setIsLoadingCustomTools(true);
      const response = await axios.get("/custom-tools/");
      setCustomTools(response.data);
    } catch (error) {
      console.error("Failed to load custom tools:", error);
      toast.error("Failed to load custom tools");
    } finally {
      setIsLoadingCustomTools(false);
    }
  };

  const deleteCustomTool = async (tool) => {
    const confirmed = window.confirm(
      `Delete custom tool "${tool.display_name}"? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      setDeletingToolId(tool.id);
      await axios.delete(`/custom-tools/${tool.id}`);
      setCustomTools((prev) => prev.filter((t) => t.id !== tool.id));
      setLocalAllowedTools((prev) => prev.filter((n) => n !== tool.name));
      await refreshUserData();
      toast.success(`Deleted ${tool.display_name}`);
    } catch (error) {
      console.error("Failed to delete custom tool:", error);
      toast.error(error.response?.data?.detail || "Failed to delete tool");
    } finally {
      setDeletingToolId(null);
    }
  };

  const toggleTool = async (
    toolName,
    currentlyEnabled,
    isCustomTool = false
  ) => {
    console.log("toggleTool called:", {
      toolName,
      currentlyEnabled,
      userAllowedTools,
      isCustomTool,
    });
    setTogglingTool(toolName);

    // Update local state immediately for responsive UI
    const newAllowedTools = currentlyEnabled
      ? localAllowedTools.filter((tool) => tool !== toolName)
      : [...localAllowedTools, toolName];

    console.log("Updating local state immediately:", {
      from: localAllowedTools,
      to: newAllowedTools,
    });

    setLocalAllowedTools(newAllowedTools);

    try {
      let response;

      if (isCustomTool) {
        // For custom tools, we need to add/remove them from user's allowed_tools directly
        // Since custom tools are user-created, they should be automatically available to the creator
        // We'll update the user's allowed_tools list directly through the auth API
        response = await axios.put("/auth/me", {
          allowed_tools: newAllowedTools,
        });
        console.log(
          "Custom tool permission updated via auth API:",
          response.data
        );
      } else {
        // For built-in tools, use the existing grant-permission endpoint
        response = await axios.post("/tools/grant-permission", {
          tool_name: toolName,
          grant: !currentlyEnabled,
        });
        console.log("Built-in tool permission updated:", response.data);
      }

      // Update auth store to persist the change
      await refreshUserData();

      toast.success(
        currentlyEnabled ? `Disabled ${toolName}` : `Enabled ${toolName}`
      );
    } catch (error) {
      console.error("Tool permission update error:", error);
      // Revert local state on error
      setLocalAllowedTools(user?.allowed_tools || []);
      toast.error("Failed to update tool permission");
    } finally {
      setTogglingTool(null);
    }
  };

  // refreshUserData is now available from useAuthStore hook

  const getToolIcon = (toolName) => {
    if (toolName.includes("file") || toolName.includes("read")) {
      return <FileText className="w-5 h-5" />;
    }
    if (toolName.includes("web") || toolName.includes("search")) {
      return <Globe className="w-5 h-5" />;
    }
    if (toolName.includes("database") || toolName.includes("query")) {
      return <Database className="w-5 h-5" />;
    }
    if (toolName.includes("calculator")) {
      return <Calculator className="w-5 h-5" />;
    }
    return <Wrench className="w-5 h-5" />;
  };

  const getPermissionColor = (permission) => {
    switch (permission) {
      case "safe":
        return "text-green-400 bg-green-500/20 border-green-500/30";
      case "read_files":
        return "text-blue-400 bg-blue-500/20 border-blue-500/30";
      case "write_files":
        return "text-yellow-400 bg-yellow-500/20 border-yellow-500/30";
      case "network":
        return "text-purple-400 bg-purple-500/20 border-purple-500/30";
      case "database_read":
        return "text-cyan-400 bg-cyan-500/20 border-cyan-500/30";
      case "database_write":
        return "text-orange-400 bg-orange-500/20 border-orange-500/30";
      case "system":
        return "text-red-400 bg-red-500/20 border-red-500/30";
      default:
        return "text-gray-400 bg-gray-500/20 border-gray-500/30";
    }
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              Tools & Permissions
            </h1>
            <p className="text-gray-400">
              Manage which tools the AI agent can use and their permissions
            </p>
          </div>

          <div className="flex space-x-3">
            {/* Create Custom Tool button */}
            <button
              onClick={() => navigate("/add-tool")}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 transition-all duration-200 flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm font-medium">Create Tool</span>
            </button>

            {/* Debug refresh button */}
            <button
              onClick={async () => {
                console.log("Manual refresh clicked");
                const updatedUser = await refreshUserData();
                if (updatedUser?.allowed_tools) {
                  setLocalAllowedTools([...updatedUser.allowed_tools]);
                }
                await loadCustomTools(); // Also refresh custom tools
                setForceUpdate((prev) => prev + 1);
                toast.success("Data refreshed");
              }}
              className="px-3 py-1.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-all duration-200"
            >
              <div className="flex items-center space-x-2">
                <Search className="w-4 h-4" />
                <span className="text-sm">Refresh</span>
              </div>
            </button>
          </div>
        </div>

        {/* Available tools */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-dark rounded-xl p-6"
        >
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
            <Wrench className="w-5 h-5 mr-2 text-primary-400" />
            Available Tools
          </h2>

          {isLoading ? (
            <div className="text-center py-8">
              <div className="loading-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {tools.map((tool) => {
                const isEnabled = userAllowedTools.includes(tool.name);
                console.log(
                  `Tool ${tool.name}: isEnabled=${isEnabled}, userAllowedTools:`,
                  userAllowedTools,
                  `user.allowed_tools:`,
                  user?.allowed_tools
                );

                return (
                  <motion.div
                    key={`${tool.name}-${forceUpdate}-${isEnabled}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    whileHover={{ x: 4 }}
                    className="p-4 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:bg-gray-800/70 transition-all duration-200"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3 flex-1">
                        <div className="text-primary-400 mt-1">
                          {getToolIcon(tool.name)}
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-white">
                            {tool.name}
                          </h3>
                          <p className="text-sm text-gray-400 mt-1">
                            {tool.description}
                          </p>

                          {/* Permission badge */}
                          <div className="mt-2">
                            <span
                              className={`inline-flex px-2 py-1 text-xs rounded-full border ${getPermissionColor(
                                tool.permission
                              )}`}
                            >
                              {tool.permission.replace("_", " ")}
                            </span>
                          </div>

                          {/* Parameters */}
                          {tool.parameters?.properties && (
                            <div className="mt-3 p-3 bg-gray-900/50 rounded-lg">
                              <p className="text-xs font-medium text-gray-400 mb-2">
                                Parameters:
                              </p>
                              <div className="space-y-1">
                                {Object.entries(tool.parameters.properties).map(
                                  ([param, spec]) => (
                                    <div
                                      key={param}
                                      className="flex items-start text-xs"
                                    >
                                      <span className="text-primary-400 font-mono">
                                        {param}
                                      </span>
                                      <span className="text-gray-500 mx-1">
                                        :
                                      </span>
                                      <span className="text-gray-400">
                                        {spec.type}
                                        {tool.parameters.required?.includes(
                                          param
                                        ) && (
                                          <span className="text-yellow-400 ml-1">
                                            *
                                          </span>
                                        )}
                                      </span>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Enable/Disable toggle */}
                      <button
                        onClick={() => toggleTool(tool.name, isEnabled, false)}
                        disabled={togglingTool === tool.name}
                        className={`px-4 py-2 rounded-lg transition-all duration-200 ${
                          togglingTool === tool.name
                            ? "bg-gray-700/50 text-gray-500 border border-gray-600/50 cursor-not-allowed"
                            : isEnabled
                            ? "bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30"
                            : "bg-gray-700/50 text-gray-400 border border-gray-600/50 hover:bg-gray-700/70"
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          {togglingTool === tool.name ? (
                            <>
                              <div className="w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
                              <span>Updating...</span>
                            </>
                          ) : isEnabled ? (
                            <>
                              <CheckCircle className="w-4 h-4" />
                              <span>Enabled</span>
                            </>
                          ) : (
                            <>
                              <XCircle className="w-4 h-4" />
                              <span>Disabled</span>
                            </>
                          )}
                        </div>
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </motion.div>

        {/* Custom Tools */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-dark rounded-xl p-6 mt-8"
        >
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
            <Plus className="w-5 h-5 mr-2 text-primary-400" />
            Custom Tools
          </h2>

          {isLoadingCustomTools ? (
            <div className="text-center py-8">
              <div className="loading-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          ) : customTools.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Plus className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No custom tools created yet</p>
              <p className="text-sm">
                Click "Create Tool" to build your own AI tools
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {customTools.map((customTool) => {
                const isEnabled = userAllowedTools.includes(customTool.name);

                return (
                  <motion.div
                    key={`custom-${customTool.name}-${forceUpdate}-${isEnabled}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    whileHover={{ x: 4 }}
                    className="p-4 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:bg-gray-800/70 transition-all duration-200"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3 flex-1">
                        <div className="text-primary-400 mt-1">
                          <Plus className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-1">
                            <h3 className="font-semibold text-white">
                              {customTool.display_name}
                            </h3>
                            <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded-full border border-purple-500/30">
                              Custom
                            </span>
                          </div>
                          <p className="text-sm text-gray-400 mb-2">
                            {customTool.description}
                          </p>

                          {/* Permission badge */}
                          <div className="mb-2">
                            <span
                              className={`inline-flex px-2 py-1 text-xs rounded-full border ${getPermissionColor(
                                customTool.permission_level
                              )}`}
                            >
                              {customTool.permission_level.replace("_", " ")}
                            </span>
                          </div>

                          {/* Parameters */}
                          {customTool.parameters_schema?.properties &&
                            Object.keys(customTool.parameters_schema.properties)
                              .length > 0 && (
                              <div className="mt-3 p-3 bg-gray-900/50 rounded-lg">
                                <p className="text-xs font-medium text-gray-400 mb-2">
                                  Parameters:
                                </p>
                                <div className="space-y-1">
                                  {Object.entries(
                                    customTool.parameters_schema.properties
                                  ).map(([param, spec]) => (
                                    <div
                                      key={param}
                                      className="flex items-start text-xs"
                                    >
                                      <span className="text-primary-400 font-mono">
                                        {param}
                                      </span>
                                      <span className="text-gray-500 mx-1">
                                        :
                                      </span>
                                      <span className="text-gray-400">
                                        {spec.type}
                                        {customTool.parameters_schema.required?.includes(
                                          param
                                        ) && (
                                          <span className="text-yellow-400 ml-1">
                                            *
                                          </span>
                                        )}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {/* Edit custom tool */}
                        <button
                          onClick={() =>
                            navigate(`/edit-tool/${customTool.id}`)
                          }
                          className="px-3 py-2 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-all duration-200 flex items-center space-x-1"
                        >
                          <Pencil className="w-4 h-4" />
                          <span>Edit</span>
                        </button>

                        {/* Remove custom tool */}
                        <button
                          onClick={() => deleteCustomTool(customTool)}
                          disabled={deletingToolId === customTool.id}
                          className={`px-3 py-2 rounded-lg border transition-all duration-200 flex items-center space-x-1 ${
                            deletingToolId === customTool.id
                              ? "bg-gray-700/50 text-gray-500 border-gray-600/50 cursor-not-allowed"
                              : "bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/30"
                          }`}
                        >
                          <span className="w-4 h-4 inline-block">🗑️</span>
                          <span>
                            {deletingToolId === customTool.id
                              ? "Removing..."
                              : "Remove"}
                          </span>
                        </button>

                        {/* Enable/Disable toggle */}
                        <button
                          onClick={() =>
                            toggleTool(customTool.name, isEnabled, true)
                          }
                          disabled={togglingTool === customTool.name}
                          className={`px-4 py-2 rounded-lg transition-all duration-200 ${
                            togglingTool === customTool.name
                              ? "bg-gray-700/50 text-gray-500 border border-gray-600/50 cursor-not-allowed"
                              : isEnabled
                              ? "bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30"
                              : "bg-gray-700/50 text-gray-400 border border-gray-600/50 hover:bg-gray-700/70"
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            {togglingTool === customTool.name ? (
                              <>
                                <div className="w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
                                <span>Updating...</span>
                              </>
                            ) : isEnabled ? (
                              <>
                                <CheckCircle className="w-4 h-4" />
                                <span>Enabled</span>
                              </>
                            ) : (
                              <>
                                <XCircle className="w-4 h-4" />
                                <span>Disabled</span>
                              </>
                            )}
                          </div>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </motion.div>

        {/* Info note */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mt-8 p-4 bg-primary-500/10 border border-primary-500/30 rounded-lg"
        >
          <div className="flex items-start space-x-3">
            <Info className="w-5 h-5 text-primary-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-primary-300">
              <p className="font-medium mb-1">About Tool Permissions</p>
              <p className="opacity-90">
                Tools are only executed after your explicit approval during
                conversations. Enabling a tool here allows the AI to suggest
                using it, but you'll always have the final say on whether it
                actually runs.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Permission levels */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-dark rounded-xl p-6 mt-8"
        >
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
            <Shield className="w-5 h-5 mr-2 text-primary-400" />
            Permission Levels
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {permissions.map((perm) => (
              <div
                key={perm.name}
                className={`p-3 rounded-lg border ${getPermissionColor(
                  perm.name
                )}`}
              >
                <p className="font-medium">
                  {perm.name.replace("_", " ").toUpperCase()}
                </p>
                <p className="text-xs opacity-80 mt-1">{perm.description}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Tools;
