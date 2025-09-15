import React from "react";
import { motion } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  X,
  Check,
  FileText,
  Globe,
  Database,
} from "lucide-react";

const PermissionDialog = ({ request, onApprove, onDeny, onClose }) => {
  const getPermissionIcon = (toolName) => {
    if (toolName?.includes("file") || toolName?.includes("read")) {
      return <FileText className="w-5 h-5" />;
    }
    if (toolName?.includes("web") || toolName?.includes("search")) {
      return <Globe className="w-5 h-5" />;
    }
    if (toolName?.includes("database") || toolName?.includes("query")) {
      return <Database className="w-5 h-5" />;
    }
    return <Shield className="w-5 h-5" />;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
      />

      {/* Dialog */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        className="relative w-full max-w-md"
      >
        <div className="glass-dark rounded-2xl border border-yellow-500/30 shadow-2xl overflow-hidden">
          {/* Glow effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-yellow-400 to-orange-400 rounded-2xl blur opacity-30 animate-pulse" />

          <div className="relative">
            {/* Header */}
            <div className="p-6 border-b border-gray-700/50">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-yellow-400 to-orange-400 flex items-center justify-center">
                    <AlertTriangle className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Permission Required
                    </h3>
                    <p className="text-sm text-gray-400">
                      Tool wants to perform an action
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              {/* Tool info */}
              <div className="flex items-center space-x-3 p-3 bg-gray-800/50 rounded-lg">
                <div className="text-primary-400">
                  {getPermissionIcon(request?.tool)}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-white">
                    {request?.tool || "Unknown Tool"}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Step #{request?.step || 1}
                  </p>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-300">
                  What this tool will do:
                </p>
                <div className="p-3 bg-gray-800/50 rounded-lg">
                  <p className="text-sm text-gray-300">
                    {request?.description ||
                      "Execute the requested action with the provided parameters."}
                  </p>
                </div>
              </div>

              {/* Parameters */}
              {request?.parameters && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-300">
                    Parameters:
                  </p>
                  <div className="p-3 bg-gray-800/50 rounded-lg">
                    <pre className="text-xs text-gray-400 overflow-x-auto">
                      {JSON.stringify(request.parameters, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Warning */}
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-yellow-400">
                    This action requires your permission because it may access
                    sensitive resources. Review carefully before approving.
                  </p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="p-6 border-t border-gray-700/50 flex items-center justify-end space-x-3">
              <button
                onClick={onDeny}
                className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 border border-red-500/30 transition-all duration-200"
              >
                <div className="flex items-center space-x-2">
                  <X className="w-4 h-4" />
                  <span>Deny</span>
                </div>
              </button>
              <button
                onClick={onApprove}
                className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 border border-green-500/30 transition-all duration-200"
              >
                <div className="flex items-center space-x-2">
                  <Check className="w-4 h-4" />
                  <span>Approve</span>
                </div>
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default PermissionDialog;
