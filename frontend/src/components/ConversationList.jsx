import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  MoreVertical,
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
  } = useChatStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [filteredConversations, setFilteredConversations] = useState([]);

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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700/50">
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
      <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
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
                      <h3
                        className={clsx(
                          "font-medium truncate",
                          isActive ? "text-primary-400" : "text-gray-200"
                        )}
                      >
                        {conv.title}
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">
                        {conv.total_messages} messages •{" "}
                        {format(new Date(conv.created_at), "MMM d")}
                      </p>
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all duration-200"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
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
    </div>
  );
};

export default ConversationList;
