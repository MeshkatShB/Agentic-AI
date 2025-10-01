import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Save,
  Code,
  Settings,
  Shield,
  AlertCircle,
  CheckCircle,
  Trash2,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

const EditTool = () => {
  const navigate = useNavigate();
  const { toolId } = useParams();
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [testResult, setTestResult] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [formData, setFormData] = useState({
    display_name: "",
    description: "",
    permission_level: "safe",
    code: "",
    parameters_schema: { type: "object", properties: {}, required: [] },
    is_active: true,
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    const loadTool = async () => {
      try {
        setIsFetching(true);
        const res = await axios.get(`/custom-tools/${toolId}`);
        const tool = res.data;
        setFormData({
          display_name: tool.display_name,
          description: tool.description,
          permission_level: tool.permission_level,
          code: tool.code || "",
          parameters_schema: tool.parameters_schema || {
            type: "object",
            properties: {},
            required: [],
          },
          is_active: tool.is_active,
        });
      } catch (e) {
        toast.error("Failed to load tool");
        navigate("/tools");
      } finally {
        setIsFetching(false);
      }
    };
    loadTool();
  }, [toolId, navigate]);

  const validateForm = () => {
    const newErrors = {};
    if (!formData.display_name.trim())
      newErrors.display_name = "Display name is required";
    if (!formData.description.trim())
      newErrors.description = "Description is required";
    if (!formData.code.trim()) newErrors.code = "Code is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) {
      toast.error("Please fix the errors in the form");
      return;
    }
    setIsLoading(true);
    try {
      const res = await axios.put(`/custom-tools/${toolId}`, {
        display_name: formData.display_name,
        description: formData.description,
        permission_level: formData.permission_level,
        code: formData.code,
        parameters_schema: formData.parameters_schema,
        is_active: formData.is_active,
      });
      toast.success("Tool updated successfully");
      navigate("/tools");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update tool");
    } finally {
      setIsLoading(false);
    }
  };

  const permissionLevels = [
    { value: "safe", label: "Safe", color: "text-green-400" },
    { value: "read_files", label: "Read Files", color: "text-blue-400" },
    { value: "write_files", label: "Write Files", color: "text-yellow-400" },
    { value: "network", label: "Network", color: "text-purple-400" },
    { value: "database_read", label: "Database Read", color: "text-cyan-400" },
    {
      value: "database_write",
      label: "Database Write",
      color: "text-orange-400",
    },
    { value: "system", label: "System", color: "text-red-400" },
  ];

  const handleDelete = async () => {
    const confirmed = window.confirm(
      "Delete this custom tool? This action cannot be undone."
    );
    if (!confirmed) return;
    try {
      setIsDeleting(true);
      await axios.delete(`/custom-tools/${toolId}`);
      toast.success("Tool deleted");
      navigate("/tools");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to delete tool");
    } finally {
      setIsDeleting(false);
    }
  };

  if (isFetching) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="loading-dots">
          <span />
          <span />
          <span />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto p-6">
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
                Edit Custom Tool
              </h1>
              <p className="text-gray-400">
                Update your tool configuration and code
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
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
                  Display Name *
                </label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) =>
                    setFormData({ ...formData, display_name: e.target.value })
                  }
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
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Permission Level
                </label>
                <select
                  value={formData.permission_level}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      permission_level: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 rounded-lg bg-gray-800/50 border border-gray-700/50 text-white"
                >
                  {permissionLevels.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
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

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-dark rounded-xl p-6"
          >
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
              <Code className="w-5 h-5 mr-2 text-primary-400" />
              Tool Implementation
            </h2>
            <textarea
              value={formData.code}
              onChange={(e) =>
                setFormData({ ...formData, code: e.target.value })
              }
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
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="flex items-center justify-between space-x-4"
          >
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-6 py-2 rounded-lg text-red-400 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors flex items-center space-x-2 disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              <span>{isDeleting ? "Deleting..." : "Delete Tool"}</span>
            </button>

            <div className="flex items-center space-x-4">
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
                <span>{isLoading ? "Saving..." : "Save Changes"}</span>
              </button>
            </div>
          </motion.div>
        </form>
      </div>
    </div>
  );
};

export default EditTool;
