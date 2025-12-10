import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Plus,
  Search,
  Trash2,
  ChevronRight,
  Zap,
  AlertCircle,
  CheckCircle,
  Clock,
  Bot,
  Edit2,
  Check,
  X,
  Wrench,
  Square,
  Paperclip,
  File,
} from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import ConversationList from "../components/ConversationList";
import MessageList from "../components/MessageList";
import StepsPanel from "../components/StepsPanel";
import PermissionDialog from "../components/PermissionDialog";
import ToolSelector from "../components/ToolSelector";
import toast from "react-hot-toast";

const Chat = () => {
  const { conversationId } = useParams();
  const {
    currentConversation,
    messages,
    historicalSteps,
    isStreaming,
    streamingMessage,
    currentSteps,
    activeFiles,
    loadConversation,
    createConversation,
    sendMessage,
    updateConversation,
    stopStreaming,
    uploadFile,
    loadActiveFiles,
    deleteFileAttachment,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [showSteps, setShowSteps] = useState(true);
  const [showPermissionDialog, setShowPermissionDialog] = useState(false);
  const [permissionRequest, setPermissionRequest] = useState(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState("");
  const [selectedTools, setSelectedTools] = useState([]);
  const [useDeepAgent, setUseDeepAgent] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const fileInputRef = useRef(null);

  // Function to detect RTL text (Persian, Arabic, Hebrew, etc.)
  const isRTL = (text) => {
    if (!text) return false;
    // RTL Unicode ranges: Arabic (0600-06FF), Persian (0600-06FF), Hebrew (0590-05FF)
    const rtlRegex =
      /[\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return rtlRegex.test(text);
  };
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation]);

  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom();
    }
  }, [messages, streamingMessage, shouldAutoScroll]);

  // Handle scroll events to determine if we should auto-scroll
  const handleScroll = () => {
    if (!messagesContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } =
      messagesContainerRef.current;
    const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 100;
    setShouldAutoScroll(isAtBottom);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    let targetConversation = currentConversation;
    if (!targetConversation) {
      targetConversation = await createConversation();
      if (!targetConversation) {
        toast.error("Failed to create conversation");
        return;
      }
    }

    // Upload and parse each file
    for (const file of files) {
      try {
        const result = await uploadFile(targetConversation.id, file);
        if (result && result.success) {
          setUploadedFiles((prev) => [
            ...prev,
            {
              id: Date.now() + Math.random(),
              filename: result.filename,
              content: result.content,
              metadata: result.metadata,
            },
          ]);
          toast.success(`File "${file.name}" uploaded successfully`);
        }
      } catch (error) {
        toast.error(`Failed to upload "${file.name}"`);
      }
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRemoveFile = (fileId) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleSend = async () => {
    if ((!input.trim() && uploadedFiles.length === 0) || isStreaming) return;

    let targetConversation = currentConversation;
    if (!targetConversation) {
      targetConversation = await createConversation();
      if (!targetConversation) {
        toast.error("Failed to create conversation");
        return;
      }
    }

    const message = input || "Please analyze the uploaded files.";
    const fileContents = uploadedFiles.map((f) => ({
      filename: f.filename,
      content: f.content,
      metadata: f.metadata,
    }));

    setInput("");
    setUploadedFiles([]);
    setShouldAutoScroll(true); // Enable auto-scroll when sending a new message

    // Send message with selected tools and file contents
    await sendMessage(
      targetConversation.id,
      message,
      selectedTools,
      useDeepAgent,
      fileContents
    );

    // Reload active files after sending
    await loadActiveFiles(targetConversation.id);
  };

  const handleStop = () => {
    stopStreaming();
    toast.success("Stopped generation");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePermissionResponse = (approved) => {
    setShowPermissionDialog(false);
    setPermissionRequest(null);
  };

  const handleTitleEditStart = () => {
    if (currentConversation) {
      setEditingTitle(true);
      setTitleValue(currentConversation.title);
    }
  };

  const handleTitleEditSave = async () => {
    if (
      currentConversation &&
      titleValue.trim() &&
      titleValue !== currentConversation.title
    ) {
      await updateConversation(currentConversation.id, {
        title: titleValue.trim(),
      });
    }
    setEditingTitle(false);
    setTitleValue("");
  };

  const handleTitleEditCancel = () => {
    setEditingTitle(false);
    setTitleValue("");
  };

  const handleTitleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleTitleEditSave();
    } else if (e.key === "Escape") {
      handleTitleEditCancel();
    }
  };

  return (
    <div className="h-full flex">
      {/* Conversations sidebar */}
      <div className="w-80 glass-dark border-r border-gray-700/50 flex flex-col">
        <ConversationList />
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Chat header */}
        <div className="h-16 glass-dark border-b border-gray-700/50 flex items-center justify-between px-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              {editingTitle && currentConversation ? (
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={titleValue}
                    onChange={(e) => setTitleValue(e.target.value)}
                    onKeyPress={handleTitleKeyPress}
                    onBlur={handleTitleEditSave}
                    className="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                    autoFocus
                  />
                  <button
                    onClick={handleTitleEditSave}
                    className="p-1 rounded hover:bg-green-500/20 text-gray-400 hover:text-green-400 transition-all duration-200"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleTitleEditCancel}
                    className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all duration-200"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="group flex items-center space-x-2">
                  <div>
                    <h2 className="font-semibold text-white">
                      {currentConversation?.title || "New Conversation"}
                    </h2>
                    <p className="text-xs text-gray-400">
                      {currentConversation
                        ? `${messages.length} messages`
                        : "Start a conversation"}
                    </p>
                  </div>
                  {currentConversation && (
                    <button
                      onClick={handleTitleEditStart}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-blue-500/20 text-gray-400 hover:text-blue-400 transition-all duration-200"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Active files indicator */}
            {activeFiles.length > 0 && (
              <div className="flex items-center space-x-1 px-2 py-1 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30">
                <File className="w-3 h-3" />
                <span className="text-xs font-medium">
                  {activeFiles.length} file{activeFiles.length !== 1 ? "s" : ""}
                </span>
              </div>
            )}

            {/* Tool selector */}
            <ToolSelector
              selectedTools={selectedTools}
              onToolsChange={setSelectedTools}
              showSteps={showSteps}
            />

            {/* Selected tools indicator */}
            {selectedTools.length > 0 && (
              <div className="flex items-center space-x-1 px-2 py-1 bg-primary-500/20 text-primary-400 rounded-lg border border-primary-500/30">
                <Wrench className="w-3 h-3" />
                <span className="text-xs font-medium">
                  {selectedTools.length} tool
                  {selectedTools.length !== 1 ? "s" : ""}
                </span>
              </div>
            )}

            {/* DeepAgent toggle */}
            <button
              onClick={() => setUseDeepAgent(!useDeepAgent)}
              className={`px-3 py-1.5 rounded-lg transition-all duration-200 ${
                useDeepAgent
                  ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                  : "text-gray-400 hover:bg-white/10"
              }`}
              title="Use DeepAgent for enhanced reasoning"
            >
              <div className="flex items-center space-x-2">
                <Bot className="w-4 h-4" />
                <span className="text-sm">DeepAgent</span>
              </div>
            </button>

            {/* Steps toggle */}
            <button
              onClick={() => setShowSteps(!showSteps)}
              className={`px-3 py-1.5 rounded-lg transition-all duration-200 ${
                showSteps
                  ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
                  : "text-gray-400 hover:bg-white/10"
              }`}
            >
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4" />
                <span className="text-sm">Steps</span>
              </div>
            </button>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Messages area */}
          <div className="flex-1 flex flex-col">
            <div
              ref={messagesContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto custom-scrollbar p-6"
            >
              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
              />
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="p-6 glass-dark border-t border-gray-700/50">
              {/* Uploaded files preview */}
              {uploadedFiles.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {uploadedFiles.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center space-x-2 px-3 py-2 bg-primary-500/20 border border-primary-500/30 rounded-lg"
                    >
                      <File className="w-4 h-4 text-primary-400" />
                      <span className="text-sm text-primary-300 max-w-[200px] truncate">
                        {file.filename}
                      </span>
                      <button
                        onClick={() => handleRemoveFile(file.id)}
                        className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-end space-x-3">
                {/* File upload button */}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".pdf,.docx,.txt,.md,.csv,.json,.xml,.html,.htm,.log"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isStreaming}
                  className="p-3 rounded-xl bg-gray-700/50 text-gray-300 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                  title="Upload file"
                >
                  <Paperclip className="w-5 h-5" />
                </button>

                <div className="flex-1">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={
                      uploadedFiles.length > 0
                        ? "Add a message or send to analyze files..."
                        : "Ask me anything..."
                    }
                    disabled={isStreaming}
                    rows={1}
                    dir={isRTL(input) ? "rtl" : "ltr"}
                    className="w-full px-4 py-3 rounded-xl bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition-all duration-200 disabled:opacity-50"
                    style={{
                      minHeight: "48px",
                      maxHeight: "120px",
                      textAlign: isRTL(input) ? "right" : "left",
                      fontFamily: isRTL(input)
                        ? "Tahoma, Arial, sans-serif"
                        : "inherit",
                    }}
                  />
                </div>
                {isStreaming ? (
                  <button
                    onClick={handleStop}
                    className="p-3 rounded-xl bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 transition-all duration-200"
                    title="Stop generation"
                  >
                    <Square className="w-5 h-5" />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() && uploadedFiles.length === 0}
                    className="p-3 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                )}
              </div>

              {/* Status indicators */}
              {isStreaming && (
                <div className="mt-3 flex items-center space-x-2 text-sm text-primary-400">
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span>AI is thinking...</span>
                </div>
              )}
            </div>
          </div>

          {/* Steps panel */}
          <AnimatePresence>
            {showSteps && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 320, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="glass-dark border-l border-gray-700/50 h-full flex flex-col"
              >
                {/* Active Files Section */}
                {activeFiles.length > 0 && (
                  <div className="p-4 border-b border-gray-700/50">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                        <File className="w-4 h-4" />
                        <span>Active Files ({activeFiles.length})</span>
                      </h3>
                    </div>
                    <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                      {activeFiles.map((file, index) => (
                        <div
                          key={`${file.filename}_${file.message_id}_${index}`}
                          className="flex items-center justify-between p-2 bg-gray-800/50 rounded-lg border border-gray-700/50"
                        >
                          <div className="flex items-center space-x-2 flex-1 min-w-0">
                            <File className="w-3 h-3 text-primary-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-white truncate">
                                {file.filename}
                              </p>
                              <p className="text-xs text-gray-400">
                                {(file.size / 1024).toFixed(1)} KB
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={async () => {
                              if (
                                await deleteFileAttachment(
                                  currentConversation.id,
                                  file.message_id,
                                  file.filename
                                )
                              ) {
                                await loadActiveFiles(
                                  currentConversation.id
                                );
                              }
                            }}
                            className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all flex-shrink-0"
                            title="Remove file"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <StepsPanel
                  steps={currentSteps}
                  historicalSteps={historicalSteps}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Permission dialog */}
      <AnimatePresence>
        {showPermissionDialog && permissionRequest && (
          <PermissionDialog
            request={permissionRequest}
            onApprove={() => handlePermissionResponse(true)}
            onDeny={() => handlePermissionResponse(false)}
            onClose={() => setShowPermissionDialog(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default Chat;
