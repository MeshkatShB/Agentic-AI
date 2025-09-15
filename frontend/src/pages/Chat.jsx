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
} from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import ConversationList from "../components/ConversationList";
import MessageList from "../components/MessageList";
import StepsPanel from "../components/StepsPanel";
import PermissionDialog from "../components/PermissionDialog";
import toast from "react-hot-toast";

const Chat = () => {
  const { conversationId } = useParams();
  const {
    currentConversation,
    messages,
    isStreaming,
    streamingMessage,
    currentSteps,
    loadConversation,
    createConversation,
    sendMessage,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [showSteps, setShowSteps] = useState(true);
  const [showPermissionDialog, setShowPermissionDialog] = useState(false);
  const [permissionRequest, setPermissionRequest] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    }
  }, [conversationId, loadConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    let targetConversation = currentConversation;
    if (!targetConversation) {
      targetConversation = await createConversation();
      if (!targetConversation) {
        toast.error("Failed to create conversation");
        return;
      }
    }

    const message = input;
    setInput("");
    await sendMessage(targetConversation.id, message);
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePermissionResponse = (approved) => {
    // Handle permission response
    setShowPermissionDialog(false);
    setPermissionRequest(null);
    // Send response to backend
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
          </div>

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

        <div className="flex-1 flex overflow-hidden">
          {/* Messages area */}
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
              />
              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="p-6 glass-dark border-t border-gray-700/50">
              <div className="flex items-end space-x-3">
                <div className="flex-1">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask me anything..."
                    disabled={isStreaming}
                    rows={1}
                    className="w-full px-4 py-3 rounded-xl bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition-all duration-200 disabled:opacity-50"
                    style={{
                      minHeight: "48px",
                      maxHeight: "120px",
                    }}
                  />
                </div>
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="p-3 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  <Send className="w-5 h-5" />
                </button>
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
                className="glass-dark border-l border-gray-700/50"
              >
                <StepsPanel steps={currentSteps} />
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
