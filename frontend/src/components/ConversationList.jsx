import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  MoreVertical,
  Edit2,
  Check,
  X,
} from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { format } from "date-fns";
import clsx from "clsx";

const ConversationList = () => {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const {
    conversations,
    loadConversations,
    createConversation,
    deleteConversation,
    updateConversation,
  } = useChatStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [filteredConversations, setFilteredConversations] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);
  const contentRef = React.useRef(null);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    if (searchQuery) {
      const filtered = conversations.filter((conv) =>
        conv.title.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredConversations(filtered);
    } else {
      setFilteredConversations(conversations);
    }
  }, [searchQuery, conversations]);

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
  useEffect(() => {
    checkScrollable();
  }, [filteredConversations, checkScrollable]);

  const handleNewConversation = async () => {
    const conversation = await createConversation();
    if (conversation) {
      navigate(`/chat/${conversation.id}`);
    }
  };

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation();
    await deleteConversation(convId);
    if (conversationId === String(convId)) {
      navigate("/chat");
    }
  };

  const handleEditStart = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditingTitle(conv.title);
  };

  const handleEditSave = async (e, convId) => {
    e.stopPropagation();
    if (
      editingTitle.trim() &&
      editingTitle !== conversations.find((c) => c.id === convId)?.title
    ) {
      await updateConversation(convId, { title: editingTitle.trim() });
    }
    setEditingId(null);
    setEditingTitle("");
  };

  const handleEditCancel = (e) => {
    e.stopPropagation();
    setEditingId(null);
    setEditingTitle("");
  };

  const handleKeyPress = (e, convId) => {
    if (e.key === "Enter") {
      handleEditSave(e, convId);
    } else if (e.key === "Escape") {
      handleEditCancel(e);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden relative">
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50 flex-shrink-0">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all duration-200"
        >
          <Plus className="w-5 h-5" />
          <span className="font-medium">New Chat</span>
        </button>

        {/* Search */}
        <div className="mt-3 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-9 pr-3 py-2 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Conversations list */}
      <div
        ref={contentRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-2 min-h-0 scroll-smooth"
        onScroll={checkScrollable}
      >
        {filteredConversations.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm">No conversations yet</p>
            <p className="text-gray-500 text-xs mt-1">
              Start a new chat to begin
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {filteredConversations.map((conv) => {
              const isActive = conversationId === String(conv.id);

              return (
                <motion.div
                  key={conv.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  whileHover={{ x: 4 }}
                  onClick={() => navigate(`/chat/${conv.id}`)}
                  className={clsx(
                    "group relative p-3 rounded-lg cursor-pointer transition-all duration-200",
                    isActive
                      ? "bg-primary-500/20 border border-primary-500/30"
                      : "hover:bg-white/5"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {editingId === conv.id ? (
                        <input
                          type="text"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyPress={(e) => handleKeyPress(e, conv.id)}
                          onBlur={(e) => handleEditSave(e, conv.id)}
                          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : (
                        <h3
                          className={clsx(
                            "font-medium truncate",
                            isActive ? "text-primary-400" : "text-gray-200"
                          )}
                        >
                          {conv.title}
                        </h3>
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {conv.total_messages} messages •{" "}
                        {format(new Date(conv.created_at), "MMM d")}
                      </p>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center space-x-1">
                      {editingId === conv.id ? (
                        <>
                          <button
                            onClick={(e) => handleEditSave(e, conv.id)}
                            className="p-1 rounded hover:bg-green-500/20 text-gray-400 hover:text-green-400 transition-all duration-200"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={handleEditCancel}
                            className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all duration-200"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={(e) => handleEditStart(e, conv)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-blue-500/20 text-gray-400 hover:text-blue-400 transition-all duration-200"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) =>
                              handleDeleteConversation(e, conv.id)
                            }
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all duration-200"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary-500 rounded-r" />
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Scroll indicator gradient - only show when content is scrollable and not at bottom */}
      {showScrollIndicator && (
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-gray-800/90 to-transparent pointer-events-none transition-opacity duration-300" />
      )}
    </div>
  );
};

export default ConversationList;
