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
  Grid3x3,
  List,
  LayoutGrid,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Filter,
  X,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";
import { useNavigate } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";

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
  const [viewMode, setViewMode] = useState("grid"); // "grid", "list", "compact"
  const [searchQuery, setSearchQuery] = useState("");
  const [filterPermission, setFilterPermission] = useState("all");
  const [expandedTools, setExpandedTools] = useState(new Set());
  const [showPermissions, setShowPermissions] = useState(false);
  const [builtInToolsExpanded, setBuiltInToolsExpanded] = useState(true);
  const [customToolsExpanded, setCustomToolsExpanded] = useState(true);

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

  const toggleToolExpansion = (toolName) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName);
    } else {
      newExpanded.add(toolName);
    }
    setExpandedTools(newExpanded);
  };

  // Filter tools based on search and permission filter
  const filteredTools = tools.filter((tool) => {
    const matchesSearch =
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPermission =
      filterPermission === "all" || tool.permission === filterPermission;
    return matchesSearch && matchesPermission;
  });

  const filteredCustomTools = customTools.filter((tool) => {
    const matchesSearch =
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPermission =
      filterPermission === "all" || tool.permission_level === filterPermission;
    return matchesSearch && matchesPermission;
  });

  // Tool card component for reuse
  const ToolCard = ({ tool, isCustom = false, viewMode }) => {
    const isEnabled = userAllowedTools.includes(tool.name);
    const toolName = isCustom ? tool.display_name : tool.name;
    const toolDescription = tool.description;
    const permission = isCustom ? tool.permission_level : tool.permission;
    const parameters = isCustom ? tool.parameters_schema : tool.parameters;
    const isExpanded = expandedTools.has(tool.name);
    const hasParams =
      parameters?.properties && Object.keys(parameters.properties).length > 0;

    if (viewMode === "compact") {
      return (
        <div className="flex items-center justify-between p-2 rounded-lg bg-gray-800/30 border border-gray-700/30 hover:bg-gray-800/50 transition-all">
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            <div className="text-primary-400 flex-shrink-0">
              {getToolIcon(tool.name)}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-white truncate">
                {toolName}
              </h3>
            </div>
            {isCustom && (
              <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded border border-purple-500/30 flex-shrink-0">
                Custom
              </span>
            )}
            <span
              className={`px-1.5 py-0.5 text-xs rounded border flex-shrink-0 ${getPermissionColor(
                permission
              )}`}
            >
              {permission.replace("_", " ")}
            </span>
          </div>
          <button
            onClick={() => toggleTool(tool.name, isEnabled, isCustom)}
            disabled={togglingTool === tool.name}
            className={`ml-2 px-2 py-1 rounded text-xs transition-all ${
              isEnabled
                ? "bg-green-500/20 text-green-400 border border-green-500/30"
                : "bg-gray-700/50 text-gray-400 border border-gray-600/50"
            }`}
          >
            {isEnabled ? "ON" : "OFF"}
          </button>
        </div>
      );
    }

    if (viewMode === "grid") {
      return (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-4 rounded-lg bg-gray-800/30 border border-gray-700/30 hover:bg-gray-800/50 hover:border-gray-700/50 transition-all"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2 flex-1 min-w-0">
              <div className="text-primary-400 flex-shrink-0">
                {getToolIcon(tool.name)}
              </div>
              <h3 className="text-sm font-semibold text-white truncate">
                {toolName}
              </h3>
              {isCustom && (
                <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded border border-purple-500/30 flex-shrink-0">
                  Custom
                </span>
              )}
            </div>
            <button
              onClick={() => toggleTool(tool.name, isEnabled, isCustom)}
              disabled={togglingTool === tool.name}
              className={`px-2 py-1 rounded text-xs transition-all flex-shrink-0 ${
                isEnabled
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-gray-700/50 text-gray-400 border border-gray-600/50"
              }`}
            >
              {isEnabled ? (
                <CheckCircle className="w-3 h-3" />
              ) : (
                <XCircle className="w-3 h-3" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 mb-2 line-clamp-2">
            {toolDescription}
          </p>
          <div className="flex items-center justify-between">
            <span
              className={`px-2 py-0.5 text-xs rounded border ${getPermissionColor(
                permission
              )}`}
            >
              {permission.replace("_", " ")}
            </span>
            {hasParams && (
              <button
                onClick={() => toggleToolExpansion(tool.name)}
                className="text-xs text-gray-500 hover:text-gray-400"
              >
                {isExpanded ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            )}
          </div>
          {isExpanded && hasParams && (
            <div className="mt-2 pt-2 border-t border-gray-700/30">
              <div className="space-y-1">
                {Object.entries(parameters.properties)
                  .slice(0, 3)
                  .map(([param, spec]) => (
                    <div key={param} className="text-xs">
                      <span className="text-primary-400 font-mono">
                        {param}
                      </span>
                      <span className="text-gray-500 mx-1">:</span>
                      <span className="text-gray-400">{spec.type}</span>
                      {parameters.required?.includes(param) && (
                        <span className="text-yellow-400 ml-1">*</span>
                      )}
                    </div>
                  ))}
                {Object.keys(parameters.properties).length > 3 && (
                  <p className="text-xs text-gray-500">
                    +{Object.keys(parameters.properties).length - 3} more
                  </p>
                )}
              </div>
            </div>
          )}
          {isCustom && (
            <div className="mt-2 pt-2 border-t border-gray-700/30 flex space-x-1">
              <button
                onClick={() => navigate(`/edit-tool/${tool.id}`)}
                className="flex-1 px-2 py-1 text-xs bg-blue-500/20 text-blue-400 rounded border border-blue-500/30 hover:bg-blue-500/30"
              >
                Edit
              </button>
              <button
                onClick={() => deleteCustomTool(tool)}
                disabled={deletingToolId === tool.id}
                className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded border border-red-500/30 hover:bg-red-500/30"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          )}
        </motion.div>
      );
    }

    // List view (original detailed view but more compact)
    return (
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className="p-3 rounded-lg bg-gray-800/30 border border-gray-700/30 hover:bg-gray-800/50 transition-all"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className="text-primary-400 mt-0.5 flex-shrink-0">
              {getToolIcon(tool.name)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="text-sm font-semibold text-white">{toolName}</h3>
                {isCustom && (
                  <span className="px-1.5 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded border border-purple-500/30">
                    Custom
                  </span>
                )}
                <span
                  className={`px-1.5 py-0.5 text-xs rounded border ${getPermissionColor(
                    permission
                  )}`}
                >
                  {permission.replace("_", " ")}
                </span>
              </div>
              <p className="text-xs text-gray-400 mb-2">{toolDescription}</p>
              {isExpanded && hasParams && (
                <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs">
                  {Object.entries(parameters.properties).map(
                    ([param, spec]) => (
                      <div key={param} className="flex items-center">
                        <span className="text-primary-400 font-mono">
                          {param}
                        </span>
                        <span className="text-gray-500 mx-1">:</span>
                        <span className="text-gray-400">{spec.type}</span>
                        {parameters.required?.includes(param) && (
                          <span className="text-yellow-400 ml-1">*</span>
                        )}
                      </div>
                    )
                  )}
                </div>
              )}
              {hasParams && (
                <button
                  onClick={() => toggleToolExpansion(tool.name)}
                  className="text-xs text-gray-500 hover:text-gray-400 mt-1"
                >
                  {isExpanded ? "Hide" : "Show"} parameters
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2 flex-shrink-0">
            {isCustom && (
              <>
                <button
                  onClick={() => navigate(`/edit-tool/${tool.id}`)}
                  className="p-1.5 text-blue-400 hover:bg-blue-500/20 rounded"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => deleteCustomTool(tool)}
                  disabled={deletingToolId === tool.id}
                  className="p-1.5 text-red-400 hover:bg-red-500/20 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
            <button
              onClick={() => toggleTool(tool.name, isEnabled, isCustom)}
              disabled={togglingTool === tool.name}
              className={`px-3 py-1.5 rounded text-xs transition-all ${
                isEnabled
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-gray-700/50 text-gray-400 border border-gray-600/50"
              }`}
            >
              {isEnabled ? "Enabled" : "Disabled"}
            </button>
          </div>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-7xl mx-auto p-4">
        {/* Minimal Header */}
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Tools</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              {filteredTools.length + filteredCustomTools.length} tools
              available
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigate("/add-tool")}
              className="px-3 py-1.5 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-all text-sm flex items-center space-x-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>New</span>
            </button>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="mb-4 flex items-center justify-between gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Filter */}
          <select
            value={filterPermission}
            onChange={(e) => setFilterPermission(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          >
            <option value="all">All Permissions</option>
            {permissions.map((perm) => (
              <option key={perm.name} value={perm.name}>
                {perm.name.replace("_", " ")}
              </option>
            ))}
          </select>

          {/* View Toggle */}
          <div className="flex items-center space-x-1 bg-gray-800/50 rounded-lg p-1 border border-gray-700/50">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded transition-all ${
                viewMode === "grid"
                  ? "bg-primary-500/20 text-primary-400"
                  : "text-gray-400 hover:text-white"
              }`}
              title="Grid View"
            >
              <Grid3x3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded transition-all ${
                viewMode === "list"
                  ? "bg-primary-500/20 text-primary-400"
                  : "text-gray-400 hover:text-white"
              }`}
              title="List View"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("compact")}
              className={`p-1.5 rounded transition-all ${
                viewMode === "compact"
                  ? "bg-primary-500/20 text-primary-400"
                  : "text-gray-400 hover:text-white"
              }`}
              title="Compact View"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Loading State */}
        {isLoading || isLoadingCustomTools ? (
          <div className="text-center py-12">
            <div className="loading-dots">
              <span />
              <span />
              <span />
            </div>
            <p className="text-sm text-gray-400 mt-3">Loading tools...</p>
          </div>
        ) : (
          <>
            {/* Built-in Tools */}
            {filteredTools.length > 0 && (
              <div className="mb-6">
                <button
                  onClick={() => setBuiltInToolsExpanded(!builtInToolsExpanded)}
                  className="flex items-center space-x-2 mb-3 hover:opacity-80 transition-opacity"
                >
                  <ChevronRight
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      builtInToolsExpanded ? "rotate-90" : ""
                    }`}
                  />
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                    Built-in Tools ({filteredTools.length})
                  </h2>
                </button>
                {builtInToolsExpanded && (
                  <>
                    {viewMode === "grid" ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                        {filteredTools.map((tool) => (
                          <ToolCard
                            key={tool.name}
                            tool={tool}
                            viewMode={viewMode}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {filteredTools.map((tool) => (
                          <ToolCard
                            key={tool.name}
                            tool={tool}
                            viewMode={viewMode}
                          />
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Custom Tools */}
            {filteredCustomTools.length > 0 && (
              <div className="mb-6">
                <button
                  onClick={() => setCustomToolsExpanded(!customToolsExpanded)}
                  className="flex items-center space-x-2 mb-3 hover:opacity-80 transition-opacity"
                >
                  <ChevronRight
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      customToolsExpanded ? "rotate-90" : ""
                    }`}
                  />
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
                    Custom Tools ({filteredCustomTools.length})
                  </h2>
                </button>
                {customToolsExpanded && (
                  <>
                    {viewMode === "grid" ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                        {filteredCustomTools.map((tool) => (
                          <ToolCard
                            key={tool.id}
                            tool={tool}
                            isCustom={true}
                            viewMode={viewMode}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {filteredCustomTools.map((tool) => (
                          <ToolCard
                            key={tool.id}
                            tool={tool}
                            isCustom={true}
                            viewMode={viewMode}
                          />
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Empty State */}
            {filteredTools.length === 0 && filteredCustomTools.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <Wrench className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No tools found</p>
                {searchQuery && (
                  <p className="text-sm mt-1">
                    Try adjusting your search or filters
                  </p>
                )}
                {!searchQuery && customTools.length === 0 && (
                  <button
                    onClick={() => navigate("/add-tool")}
                    className="mt-4 px-4 py-2 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-all text-sm"
                  >
                    Create Your First Tool
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {/* Permissions Section - Collapsible */}
        <div className="mt-6">
          <button
            onClick={() => setShowPermissions(!showPermissions)}
            className="flex items-center justify-between w-full p-3 rounded-lg bg-gray-800/30 border border-gray-700/30 hover:bg-gray-800/50 transition-all"
          >
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-300">
                Permission Levels
              </span>
            </div>
            {showPermissions ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>
          {showPermissions && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2"
            >
              {permissions.map((perm) => (
                <div
                  key={perm.name}
                  className={`p-2 rounded border text-xs ${getPermissionColor(
                    perm.name
                  )}`}
                >
                  <p className="font-medium">
                    {perm.name.replace("_", " ").toUpperCase()}
                  </p>
                  <p className="opacity-80 mt-0.5">{perm.description}</p>
                </div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Tools;
