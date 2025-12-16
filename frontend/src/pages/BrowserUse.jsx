import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Send,
  Globe,
  Loader2,
  AlertCircle,
  CheckCircle,
  X,
  Play,
  Square,
} from "lucide-react";
import toast from "react-hot-toast";

const BrowserUse = () => {
  const [task, setTask] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [browserState, setBrowserState] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, status]);

  const executeTask = async () => {
    if (!task.trim()) {
      toast.error("Please enter a task");
      return;
    }

    setIsRunning(true);
    setStatus("Starting browser task...");
    setError(null);
    setHistory([]);
    setBrowserState(null);

    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();

    try {
      // Use fetch for streaming SSE responses
      const token = localStorage.getItem("token");
      const response = await fetch("/api/browser-use/execute", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          task: task.trim(),
          stream: true,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "status") {
                setStatus(data.message);
                setHistory((prev) => [
                  ...prev,
                  {
                    type: "status",
                    message: data.message,
                    timestamp: new Date(),
                  },
                ]);
              } else if (data.type === "browser_state") {
                setBrowserState(data);
                setHistory((prev) => [
                  ...prev,
                  {
                    type: "browser_state",
                    url: data.url,
                    timestamp: new Date(),
                  },
                ]);
              } else if (data.type === "browser_action") {
                setHistory((prev) => [
                  ...prev,
                  {
                    type: "action",
                    action: data.action,
                    timestamp: new Date(),
                  },
                ]);
              } else if (data.type === "complete") {
                setStatus(data.message || "Task completed");
                setHistory((prev) => [
                  ...prev,
                  {
                    type: "complete",
                    message: data.message,
                    history: data.history,
                    details: data.details,
                    errors: data.errors,
                    timestamp: new Date(),
                  },
                ]);
                setIsRunning(false);

                // Show toast if there were errors
                if (data.errors && data.errors.length > 0) {
                  toast.error(
                    `Task completed with ${data.errors.length} error(s)`
                  );
                } else {
                  toast.success("Task completed successfully");
                }
              } else if (data.type === "error") {
                setError(data.error);
                setStatus("Error occurred");
                setHistory((prev) => [
                  ...prev,
                  {
                    type: "error",
                    error: data.error,
                    timestamp: new Date(),
                  },
                ]);
                setIsRunning(false);
                toast.error(`Browser task error: ${data.error}`);
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }
      }
    } catch (error) {
      if (error.name === "AbortError") {
        setStatus("Task cancelled");
        toast.info("Browser task cancelled");
      } else {
        const errorMessage =
          error.response?.data?.detail || error.message || "Unknown error";
        setError(errorMessage);
        setStatus("Error occurred");
        toast.error(`Failed to execute task: ${errorMessage}`);
      }
      setIsRunning(false);
    }
  };

  const stopTask = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsRunning(false);
      setStatus("Task stopped");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !isRunning) {
      e.preventDefault();
      executeTask();
    }
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="glass-dark border-b border-gray-700/50 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center">
              <Globe className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Browser Automation</h1>
              <p className="text-sm text-gray-400">
                Automate browser tasks with AI
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isRunning && (
              <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/30">
                <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                <span className="text-xs text-blue-400">Running...</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Browser View / Status Area */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-6xl mx-auto space-y-4">
            {/* Browser State Display */}
            {browserState && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-dark rounded-xl p-4 border border-blue-500/30"
              >
                <div className="flex items-center space-x-2 mb-2">
                  <Globe className="w-5 h-5 text-blue-400" />
                  <span className="text-sm font-medium text-white">
                    Current URL
                  </span>
                </div>
                <p className="text-sm text-gray-300 break-all">
                  {browserState.url}
                </p>
              </motion.div>
            )}

            {/* Status Display */}
            {status && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-dark rounded-xl p-4"
              >
                <div className="flex items-center space-x-2">
                  {isRunning ? (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  ) : error ? (
                    <AlertCircle className="w-5 h-5 text-red-400" />
                  ) : (
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  )}
                  <span className="text-sm font-medium text-white">
                    {status}
                  </span>
                </div>
              </motion.div>
            )}

            {/* History / Logs */}
            {history.length > 0 && (
              <div className="glass-dark rounded-xl p-4">
                <h3 className="text-sm font-semibold text-white mb-3">
                  Task History
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {history.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`p-3 rounded-lg ${
                        item.type === "error"
                          ? "bg-red-500/10 border border-red-500/30"
                          : item.type === "complete"
                          ? "bg-green-500/10 border border-green-500/30"
                          : "bg-gray-700/30"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm text-gray-300">
                            {item.message ||
                              item.action ||
                              item.error ||
                              "Processing..."}
                          </p>
                          {item.url && (
                            <p className="text-xs text-gray-400 mt-1">
                              URL: {item.url}
                            </p>
                          )}
                          {item.errors && item.errors.length > 0 && (
                            <div className="mt-2 space-y-1">
                              {item.errors.map((err, errIdx) => (
                                <p
                                  key={errIdx}
                                  className="text-xs text-red-400 bg-red-500/10 p-2 rounded"
                                >
                                  ⚠️ {err}
                                </p>
                              ))}
                            </div>
                          )}
                          {item.details && item.details.length > 0 && (
                            <div className="mt-2 space-y-1">
                              <p className="text-xs text-gray-400 font-semibold">
                                Steps:
                              </p>
                              {item.details.map((detail, detailIdx) => (
                                <div
                                  key={detailIdx}
                                  className={`text-xs p-2 rounded ${
                                    detail.error
                                      ? "text-red-400 bg-red-500/10"
                                      : detail.success
                                      ? "text-green-400 bg-green-500/10"
                                      : "text-gray-400 bg-gray-700/30"
                                  }`}
                                >
                                  Step {detail.step}:{" "}
                                  {detail.error
                                    ? `Error: ${detail.error}`
                                    : detail.success
                                    ? "Success"
                                    : "In progress"}
                                </div>
                              ))}
                            </div>
                          )}
                          {item.history && (
                            <details className="mt-2">
                              <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
                                Show full history
                              </summary>
                              <pre className="text-xs text-gray-400 mt-2 whitespace-pre-wrap bg-gray-800/50 p-2 rounded max-h-40 overflow-y-auto">
                                {item.history}
                              </pre>
                            </details>
                          )}
                        </div>
                        <span className="text-xs text-gray-500 ml-2">
                          {item.timestamp?.toLocaleTimeString()}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div ref={messagesEndRef} />
              </div>
            )}

            {/* Empty State */}
            {history.length === 0 && !isRunning && (
              <div className="flex flex-col items-center justify-center h-full py-12">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-400/20 to-blue-600/20 flex items-center justify-center mb-4">
                  <Globe className="w-12 h-12 text-blue-400" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  Ready to automate
                </h3>
                <p className="text-gray-400 text-center max-w-md">
                  Enter a task below and watch the AI agent perform it in the
                  browser. Examples: "Search for Python tutorials", "Find the
                  weather in New York", "Open GitHub and search for React
                  projects"
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="glass-dark border-t border-gray-700/50 px-6 py-4 flex-shrink-0">
          <div className="max-w-6xl mx-auto">
            <div className="flex items-end space-x-3">
              <div className="flex-1">
                <textarea
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter a browser task (e.g., 'Search for Python tutorials on YouTube')"
                  className="input-glass text-white w-full min-h-[80px] max-h-[200px] resize-y"
                  disabled={isRunning}
                />
              </div>
              <div className="flex flex-col space-y-2">
                {isRunning ? (
                  <button
                    onClick={stopTask}
                    className="px-6 py-3 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all duration-200 flex items-center space-x-2 disabled:opacity-50"
                  >
                    <Square className="w-5 h-5" />
                    <span>Stop</span>
                  </button>
                ) : (
                  <button
                    onClick={executeTask}
                    disabled={!task.trim()}
                    className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all duration-200 flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play className="w-5 h-5" />
                    <span>Run Task</span>
                  </button>
                )}
              </div>
            </div>
            {error && (
              <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-red-400 font-medium">Error</p>
                    <p className="text-sm text-red-300 mt-1">{error}</p>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    className="text-red-400 hover:text-red-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BrowserUse;
