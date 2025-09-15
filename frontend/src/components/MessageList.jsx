import React from "react";
import { motion } from "framer-motion";
import { User, Bot, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { format } from "date-fns";
import clsx from "clsx";
import toast from "react-hot-toast";

const MessageList = ({ messages, streamingMessage, isStreaming }) => {
  const [copiedId, setCopiedId] = React.useState(null);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  const renderMessage = (message, index) => {
    const isUser = message.role === "user";
    const content = message.content;

    return (
      <motion.div
        key={message.id || index}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.05 }}
        className={clsx(
          "flex items-start space-x-3",
          isUser ? "justify-end" : "justify-start"
        )}
      >
        {!isUser && (
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
        )}

        <div
          className={clsx(
            "max-w-[70%] rounded-2xl px-4 py-3",
            isUser
              ? "bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-br-sm"
              : "glass-dark border border-gray-700/50 rounded-bl-sm"
          )}
        >
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  return !inline && match ? (
                    <div className="relative group">
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                      <button
                        onClick={() =>
                          copyToClipboard(String(children), `code-${index}`)
                        }
                        className="absolute top-2 right-2 p-1.5 rounded bg-gray-700/50 hover:bg-gray-600/50 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        {copiedId === `code-${index}` ? (
                          <Check className="w-4 h-4 text-green-400" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                    </div>
                  ) : (
                    <code className="px-1.5 py-0.5 rounded bg-gray-800 text-primary-400">
                      {children}
                    </code>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>

          {/* Message actions */}
          {!isUser && (
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-700/50">
              <span className="text-xs text-gray-500">
                {format(new Date(message.created_at), "HH:mm")}
              </span>
              <button
                onClick={() => copyToClipboard(content, message.id)}
                className="p-1 rounded hover:bg-white/10 transition-colors"
              >
                {copiedId === message.id ? (
                  <Check className="w-3.5 h-3.5 text-green-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-gray-400" />
                )}
              </button>
            </div>
          )}
        </div>

        {isUser && (
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-blue-400 to-cyan-400 flex items-center justify-center">
            <User className="w-5 h-5 text-white" />
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <div className="space-y-6">
      {messages.map((message, index) => renderMessage(message, index))}

      {/* Streaming message */}
      {isStreaming && streamingMessage && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start space-x-3"
        >
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>

          <div className="max-w-[70%] rounded-2xl rounded-bl-sm px-4 py-3 glass-dark border border-gray-700/50">
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{streamingMessage}</ReactMarkdown>
            </div>
            <div className="mt-2 pt-2 border-t border-gray-700/50">
              <div className="loading-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default MessageList;
