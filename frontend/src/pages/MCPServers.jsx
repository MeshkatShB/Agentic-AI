import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Server,
  Plus,
  Edit,
  Trash2,
  TestTube,
  CheckCircle,
  XCircle,
  AlertCircle,
  Globe,
  Terminal,
  Save,
  X,
  Power,
  PowerOff,
  Info,
  Loader,
  Wrench,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";

const MCPServers = () => {
  const [servers, setServers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingServer, setEditingServer] = useState(null);
  const [testingServerId, setTestingServerId] = useState(null);
  const [showToolsModal, setShowToolsModal] = useState(false);
  const [selectedServerTools, setSelectedServerTools] = useState(null);
  const [loadingTools, setLoadingTools] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    transport: "http",
    url: "",
    command: "",
    args: [],
    headers: {},
    auth_config: {},
  });
  const [newArg, setNewArg] = useState("");
  const [newHeaderKey, setNewHeaderKey] = useState("");
  const [newHeaderValue, setNewHeaderValue] = useState("");

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get("/mcp/");
      setServers(response.data);
    } catch (error) {
      console.error("Failed to load MCP servers:", error);
      toast.error("Failed to load MCP servers");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        args: formData.args || [],
        headers: formData.headers || {},
        auth_config: formData.auth_config || {},
      };

      if (editingServer) {
        await axios.put(`/mcp/${editingServer.id}`, payload);
        toast.success("MCP server updated successfully");
      } else {
        await axios.post("/mcp/", payload);
        toast.success("MCP server created successfully");
      }

      resetForm();
      loadServers();
    } catch (error) {
      console.error("Failed to save MCP server:", error);
      toast.error(
        error.response?.data?.detail || "Failed to save MCP server"
      );
    }
  };

  const handleDelete = async (serverId) => {
    if (!window.confirm("Are you sure you want to delete this MCP server?")) {
      return;
    }

    try {
      await axios.delete(`/mcp/${serverId}`);
      toast.success("MCP server deleted successfully");
      loadServers();
    } catch (error) {
      console.error("Failed to delete MCP server:", error);
      toast.error("Failed to delete MCP server");
    }
  };

  const handleTest = async (serverId) => {
    setTestingServerId(serverId);
    try {
      const response = await axios.post(`/mcp/${serverId}/test`, {});

      if (response.data.success) {
        const toolCount = response.data.tool_count || 0;
        const message = `Connection successful! Found ${toolCount} tool${toolCount !== 1 ? "s" : ""}.`;
        toast.success(message, { duration: 3000 });
      } else {
        toast.error(`Connection failed: ${response.data.message}`, {
          duration: 5000,
        });
      }
      loadServers(); // Refresh to update last_connected_at
    } catch (error) {
      console.error("Failed to test MCP server:", error);
      toast.error(
        error.response?.data?.detail || "Failed to test MCP server"
      );
    } finally {
      setTestingServerId(null);
    }
  };

  const handleShowTools = async (serverId) => {
    setLoadingTools(true);
    setShowToolsModal(true);
    try {
      const response = await axios.post(`/mcp/${serverId}/test`, {});
      if (response.data.success) {
        setSelectedServerTools({
          serverId,
          tools: response.data.tools || [],
          toolCount: response.data.tool_count || 0,
          serverName: servers.find(s => s.id === serverId)?.name || "Unknown"
        });
      } else {
        toast.error(`Failed to fetch tools: ${response.data.message}`);
        setShowToolsModal(false);
      }
    } catch (error) {
      console.error("Failed to fetch tools:", error);
      toast.error(
        error.response?.data?.detail || "Failed to fetch tools"
      );
      setShowToolsModal(false);
    } finally {
      setLoadingTools(false);
    }
  };

  const handleToggleEnabled = async (server) => {
    try {
      await axios.put(`/mcp/${server.id}`, {
        is_enabled: !server.is_enabled,
      });
      toast.success(
        `MCP server ${!server.is_enabled ? "enabled" : "disabled"}`
      );
      loadServers();
    } catch (error) {
      console.error("Failed to toggle server:", error);
      toast.error("Failed to toggle server status");
    }
  };

  const handleEdit = (server) => {
    setEditingServer(server);
    setFormData({
      name: server.name,
      description: server.description || "",
      transport: server.transport,
      url: server.url || "",
      command: server.command || "",
      args: server.args || [],
      headers: server.headers || {},
      auth_config: server.auth_config || {},
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      transport: "http",
      url: "",
      command: "",
      args: [],
      headers: {},
      auth_config: {},
    });
    setEditingServer(null);
    setShowForm(false);
    setNewArg("");
    setNewHeaderKey("");
    setNewHeaderValue("");
  };

  const addArg = () => {
    if (newArg.trim()) {
      setFormData({
        ...formData,
        args: [...(formData.args || []), newArg.trim()],
      });
      setNewArg("");
    }
  };

  const removeArg = (index) => {
    setFormData({
      ...formData,
      args: formData.args.filter((_, i) => i !== index),
    });
  };

  const addHeader = () => {
    if (newHeaderKey.trim() && newHeaderValue.trim()) {
      setFormData({
        ...formData,
        headers: {
          ...(formData.headers || {}),
          [newHeaderKey.trim()]: newHeaderValue.trim(),
        },
      });
      setNewHeaderKey("");
      setNewHeaderValue("");
    }
  };

  const removeHeader = (key) => {
    const newHeaders = { ...(formData.headers || {}) };
    delete newHeaders[key];
    setFormData({
      ...formData,
      headers: newHeaders,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Server className="w-8 h-8" />
            MCP Servers
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Manage Model Context Protocol (MCP) servers to extend agent
            capabilities
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="glass-dark px-6 py-3 rounded-lg flex items-center gap-2 hover:bg-opacity-80 transition-all"
        >
          <Plus className="w-5 h-5" />
          Add Server
        </button>
      </div>

      {/* Info Banner */}
      <div className="glass-dark p-4 rounded-lg mb-6 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-gray-700 dark:text-gray-300">
          <p className="font-semibold mb-1">About MCP Servers</p>
          <p>
            MCP (Model Context Protocol) servers provide tools and context to
            your AI agent. You can connect to HTTP-based servers or run local
            stdio-based servers. Tools from enabled servers will be automatically
            available to your agent.
          </p>
        </div>
      </div>

      {/* Form Modal */}
      {showForm && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) resetForm();
          }}
        >
          <motion.div
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
            className="glass-dark rounded-2xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                {editingServer ? "Edit MCP Server" : "Add MCP Server"}
              </h2>
              <button
                onClick={resetForm}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Server Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                  placeholder="e.g., math-server"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                  rows="2"
                  placeholder="Optional description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Transport Type *
                </label>
                <select
                  value={formData.transport}
                  onChange={(e) =>
                    setFormData({ ...formData, transport: e.target.value })
                  }
                  className="w-full px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                >
                  <option value="http">HTTP</option>
                  <option value="stdio">stdio</option>
                </select>
              </div>

              {formData.transport === "http" && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                      Server URL *
                    </label>
                    <input
                      type="url"
                      required={formData.transport === "http"}
                      value={formData.url}
                      onChange={(e) =>
                        setFormData({ ...formData, url: e.target.value })
                      }
                      className="w-full px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                      placeholder="http://localhost:8000/mcp"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                      Custom Headers
                    </label>
                    <div className="space-y-2">
                      {Object.entries(formData.headers || {}).map(
                        ([key, value]) => (
                          <div
                            key={key}
                            className="flex items-center gap-2 bg-gray-100 dark:bg-gray-700 p-2 rounded"
                          >
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              {key}:
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400 flex-1">
                              {value}
                            </span>
                            <button
                              type="button"
                              onClick={() => removeHeader(key)}
                              className="text-red-500 hover:text-red-700"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        )
                      )}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newHeaderKey}
                          onChange={(e) => setNewHeaderKey(e.target.value)}
                          placeholder="Header name"
                          className="flex-1 px-3 py-1 rounded bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm"
                        />
                        <input
                          type="text"
                          value={newHeaderValue}
                          onChange={(e) => setNewHeaderValue(e.target.value)}
                          placeholder="Header value"
                          className="flex-1 px-3 py-1 rounded bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm"
                        />
                        <button
                          type="button"
                          onClick={addHeader}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}

              {formData.transport === "stdio" && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                      Command *
                    </label>
                    <input
                      type="text"
                      required={formData.transport === "stdio"}
                      value={formData.command}
                      onChange={(e) =>
                        setFormData({ ...formData, command: e.target.value })
                      }
                      className="w-full px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                      placeholder="python"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                      Arguments
                    </label>
                    <div className="space-y-2">
                      {formData.args.map((arg, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-2 bg-gray-100 dark:bg-gray-700 p-2 rounded"
                        >
                          <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">
                            {arg}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeArg(index)}
                            className="text-red-500 hover:text-red-700"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newArg}
                          onChange={(e) => setNewArg(e.target.value)}
                          onKeyPress={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              addArg();
                            }
                          }}
                          placeholder="Argument value"
                          className="flex-1 px-3 py-1 rounded bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm"
                        />
                        <button
                          type="button"
                          onClick={addArg}
                          className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}

              <div className="flex gap-3 pt-4">
                <button
                  type="submit"
                  className="flex-1 glass-dark px-6 py-3 rounded-lg flex items-center justify-center gap-2 hover:bg-opacity-80 transition-all"
                >
                  <Save className="w-5 h-5" />
                  {editingServer ? "Update" : "Create"} Server
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-3 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}

      {/* Servers List */}
      {servers.length === 0 ? (
        <div className="glass-dark p-12 rounded-2xl text-center">
          <Server className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No MCP Servers
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Get started by adding your first MCP server
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="glass-dark px-6 py-3 rounded-lg flex items-center gap-2 mx-auto hover:bg-opacity-80 transition-all"
          >
            <Plus className="w-5 h-5" />
            Add Server
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {servers.map((server) => (
            <motion.div
              key={server.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-dark p-6 rounded-xl"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  {server.transport === "http" ? (
                    <Globe className="w-6 h-6 text-blue-500" />
                  ) : (
                    <Terminal className="w-6 h-6 text-green-500" />
                  )}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {server.name}
                    </h3>
                    <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                      {server.transport}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleEnabled(server)}
                    className={`p-2 rounded ${
                      server.is_enabled
                        ? "text-green-500 hover:bg-green-500/20"
                        : "text-gray-400 hover:bg-gray-500/20"
                    }`}
                    title={server.is_enabled ? "Disable" : "Enable"}
                  >
                    {server.is_enabled ? (
                      <Power className="w-5 h-5" />
                    ) : (
                      <PowerOff className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {server.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  {server.description}
                </p>
              )}

              <div className="space-y-2 mb-4">
                {server.transport === "http" && server.url && (
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">URL: </span>
                    <span className="text-gray-700 dark:text-gray-300 font-mono">
                      {server.url}
                    </span>
                  </div>
                )}
                {server.transport === "stdio" && server.command && (
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">Command: </span>
                    <span className="text-gray-700 dark:text-gray-300 font-mono">
                      {server.command}
                    </span>
                  </div>
                )}
                {server.last_connected_at && (
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Last connected:{" "}
                      {new Date(server.last_connected_at).toLocaleString()}
                    </div>
                    {server.last_tool_count !== null && server.last_tool_count !== undefined && server.last_tool_count > 0 && (
                      <button
                        onClick={() => handleShowTools(server.id)}
                        className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 cursor-pointer transition-colors"
                        title="Click to view available tools"
                      >
                        {server.last_tool_count} tool{server.last_tool_count !== 1 ? "s" : ""}
                      </button>
                    )}
                  </div>
                )}
                {server.last_error && (
                  <div className="text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {server.last_error.substring(0, 50)}...
                  </div>
                )}
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => handleTest(server.id)}
                  disabled={testingServerId === server.id}
                  className="flex-1 px-3 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {testingServerId === server.id ? (
                    <Loader className="w-4 h-4 animate-spin" />
                  ) : (
                    <TestTube className="w-4 h-4" />
                  )}
                  Test
                </button>
                <button
                  onClick={() => handleEdit(server)}
                  className="px-3 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(server.id)}
                  className="px-3 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Tools Modal */}
      {showToolsModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowToolsModal(false)}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="glass-dark rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Wrench className="w-6 h-6 text-blue-500" />
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    Available Tools
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedServerTools?.serverName}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowToolsModal(false)}
                className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>

            {loadingTools ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="w-8 h-8 animate-spin text-blue-500" />
              </div>
            ) : selectedServerTools?.tools && selectedServerTools.tools.length > 0 ? (
              <div className="flex-1 overflow-y-auto">
                <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
                  Found <span className="font-bold text-blue-400">{selectedServerTools.toolCount}</span> tool{selectedServerTools.toolCount !== 1 ? "s" : ""}:
                </div>
                <div className="space-y-3">
                  {selectedServerTools.tools.map((tool, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1 p-1.5 rounded bg-blue-500/20">
                          <Wrench className="w-4 h-4 text-blue-400" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-mono font-semibold text-gray-900 dark:text-white mb-1">
                            {tool.name}
                          </h3>
                          {tool.description && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                              {tool.description}
                            </p>
                          )}
                          {tool.parameters && Object.keys(tool.parameters).length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                Parameters:
                              </div>
                              <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-2 rounded overflow-x-auto">
                                {JSON.stringify(tool.parameters, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Wrench className="w-12 h-12 text-gray-400 mb-4" />
                <p className="text-gray-600 dark:text-gray-400">
                  No tools available on this server
                </p>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </div>
  );
};

export default MCPServers;

