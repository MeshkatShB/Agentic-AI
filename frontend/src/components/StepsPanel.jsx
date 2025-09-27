import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Brain,
  Wrench,
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Eye,
  Code,
  MessageSquare,
  Lightbulb,
} from "lucide-react";
import clsx from "clsx";

const StepsPanel = ({ steps = [], historicalSteps = [] }) => {
  const [expandedSteps, setExpandedSteps] = React.useState(new Set());
  const [activeTab, setActiveTab] = React.useState("current"); // "current", "historical", "thinking", "actions"
  const [showScrollIndicator, setShowScrollIndicator] = React.useState(false);
  const contentRef = React.useRef(null);

  const toggleStep = (index) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSteps(newExpanded);
  };

  // Separate thinking from actions
  const separateSteps = (steps) => {
    const thinking = [];
    const actions = [];

    steps.forEach((step, index) => {
      // Check if this is thinking content
      if (
        step.step_type === "thinking" ||
        (step.content &&
          (step.content.includes("<think>") ||
            step.content.includes("<thinking>")))
      ) {
        thinking.push({ ...step, originalIndex: index });
      } else {
        actions.push({ ...step, originalIndex: index });
      }
    });

    return { thinking, actions };
  };

  const { thinking, actions } = separateSteps(steps);

  // Check if content is scrollable
  const checkScrollable = React.useCallback(() => {
    if (contentRef.current) {
      const { scrollHeight, clientHeight, scrollTop } = contentRef.current;
      const isScrollable = scrollHeight > clientHeight;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 5;
      setShowScrollIndicator(isScrollable && !isAtBottom);
    }
  }, []);

  // Check scrollable state when content changes
  React.useEffect(() => {
    checkScrollable();
  }, [steps, historicalSteps, activeTab, expandedSteps, checkScrollable]);

  // Extract thinking content (remove <think> tags if present)
  const extractThinkingContent = (content) => {
    if (!content) return content;

    // Remove <think> or <thinking> tags
    let cleaned = content
      .replace(/<think>/g, "")
      .replace(/<\/think>/g, "")
      .replace(/<thinking>/g, "")
      .replace(/<\/thinking>/g, "")
      .trim();

    return cleaned || content;
  };

  const getStepIcon = (step) => {
    switch (step.step_type) {
      case "plan":
        return <Brain className="w-4 h-4" />;
      case "tool_request":
        return <Wrench className="w-4 h-4" />;
      case "tool_result":
        return <CheckCircle className="w-4 h-4" />;
      case "reflection":
        return <Eye className="w-4 h-4" />;
      case "thinking":
        return <Lightbulb className="w-4 h-4" />;
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
        return "from-orange-400 to-yellow-400";
      case "tool_result":
        return "from-green-400 to-emerald-400";
      case "reflection":
        return "from-purple-400 to-pink-400";
      case "thinking":
        return "from-purple-500 to-pink-500";
      case "answer":
        return "from-emerald-400 to-teal-400";
      default:
        return "from-gray-400 to-gray-500";
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
        return "Reasoning";
      case "thinking":
        return "Thinking";
      case "answer":
        return "Final Answer";
      default:
        return "Processing";
    }
  };

  const renderStepsList = (stepsList, isThinking = false) => (
    <div className="space-y-3">
      <AnimatePresence>
        {stepsList.map((step, index) => {
          const isExpanded = expandedSteps.has(step.originalIndex || index);
          const content = isThinking
            ? extractThinkingContent(step.content)
            : step.content;

          return (
            <motion.div
              key={step.originalIndex || index}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ delay: index * 0.1 }}
              className="glass-dark rounded-lg border border-gray-700/50 overflow-hidden"
            >
              {/* Step header */}
              <button
                onClick={() => toggleStep(step.originalIndex || index)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  {/* Step number */}
                  <div
                    className={clsx(
                      "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br",
                      isThinking
                        ? "from-purple-400 to-pink-400"
                        : getStepColor(step)
                    )}
                  >
                    {step.step_number}
                  </div>

                  {/* Step icon and title */}
                  <div className="flex items-center space-x-2">
                    <div className="text-gray-400">
                      {isThinking ? (
                        <Lightbulb className="w-4 h-4" />
                      ) : (
                        getStepIcon(step)
                      )}
                    </div>
                    <span className="font-medium text-white">
                      {isThinking ? "Thinking" : getStepTitle(step)}
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
                      {content && (
                        <div
                          className={clsx(
                            "p-3 rounded-lg",
                            isThinking
                              ? "bg-purple-900/20 border border-purple-500/20"
                              : "bg-gray-800/50"
                          )}
                        >
                          <p className="text-sm text-gray-300 whitespace-pre-wrap">
                            {content}
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
                          <pre className="text-xs text-gray-400 overflow-x-auto">
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
                          <pre className="text-xs text-gray-400 overflow-x-auto">
                            {typeof step.tool_output === "string"
                              ? step.tool_output
                              : JSON.stringify(step.tool_output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Reasoning */}
                      {step.reasoning && step.reasoning !== content && (
                        <div className="p-3 bg-gray-800/50 rounded-lg">
                          <div className="flex items-center space-x-2 mb-2">
                            <Eye className="w-4 h-4 text-blue-400" />
                            <span className="text-xs font-medium text-blue-400">
                              Reasoning
                            </span>
                          </div>
                          <p className="text-xs text-gray-400 whitespace-pre-wrap">
                            {step.reasoning}
                          </p>
                        </div>
                      )}

                      {/* Timestamp */}
                      {step.timestamp && (
                        <div className="text-xs text-gray-500 flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>
                            {new Date(step.timestamp).toLocaleTimeString()}
                          </span>
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
  );

  // Render historical steps with different styling
  const renderHistoricalSteps = (historicalSteps) => {
    const groupedByMessage = historicalSteps.reduce((acc, step) => {
      const messageId = step.message_id || "no-message";
      if (!acc[messageId]) {
        acc[messageId] = [];
      }
      acc[messageId].push(step);
      return acc;
    }, {});

    return (
      <div className="space-y-4">
        {Object.entries(groupedByMessage).map(([messageId, steps]) => (
          <div key={messageId} className="border-l-2 border-orange-500/30 pl-4">
            <div className="text-xs text-orange-400 mb-2 font-medium">
              Message #{messageId === "no-message" ? "Unknown" : messageId}
            </div>
            <div className="space-y-2">
              {steps.map((step, index) => (
                <motion.div
                  key={step.id || index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-3"
                >
                  <div className="flex items-start space-x-3">
                    <div
                      className={clsx(
                        "w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5",
                        step.step_type === "thinking" &&
                          "bg-purple-500/20 text-purple-400",
                        step.step_type === "tool_request" &&
                          "bg-blue-500/20 text-blue-400",
                        step.step_type === "tool_result" &&
                          "bg-green-500/20 text-green-400",
                        step.step_type === "reflection" &&
                          "bg-yellow-500/20 text-yellow-400"
                      )}
                    >
                      {step.step_type === "thinking" && (
                        <Brain className="w-3 h-3" />
                      )}
                      {step.step_type === "tool_request" && (
                        <Wrench className="w-3 h-3" />
                      )}
                      {step.step_type === "tool_result" && (
                        <CheckCircle className="w-3 h-3" />
                      )}
                      {step.step_type === "reflection" && (
                        <Lightbulb className="w-3 h-3" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="text-sm font-medium text-gray-200">
                          {step.title ||
                            `${step.step_type} ${step.step_number}`}
                        </span>
                        <span className="text-xs text-gray-500">
                          #{step.step_number}
                        </span>
                        {step.execution_time && (
                          <span className="text-xs text-gray-500">
                            {step.execution_time.toFixed(2)}s
                          </span>
                        )}
                      </div>
                      {step.content && (
                        <div className="text-sm text-gray-300 whitespace-pre-wrap">
                          {step.content}
                        </div>
                      )}
                      {step.tool_name && (
                        <div className="mt-2 text-xs">
                          <span className="text-blue-400">Tool:</span>{" "}
                          <span className="text-gray-300">
                            {step.tool_name}
                          </span>
                        </div>
                      )}
                      {step.tool_error && (
                        <div className="mt-2 text-xs text-red-400">
                          Error: {step.tool_error}
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header with tabs */}
      <div className="p-4 border-b border-gray-700/50 flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Zap className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">Agent Process</h2>
          </div>
          <div className="text-xs text-gray-400">
            {steps.length} step{steps.length !== 1 ? "s" : ""}
          </div>
        </div>

        {/* Tab buttons */}
        <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1 mb-2">
          <button
            onClick={() => setActiveTab("current")}
            className={clsx(
              "flex-1 px-2 py-2 text-xs font-medium rounded-md transition-colors",
              "flex items-center justify-center space-x-1",
              activeTab === "current"
                ? "bg-green-500 text-white"
                : "text-gray-400 hover:text-gray-300 hover:bg-gray-700/50"
            )}
          >
            <Clock className="w-3 h-3" />
            <span>Current</span>
            <span className="text-xs bg-white/20 px-1 py-0.5 rounded">
              {steps.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("historical")}
            className={clsx(
              "flex-1 px-2 py-2 text-xs font-medium rounded-md transition-colors",
              "flex items-center justify-center space-x-1",
              activeTab === "historical"
                ? "bg-orange-500 text-white"
                : "text-gray-400 hover:text-gray-300 hover:bg-gray-700/50"
            )}
          >
            <MessageSquare className="w-3 h-3" />
            <span>History</span>
            <span className="text-xs bg-white/20 px-1 py-0.5 rounded">
              {historicalSteps.length}
            </span>
          </button>
        </div>

        {/* Sub-tabs for current steps */}
        {activeTab === "current" && (
          <div className="flex space-x-1 bg-gray-800/30 rounded-lg p-1">
            <button
              onClick={() => setActiveTab("actions")}
              className={clsx(
                "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                "flex items-center justify-center space-x-2",
                activeTab === "actions"
                  ? "bg-blue-500 text-white"
                  : "text-gray-400 hover:text-gray-300 hover:bg-gray-700/50"
              )}
            >
              <Wrench className="w-4 h-4" />
              <span>Actions</span>
              <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">
                {actions.length}
              </span>
            </button>
            <button
              onClick={() => setActiveTab("thinking")}
              className={clsx(
                "flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                "flex items-center justify-center space-x-2",
                activeTab === "thinking"
                  ? "bg-purple-500 text-white"
                  : "text-gray-400 hover:text-gray-300 hover:bg-gray-700/50"
              )}
            >
              <Brain className="w-4 h-4" />
              <span>Thinking</span>
              <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">
                {thinking.length}
              </span>
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-4 min-h-0 scroll-smooth"
        onScroll={checkScrollable}
      >
        {activeTab === "historical" ? (
          historicalSteps.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No historical steps</p>
              <p className="text-gray-500 text-xs mt-1">
                Previous agent processes will appear here
              </p>
            </div>
          ) : (
            renderHistoricalSteps(historicalSteps)
          )
        ) : activeTab === "actions" ? (
          actions.length === 0 ? (
            <div className="text-center py-8">
              <Wrench className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No actions yet</p>
              <p className="text-gray-500 text-xs mt-1">
                Tool calls and results will appear here
              </p>
            </div>
          ) : (
            renderStepsList(actions, false)
          )
        ) : thinking.length === 0 ? (
          <div className="text-center py-8">
            <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm">No thinking process yet</p>
            <p className="text-gray-500 text-xs mt-1">
              Internal reasoning will appear here
            </p>
          </div>
        ) : (
          renderStepsList(thinking, true)
        )}
      </div>

      {/* Scroll indicator gradient - only show when content is scrollable and not at bottom */}
      {showScrollIndicator && (
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-gray-800/90 to-transparent pointer-events-none transition-opacity duration-300" />
      )}
    </div>
  );
};

export default StepsPanel;
