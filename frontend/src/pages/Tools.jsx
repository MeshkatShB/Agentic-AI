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
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";

const Tools = () => {
  const { user } = useAuthStore();
  const [tools, setTools] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadTools();
    loadPermissions();
  }, []);

  const loadTools = async () => {
    try {
      const response = await axios.get("/tools/");
      setTools(response.data);
    } catch (error) {
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

  const toggleTool = async (toolName, currentlyEnabled) => {
    try {
      await axios.post("/tools/grant-permission", {
        tool_name: toolName,
        grant: !currentlyEnabled,
      });

      // Reload tools
      await loadTools();
      toast.success(
        currentlyEnabled ? `Disabled ${toolName}` : `Enabled ${toolName}`
      );
    } catch (error) {
      toast.error("Failed to update tool permission");
    }
  };

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

  const userAllowedTools = user?.allowed_tools || [];

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Tools & Permissions
          </h1>
          <p className="text-gray-400">
            Manage which tools the AI agent can use and their permissions
          </p>
        </div>

        {/* Permission levels */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-dark rounded-xl p-6 mb-8"
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

                return (
                  <motion.div
                    key={tool.name}
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
                        onClick={() => toggleTool(tool.name, isEnabled)}
                        className={`px-4 py-2 rounded-lg transition-all duration-200 ${
                          isEnabled
                            ? "bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30"
                            : "bg-gray-700/50 text-gray-400 border border-gray-600/50 hover:bg-gray-700/70"
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          {isEnabled ? (
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
      </div>
    </div>
  );
};

export default Tools;
