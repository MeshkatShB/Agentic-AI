import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Wrench,
  Search,
  FileText,
  Globe,
  Database,
  Calculator,
  Settings,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  Info,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";

const ToolSelector = ({
  onToolsChange,
  selectedTools = [],
  showSteps = false,
}) => {
  const { user, refreshUserData } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [availableTools, setAvailableTools] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [localSelectedTools, setLocalSelectedTools] = useState(selectedTools);
  const dropdownRef = useRef(null);
  const dropdownContentRef = useRef(null);

  // Tool icons mapping
  const getToolIcon = (toolName) => {
    const iconMap = {
      search_local_files: Search,
      read_file: FileText,
      parse_document: FileText,
      web_search: Globe,
      web_scrape: Globe,
      database_query: Database,
      database_write: Database,
      calculator: Calculator,
      system_info: Settings,
    };
    return iconMap[toolName] || Wrench;
  };

  // Tool descriptions
  const getToolDescription = (toolName) => {
    const descriptions = {
      search_local_files: "Search through indexed local documents",
      read_file: "Read contents of specific files",
      parse_document: "Extract text from PDF, DOCX, and other formats",
      web_search: "Search the web for current information",
      web_scrape: "Extract content from web pages",
      database_query: "Query the local database",
      database_write: "Write data to the local database",
      calculator: "Perform mathematical calculations",
      system_info: "Get system information and status",
    };
    return descriptions[toolName] || "AI tool";
  };

  // Tool permission levels
  const getToolPermission = (toolName) => {
    const permissions = {
      search_local_files: "READ_FILES",
      read_file: "READ_FILES",
      parse_document: "READ_FILES",
      web_search: "WEB_ACCESS",
      web_scrape: "WEB_ACCESS",
      database_query: "READ_DATABASE",
      database_write: "WRITE_DATABASE",
      calculator: "SAFE",
      system_info: "SYSTEM_READ",
    };
    return permissions[toolName] || "UNKNOWN";
  };

  const getPermissionColor = (permission) => {
    const colors = {
      SAFE: "text-green-400 bg-green-400/10 border-green-400/20",
      READ_FILES: "text-blue-400 bg-blue-400/10 border-blue-400/20",
      READ_DATABASE: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
      WRITE_DATABASE: "text-orange-400 bg-orange-400/10 border-orange-400/20",
      WEB_ACCESS: "text-purple-400 bg-purple-400/10 border-purple-400/20",
      SYSTEM_READ: "text-red-400 bg-red-400/10 border-red-400/20",
      UNKNOWN: "text-gray-400 bg-gray-400/10 border-gray-400/20",
    };
    return colors[permission] || colors.UNKNOWN;
  };

  useEffect(() => {
    loadAvailableTools();
  }, [user?.allowed_tools]); // Reload when user's allowed tools change

  useEffect(() => {
    setLocalSelectedTools(selectedTools);
  }, [selectedTools]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      const isClickInsideButton =
        dropdownRef.current && dropdownRef.current.contains(event.target);
      const isClickInsideDropdown =
        dropdownContentRef.current &&
        dropdownContentRef.current.contains(event.target);

      if (!isClickInsideButton && !isClickInsideDropdown) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const loadAvailableTools = async () => {
    try {
      setIsLoading(true);
      const userAllowedTools = user?.allowed_tools || [];

      // Fetch built-in available tools and user's custom tools in parallel
      const [builtinRes, customRes] = await Promise.all([
        axios.get("/tools/available"),
        axios.get("/custom-tools/"), // active_only defaults to true on backend
      ]);

      // Built-in tools are already in correct shape
      const builtin = Array.isArray(builtinRes.data) ? builtinRes.data : [];

      // Map custom tools to ToolInfo shape and include only those enabled by the user
      const customEnabled = (
        Array.isArray(customRes.data) ? customRes.data : []
      )
        .filter((t) => userAllowedTools.includes(t.name))
        .map((t) => ({
          name: t.name,
          description: t.description,
          permission: t.permission_level,
          parameters: t.parameters_schema || {
            type: "object",
            properties: {},
            required: [],
          },
        }));

      // Combine and filter by user's allowed_tools
      const combined = [...builtin, ...customEnabled].filter((tool) =>
        userAllowedTools.includes(tool.name)
      );

      setAvailableTools(combined);
    } catch (error) {
      console.error("Failed to load tools:", error);
      toast.error("Failed to load available tools");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTool = (toolName) => {
    const isSelected = localSelectedTools.includes(toolName);
    const newSelectedTools = isSelected
      ? localSelectedTools.filter((tool) => tool !== toolName)
      : [...localSelectedTools, toolName];

    setLocalSelectedTools(newSelectedTools);
    onToolsChange(newSelectedTools);
  };

  const selectAllTools = () => {
    const allToolNames = availableTools.map((tool) => tool.name);
    setLocalSelectedTools(allToolNames);
    onToolsChange(allToolNames);
  };

  const clearAllTools = () => {
    setLocalSelectedTools([]);
    onToolsChange([]);
  };

  const selectedCount = localSelectedTools.length;
  const totalCount = availableTools.length;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Tool selector button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white hover:bg-gray-700/50 transition-all duration-200"
      >
        <Wrench className="w-4 h-4" />
        <span className="text-sm">
          Tools {selectedCount > 0 && `(${selectedCount})`}
        </span>
        {isOpen ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* Tool selection dropdown */}
      {isOpen &&
        createPortal(
          <AnimatePresence>
            <motion.div
              ref={dropdownContentRef}
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="fixed top-20 w-96 bg-gray-900/95 backdrop-blur-md rounded-xl border border-gray-700/70 shadow-2xl z-[99999]"
              style={{
                maxHeight: "calc(100vh - 120px)",
                right: showSteps ? "340px" : "16px", // Account for steps panel width (320px) + margin
              }}
            >
              {/* Header */}
              <div className="p-4 border-b border-gray-700/50">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">Select Tools</h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        selectAllTools();
                      }}
                      className="px-2 py-1 text-xs bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors"
                    >
                      All
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        clearAllTools();
                      }}
                      className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
                    >
                      None
                    </button>
                  </div>
                </div>
                <p className="text-xs text-gray-400">
                  Choose which tools the AI can use in this conversation
                </p>
              </div>

              {/* Tools list */}
              <div className="max-h-80 overflow-y-auto custom-scrollbar">
                {isLoading ? (
                  <div className="p-4 text-center text-gray-400">
                    <div className="loading-dots">
                      <span />
                      <span />
                      <span />
                    </div>
                    <p className="text-sm mt-2">Loading tools...</p>
                  </div>
                ) : (
                  <div className="p-2">
                    {availableTools.map((tool) => {
                      const Icon = getToolIcon(tool.name);
                      const description = getToolDescription(tool.name);
                      const permission = getToolPermission(tool.name);
                      const isSelected = localSelectedTools.includes(tool.name);
                      const permissionColor = getPermissionColor(permission);

                      return (
                        <motion.div
                          key={tool.name}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="mb-2"
                        >
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleTool(tool.name);
                            }}
                            className={`w-full p-3 rounded-lg border transition-all duration-200 ${
                              isSelected
                                ? "bg-primary-500/20 border-primary-500/50 text-white"
                                : "bg-gray-800/30 border-gray-700/50 text-gray-300 hover:bg-gray-700/50"
                            }`}
                          >
                            <div className="flex items-start space-x-3">
                              <div className="flex-shrink-0 mt-0.5">
                                {isSelected ? (
                                  <Check className="w-4 h-4 text-primary-400" />
                                ) : (
                                  <Icon className="w-4 h-4 text-gray-400" />
                                )}
                              </div>
                              <div className="flex-1 text-left min-w-0">
                                <div className="flex items-start justify-between mb-1 gap-2">
                                  <h4 className="font-medium text-sm truncate">
                                    {tool.name
                                      .replace(/_/g, " ")
                                      .replace(/\b\w/g, (l) => l.toUpperCase())}
                                  </h4>
                                  <span
                                    className={`px-2 py-0.5 text-xs rounded-full border flex-shrink-0 ${permissionColor}`}
                                  >
                                    {permission.replace("_", " ")}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-400 mb-1 line-clamp-2">
                                  {description}
                                </p>
                                {tool.description &&
                                  tool.description !== description && (
                                    <p className="text-xs text-gray-500 line-clamp-1">
                                      {tool.description}
                                    </p>
                                  )}
                              </div>
                            </div>
                          </button>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-3 border-t border-gray-700/50 bg-gray-800/30">
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>
                    {selectedCount} of {totalCount} tools selected
                  </span>
                  <div className="flex items-center space-x-1">
                    <Info className="w-3 h-3" />
                    <span>Tools are applied to new messages</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>,
          document.body
        )}
    </div>
  );
};

export default ToolSelector;
