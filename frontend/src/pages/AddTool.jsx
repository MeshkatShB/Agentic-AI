import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Save,
  Code,
  Settings,
  Shield,
  AlertCircle,
  CheckCircle,
  Info,
  Eye,
  EyeOff,
  Play,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

const AddTool = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isTestingCode, setIsTestingCode] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    display_name: "",
    description: "",
    permission_level: "safe",
    code: `async def execute(self, **parameters):
    """
    Implement your tool logic here.
    
    Args:
        parameters: Dictionary containing the input parameters
        
    Returns:
        ToolResult object with success, output, error, and metadata
    """
    from backend.tools.base import ToolResult
    
    # Your implementation here
    result = "Hello from custom tool!"
    
    return ToolResult(
        success=True,
        output=result,
        error=None,
        metadata={"custom_tool": True}
    )`,
    parameters_schema: {
      type: "object",
      properties: {},
      required: [],
    },
  });

  const [errors, setErrors] = useState({});

  const permissionLevels = [
    {
      value: "safe",
      label: "Safe",
      description: "No special permissions required",
      color: "text-green-400",
    },
    {
      value: "read_files",
      label: "Read Files",
      description: "Can read local files",
      color: "text-blue-400",
    },
    {
      value: "write_files",
      label: "Write Files",
      description: "Can write local files",
      color: "text-yellow-400",
    },
    {
      value: "network",
      label: "Network",
      description: "Can access the network",
      color: "text-purple-400",
    },
    {
      value: "database_read",
      label: "Database Read",
      description: "Can read from databases",
      color: "text-cyan-400",
    },
    {
      value: "database_write",
      label: "Database Write",
      description: "Can write to databases",
      color: "text-orange-400",
    },
    {
      value: "system",
      label: "System",
      description: "Can execute system commands",
      color: "text-red-400",
    },
  ];

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Tool name is required";
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.name)) {
      newErrors.name =
        "Tool name can only contain letters, numbers, and underscores";
    }

    if (!formData.display_name.trim()) {
      newErrors.display_name = "Display name is required";
    }

    if (!formData.description.trim()) {
      newErrors.description = "Description is required";
    }

    if (!formData.code.trim()) {
      newErrors.code = "Code is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const testCode = async () => {
    if (!formData.code.trim()) {
      toast.error("Please enter some code to test");
      return;
    }

    setIsTestingCode(true);
    setTestResult(null);

    try {
      // Simple syntax validation on frontend
      // Note: This is just a basic check, real validation happens on backend
      if (!formData.code.includes("def execute")) {
        throw new Error("Code must contain an 'execute' function");
      }

      setTestResult({
        success: true,
        message:
          "Code syntax appears valid. Full validation will happen when saving.",
      });
      toast.success("Code syntax check passed");
    } catch (error) {
      setTestResult({
        success: false,
        message: error.message,
      });
      toast.error("Code syntax error: " + error.message);
    } finally {
      setIsTestingCode(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      toast.error("Please fix the errors in the form");
      return;
    }

    setIsLoading(true);

    try {
      const response = await axios.post("/custom-tools/", {
        name: formData.name,
        display_name: formData.display_name,
        description: formData.description,
        permission_level: formData.permission_level,
        code: formData.code,
        parameters_schema: formData.parameters_schema,
      });

      toast.success("Custom tool created successfully!");
      navigate("/tools");
    } catch (error) {
      console.error("Error creating custom tool:", error);
      toast.error(
        error.response?.data?.detail || "Failed to create custom tool"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const addParameter = () => {
    const paramName = prompt("Enter parameter name:");
    if (paramName && paramName.trim()) {
      const newSchema = { ...formData.parameters_schema };
      newSchema.properties[paramName] = {
        type: "string",
        description: "Parameter description",
      };
      setFormData({ ...formData, parameters_schema: newSchema });
    }
  };

  const removeParameter = (paramName) => {
    const newSchema = { ...formData.parameters_schema };
    delete newSchema.properties[paramName];
    newSchema.required = newSchema.required.filter((req) => req !== paramName);
    setFormData({ ...formData, parameters_schema: newSchema });
  };

  const toggleRequired = (paramName) => {
    const newSchema = { ...formData.parameters_schema };
    if (newSchema.required.includes(paramName)) {
      newSchema.required = newSchema.required.filter(
        (req) => req !== paramName
      );
    } else {
      newSchema.required.push(paramName);
    }
    setFormData({ ...formData, parameters_schema: newSchema });
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-4 mb-4">
            <button
              onClick={() => navigate("/tools")}
              className="p-2 rounded-lg bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-700/50 transition-all duration-200"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">
                Create Custom Tool
              </h1>
              <p className="text-gray-400">
                Build your own AI tool with custom functionality
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-dark rounded-xl p-6"
          >
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2 text-primary-400" />
              Basic Information
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Tool Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="my_custom_tool"
                  className={`w-full px-3 py-2 rounded-lg bg-gray-800/50 border text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                    errors.name ? "border-red-500" : "border-gray-700/50"
                  }`}
                />
                {errors.name && (
                  <p className="text-red-400 text-sm mt-1">{errors.name}</p>
                )}
                <p className="text-gray-500 text-xs mt-1">
                  Used as identifier (letters, numbers, underscores only)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Display Name *
                </label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) =>
                    setFormData({ ...formData, display_name: e.target.value })
                  }
                  placeholder="My Custom Tool"
                  className={`w-full px-3 py-2 rounded-lg bg-gray-800/50 border text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                    errors.display_name
                      ? "border-red-500"
                      : "border-gray-700/50"
                  }`}
                />
                {errors.display_name && (
                  <p className="text-red-400 text-sm mt-1">
                    {errors.display_name}
                  </p>
                )}
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description *
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Describe what your tool does..."
                rows={3}
                className={`w-full px-3 py-2 rounded-lg bg-gray-800/50 border text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none ${
                  errors.description ? "border-red-500" : "border-gray-700/50"
                }`}
              />
              {errors.description && (
                <p className="text-red-400 text-sm mt-1">
                  {errors.description}
                </p>
              )}
            </div>
          </motion.div>

          {/* Permission Level */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-dark rounded-xl p-6"
          >
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
              <Shield className="w-5 h-5 mr-2 text-primary-400" />
              Permission Level
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {permissionLevels.map((permission) => (
                <label
                  key={permission.value}
                  className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                    formData.permission_level === permission.value
                      ? "bg-primary-500/20 border-primary-500/50"
                      : "bg-gray-800/30 border-gray-700/50 hover:bg-gray-700/50"
                  }`}
                >
                  <input
                    type="radio"
                    name="permission_level"
                    value={permission.value}
                    checked={formData.permission_level === permission.value}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        permission_level: e.target.value,
                      })
                    }
                    className="sr-only"
                  />
                  <div className="flex items-center space-x-2">
                    <div
                      className={`w-3 h-3 rounded-full ${permission.color} bg-current opacity-20`}
                    />
                    <span className={`font-medium ${permission.color}`}>
                      {permission.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    {permission.description}
                  </p>
                </label>
              ))}
            </div>
          </motion.div>

          {/* Parameters Schema */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-dark rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white flex items-center">
                <Settings className="w-5 h-5 mr-2 text-primary-400" />
                Parameters
              </h2>
              <button
                type="button"
                onClick={addParameter}
                className="px-3 py-1 text-sm bg-primary-500/20 text-primary-400 rounded hover:bg-primary-500/30 transition-colors"
              >
                Add Parameter
              </button>
            </div>

            {Object.keys(formData.parameters_schema.properties).length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No parameters defined</p>
                <p className="text-sm">
                  Click "Add Parameter" to define input parameters for your tool
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {Object.entries(formData.parameters_schema.properties).map(
                  ([paramName, paramSpec]) => (
                    <div
                      key={paramName}
                      className="p-3 bg-gray-800/30 rounded-lg"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-primary-400">
                              {paramName}
                            </span>
                            <span className="text-gray-500">:</span>
                            <span className="text-gray-400">
                              {paramSpec.type}
                            </span>
                            {formData.parameters_schema.required.includes(
                              paramName
                            ) && (
                              <span className="text-yellow-400 text-xs">
                                required
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {paramSpec.description}
                          </p>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            type="button"
                            onClick={() => toggleRequired(paramName)}
                            className={`px-2 py-1 text-xs rounded transition-colors ${
                              formData.parameters_schema.required.includes(
                                paramName
                              )
                                ? "bg-yellow-500/20 text-yellow-400"
                                : "bg-gray-700/50 text-gray-400 hover:bg-gray-600/50"
                            }`}
                          >
                            {formData.parameters_schema.required.includes(
                              paramName
                            )
                              ? "Required"
                              : "Optional"}
                          </button>
                          <button
                            type="button"
                            onClick={() => removeParameter(paramName)}
                            className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}
          </motion.div>

          {/* Code Editor */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-dark rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white flex items-center">
                <Code className="w-5 h-5 mr-2 text-primary-400" />
                Tool Implementation
              </h2>
              <div className="flex space-x-2">
                <button
                  type="button"
                  onClick={testCode}
                  disabled={isTestingCode}
                  className="px-3 py-1 text-sm bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors disabled:opacity-50 flex items-center space-x-1"
                >
                  <Play className="w-3 h-3" />
                  <span>{isTestingCode ? "Testing..." : "Test Code"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setShowPreview(!showPreview)}
                  className="px-3 py-1 text-sm bg-gray-700/50 text-gray-400 rounded hover:bg-gray-600/50 transition-colors flex items-center space-x-1"
                >
                  {showPreview ? (
                    <EyeOff className="w-3 h-3" />
                  ) : (
                    <Eye className="w-3 h-3" />
                  )}
                  <span>{showPreview ? "Hide" : "Preview"}</span>
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <textarea
                value={formData.code}
                onChange={(e) =>
                  setFormData({ ...formData, code: e.target.value })
                }
                placeholder="Enter your Python code here..."
                rows={20}
                className={`w-full px-4 py-3 rounded-lg bg-gray-900/50 border font-mono text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none ${
                  errors.code ? "border-red-500" : "border-gray-700/50"
                }`}
                style={{
                  fontFamily: "JetBrains Mono, Consolas, Monaco, monospace",
                }}
              />
              {errors.code && (
                <p className="text-red-400 text-sm">{errors.code}</p>
              )}

              {testResult && (
                <div
                  className={`p-3 rounded-lg border ${
                    testResult.success
                      ? "bg-green-500/10 border-green-500/30 text-green-400"
                      : "bg-red-500/10 border-red-500/30 text-red-400"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    {testResult.success ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <AlertCircle className="w-4 h-4" />
                    )}
                    <span className="text-sm">{testResult.message}</span>
                  </div>
                </div>
              )}

              <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="flex items-start space-x-2">
                  <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-300">
                    <p className="font-medium mb-1">
                      Implementation Guidelines
                    </p>
                    <ul className="text-xs opacity-90 space-y-1">
                      <li>
                        • Your function must be named{" "}
                        <code className="bg-blue-500/20 px-1 rounded">
                          execute
                        </code>
                      </li>
                      <li>
                        • Return a{" "}
                        <code className="bg-blue-500/20 px-1 rounded">
                          ToolResult
                        </code>{" "}
                        object
                      </li>
                      <li>
                        • Use{" "}
                        <code className="bg-blue-500/20 px-1 rounded">
                          **parameters
                        </code>{" "}
                        to receive input
                      </li>
                      <li>
                        • Handle errors gracefully and return appropriate error
                        messages
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex items-center justify-end space-x-4"
          >
            <button
              type="button"
              onClick={() => navigate("/tools")}
              className="px-6 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 transition-all duration-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>{isLoading ? "Creating..." : "Create Tool"}</span>
            </button>
          </motion.div>
        </form>
      </div>
    </div>
  );
};

export default AddTool;
