import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Brain,
  Tool,
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Eye,
  Code,
} from "lucide-react";
import clsx from "clsx";

const StepsPanel = ({ steps = [] }) => {
  const [expandedSteps, setExpandedSteps] = React.useState(new Set());

  const toggleStep = (index) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSteps(newExpanded);
  };

  const getStepIcon = (step) => {
    switch (step.step_type) {
      case "plan":
        return <Brain className="w-4 h-4" />;
      case "tool_request":
        return <Tool className="w-4 h-4" />;
      case "tool_result":
        return <CheckCircle className="w-4 h-4" />;
      case "reflection":
        return <Eye className="w-4 h-4" />;
      case "answer":
        return <Zap className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getStepColor = (step) => {
    switch (step.step_type) {
      case "plan":
        return "from-blue-400 to-cyan-400";
      case "tool_request":
        return "from-yellow-400 to-orange-400";
      case "tool_result":
        return "from-green-400 to-emerald-400";
      case "reflection":
        return "from-purple-400 to-pink-400";
      case "answer":
        return "from-primary-400 to-primary-600";
      default:
        return "from-gray-400 to-gray-600";
    }
  };

  const getStepTitle = (step) => {
    switch (step.step_type) {
      case "plan":
        return "Planning";
      case "tool_request":
        return `Tool: ${step.tool_name}`;
      case "tool_result":
        return "Tool Result";
      case "reflection":
        return "Reflection";
      case "answer":
        return "Final Answer";
      default:
        return "Processing";
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50">
        <div className="flex items-center space-x-2">
          <Zap className="w-5 h-5 text-primary-400" />
          <h3 className="font-semibold text-white">Agent Steps</h3>
          {steps.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-primary-500/20 text-primary-400 text-xs">
              {steps.length}
            </span>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Real-time reasoning process
        </p>
      </div>

      {/* Steps list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {steps.length === 0 ? (
          <div className="text-center py-8">
            <Clock className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm">No steps yet</p>
            <p className="text-gray-500 text-xs mt-1">
              Steps will appear here when the agent processes your request
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <AnimatePresence>
              {steps.map((step, index) => {
                const isExpanded = expandedSteps.has(index);

                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ delay: index * 0.1 }}
                    className="glass-dark rounded-lg border border-gray-700/50 overflow-hidden"
                  >
                    {/* Step header */}
                    <button
                      onClick={() => toggleStep(index)}
                      className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        {/* Step number */}
                        <div
                          className={clsx(
                            "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br",
                            getStepColor(step)
                          )}
                        >
                          {step.step_number}
                        </div>

                        {/* Step icon and title */}
                        <div className="flex items-center space-x-2">
                          <div className="text-gray-400">
                            {getStepIcon(step)}
                          </div>
                          <span className="font-medium text-white">
                            {getStepTitle(step)}
                          </span>
                        </div>

                        {/* Tool approval badge */}
                        {step.tool_approved !== null && (
                          <span
                            className={clsx(
                              "px-2 py-0.5 rounded-full text-xs",
                              step.tool_approved
                                ? "bg-green-500/20 text-green-400"
                                : "bg-red-500/20 text-red-400"
                            )}
                          >
                            {step.tool_approved ? "Approved" : "Denied"}
                          </span>
                        )}
                      </div>

                      {/* Expand icon */}
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      )}
                    </button>

                    {/* Step content */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: "auto" }}
                          exit={{ height: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-3 space-y-2">
                            {/* Content */}
                            {step.content && (
                              <div className="p-3 bg-gray-800/50 rounded-lg">
                                <p className="text-sm text-gray-300 whitespace-pre-wrap">
                                  {step.content}
                                </p>
                              </div>
                            )}

                            {/* Tool input */}
                            {step.tool_input && (
                              <div className="p-3 bg-gray-800/50 rounded-lg">
                                <div className="flex items-center space-x-2 mb-2">
                                  <Code className="w-4 h-4 text-yellow-400" />
                                  <span className="text-xs font-medium text-yellow-400">
                                    Tool Input
                                  </span>
                                </div>
                                <pre className="text-xs text-gray-300 overflow-x-auto">
                                  {JSON.stringify(step.tool_input, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Tool output */}
                            {step.tool_output && (
                              <div className="p-3 bg-gray-800/50 rounded-lg">
                                <div className="flex items-center space-x-2 mb-2">
                                  <CheckCircle className="w-4 h-4 text-green-400" />
                                  <span className="text-xs font-medium text-green-400">
                                    Tool Output
                                  </span>
                                </div>
                                <pre className="text-xs text-gray-300 overflow-x-auto">
                                  {typeof step.tool_output === "string"
                                    ? step.tool_output
                                    : JSON.stringify(step.tool_output, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Reasoning */}
                            {step.reasoning && (
                              <div className="p-3 bg-gray-800/50 rounded-lg">
                                <div className="flex items-center space-x-2 mb-2">
                                  <Brain className="w-4 h-4 text-purple-400" />
                                  <span className="text-xs font-medium text-purple-400">
                                    Reasoning
                                  </span>
                                </div>
                                <p className="text-xs text-gray-300">
                                  {step.reasoning}
                                </p>
                              </div>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

export default StepsPanel;
