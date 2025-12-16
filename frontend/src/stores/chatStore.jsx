import { create } from "zustand";
import axios from "axios";
import toast from "react-hot-toast";

export const useChatStore = create((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  historicalSteps: [], // Store agent steps from previous conversations
  isLoading: false,
  isStreaming: false,
  streamingMessage: "",
  currentSteps: [],
  abortController: null, // For stopping streaming requests

  loadConversations: async () => {
    set({ isLoading: true });
    try {
      const response = await axios.get("/chat/conversations");
      set({ conversations: response.data, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      toast.error("Failed to load conversations");
    }
  },

  createConversation: async (title = "New Conversation") => {
    try {
      const response = await axios.post("/chat/conversations", { title });
      const conversation = response.data;

      set((state) => ({
        conversations: [conversation, ...state.conversations],
        currentConversation: conversation,
        messages: [],
      }));

      return conversation;
    } catch (error) {
      toast.error("Failed to create conversation");
      return null;
    }
  },

  updateConversation: async (conversationId, updates) => {
    try {
      const response = await axios.put(
        `/chat/conversations/${conversationId}`,
        updates
      );
      const updatedConversation = response.data;

      set((state) => ({
        conversations: state.conversations.map((conv) =>
          conv.id === conversationId ? updatedConversation : conv
        ),
        currentConversation:
          state.currentConversation?.id === conversationId
            ? updatedConversation
            : state.currentConversation,
      }));

      toast.success("Conversation updated");
      return updatedConversation;
    } catch (error) {
      toast.error("Failed to update conversation");
      return null;
    }
  },

  loadConversation: async (conversationId) => {
    set({ isLoading: true });
    try {
      const [conversationResponse, stepsResponse] = await Promise.all([
        axios.get(`/chat/conversations/${conversationId}`),
        axios.get(`/chat/conversations/${conversationId}/steps`),
      ]);

      const { conversation, messages } = conversationResponse.data;
      const { steps } = stepsResponse.data;

      set({
        currentConversation: conversation,
        messages,
        historicalSteps: steps || [], // Store historical steps
        isLoading: false,
        currentSteps: [], // Clear current steps when loading new conversation
      });

      // Load active files for this conversation
      await get().loadActiveFiles(conversationId);
    } catch (error) {
      set({ isLoading: false });
      toast.error("Failed to load conversation");
    }
  },

  activeFiles: [],

  loadActiveFiles: async (conversationId) => {
    if (!conversationId) return;
    try {
      const response = await axios.get(
        `/chat/conversations/${conversationId}/files`
      );
      set({ activeFiles: response.data.files || [] });
    } catch (error) {
      console.error("Failed to load active files:", error);
      set({ activeFiles: [] });
    }
  },

  deleteFileAttachment: async (conversationId, messageId, filename) => {
    try {
      await axios.delete(
        `/chat/conversations/${conversationId}/files/${messageId}?filename=${encodeURIComponent(
          filename
        )}`
      );
      // Reload active files
      await get().loadActiveFiles(conversationId);
      toast.success("File removed successfully");
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to remove file");
      return false;
    }
  },

  uploadFile: async (conversationId, file) => {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        `/chat/conversations/${conversationId}/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      // Reload active files after upload
      await get().loadActiveFiles(conversationId);

      return response.data;
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload file");
      return null;
    }
  },

  sendMessage: async (
    conversationId,
    content,
    selectedTools = [],
    useDeepAgent = false,
    fileContents = []
  ) => {
    if (!content.trim() && fileContents.length === 0) return;

    // Create abort controller for this request
    const abortController = new AbortController();
    set({ abortController });

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
      timestamp: new Date().toISOString(),
    };

    // Create a placeholder for the assistant's response
    const assistantPlaceholder = {
      id: Date.now() + 1,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage, assistantPlaceholder],
      isStreaming: true,
      streamingMessage: "",
      currentSteps: [], // Reset steps for new message
    }));

    try {
      // Prepare file attachments metadata
      const fileAttachments = fileContents.map((f) => ({
        filename: f.filename,
        size: f.metadata?.file_size || 0,
        type: f.metadata?.file_type || "unknown",
      }));

      const response = await fetch(
        `/api/chat/conversations/${conversationId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({
            content,
            stream: true,
            selected_tools: selectedTools,
            use_deepagent: useDeepAgent,
            file_contents: fileContents,
            file_attachments: fileAttachments,
          }),
          signal: abortController.signal,
        }
      );

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

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
              console.log("Received event:", data.type, data);

              if (data.type === "token") {
                // Update the streaming message in the placeholder
                set((state) => {
                  const messages = [...state.messages];
                  const lastMessage = messages[messages.length - 1];
                  if (lastMessage.role === "assistant") {
                    // The token field contains the actual text, not 'content'
                    const tokenText = data.token || data.content || "";
                    if (tokenText && tokenText !== "undefined") {
                      lastMessage.content += tokenText;
                    }
                  }
                  return { messages };
                });
              } else if (data.type === "reasoning") {
                // Handle reasoning content streaming
                set((state) => {
                  const messages = [...state.messages];
                  const lastMessage = messages[messages.length - 1];
                  if (lastMessage.role === "assistant") {
                    const tokenText = data.token || data.content || "";
                    if (tokenText && tokenText !== "undefined") {
                      // Append reasoning content to the message
                      lastMessage.content += tokenText;
                    }
                  }
                  return { messages };
                });
              } else if (data.type === "step") {
                // Add new step to the steps panel
                set((state) => ({
                  currentSteps: [...state.currentSteps, data.step],
                }));
              } else if (data.type === "permission_request") {
                // Handle permission request
                const approved = await get().requestPermission(data);
                // Send approval response (in real implementation)
              } else if (data.type === "title_update") {
                // Update conversation title
                set((state) => {
                  const updatedConversations = state.conversations.map((conv) =>
                    conv.id === data.conversation_id
                      ? { ...conv, title: data.title }
                      : conv
                  );
                  const updatedCurrentConversation =
                    state.currentConversation?.id === data.conversation_id
                      ? { ...state.currentConversation, title: data.title }
                      : state.currentConversation;
                  return {
                    conversations: updatedConversations,
                    currentConversation: updatedCurrentConversation,
                  };
                });
              } else if (data.type === "complete") {
                // Update the final answer
                console.log("Complete event received:", data);
                console.log(
                  "Full response object:",
                  JSON.stringify(data.response, null, 2)
                );
                console.log("Final answer:", data.response?.final_answer);
                set((state) => {
                  const messages = [...state.messages];
                  const lastMessage = messages[messages.length - 1];
                  console.log("Last message before update:", lastMessage);
                  if (lastMessage && lastMessage.role === "assistant") {
                    const finalAnswer =
                      data.response?.final_answer || "No response received";
                    console.log("Setting final answer:", finalAnswer);
                    lastMessage.content = finalAnswer;
                    lastMessage.created_at = new Date().toISOString();
                    lastMessage.timestamp = new Date().toISOString();
                  }
                  console.log("Messages after update:", messages);
                  return {
                    messages,
                    isStreaming: false,
                    streamingMessage: "",
                    abortController: null,
                  };
                });
              } else if (data.type === "error") {
                toast.error(data.error);
                set((state) => {
                  const messages = state.messages.slice(0, -1); // Remove placeholder
                  return {
                    messages,
                    isStreaming: false,
                    streamingMessage: "",
                    abortController: null,
                  };
                });
              } else if (data.type === "cancelled") {
                // Handle cancellation
                set((state) => {
                  const messages = [...state.messages];
                  const lastMessage = messages[messages.length - 1];
                  if (lastMessage && lastMessage.role === "assistant") {
                    lastMessage.content += "\n\n[Generation stopped by user]";
                  }
                  return {
                    messages,
                    isStreaming: false,
                    streamingMessage: "",
                    abortController: null,
                  };
                });
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e);
            }
          }
        }
      }

      // Stream ended - ensure streaming state is reset
      set((state) => ({
        isStreaming: false,
        streamingMessage: "",
        abortController: null,
      }));
    } catch (error) {
      // Don't show error if it was aborted (user stopped)
      if (error.name !== "AbortError") {
        set((state) => {
          const messages = state.messages.slice(0, -1); // Remove placeholder on error
          return {
            messages,
            isStreaming: false,
            streamingMessage: "",
            abortController: null,
          };
        });
        toast.error("Failed to send message");
      } else {
        // User stopped the request
        set((state) => {
          const messages = [...state.messages];
          const lastMessage = messages[messages.length - 1];
          if (lastMessage && lastMessage.role === "assistant") {
            lastMessage.content += "\n\n[Generation stopped by user]";
          }
          return {
            messages,
            isStreaming: false,
            streamingMessage: "",
            abortController: null,
          };
        });
      }
    }
  },

  stopStreaming: () => {
    const { abortController } = get();
    if (abortController) {
      abortController.abort();
      set({
        isStreaming: false,
        streamingMessage: "",
        abortController: null,
      });
    }
  },

  requestPermission: async (permissionData) => {
    // In a real implementation, this would show a modal
    // For now, auto-approve after showing a toast
    toast(
      (t) => (
        <div>
          <p className="font-semibold">Tool Permission Request</p>
          <p className="text-sm">{permissionData.description}</p>
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => {
                toast.dismiss(t.id);
                return true;
              }}
              className="px-3 py-1 bg-green-500 text-white rounded"
            >
              Allow
            </button>
            <button
              onClick={() => {
                toast.dismiss(t.id);
                return false;
              }}
              className="px-3 py-1 bg-red-500 text-white rounded"
            >
              Deny
            </button>
          </div>
        </div>
      ),
      { duration: 10000 }
    );

    return true; // Auto-approve for now
  },

  deleteConversation: async (conversationId) => {
    try {
      await axios.delete(`/chat/conversations/${conversationId}`);

      set((state) => ({
        conversations: state.conversations.filter(
          (c) => c.id !== conversationId
        ),
        currentConversation:
          state.currentConversation?.id === conversationId
            ? null
            : state.currentConversation,
        messages:
          state.currentConversation?.id === conversationId
            ? []
            : state.messages,
      }));

      toast.success("Conversation deleted");
    } catch (error) {
      toast.error("Failed to delete conversation");
    }
  },

  searchConversation: async (conversationId, query) => {
    try {
      const response = await axios.post(
        `/chat/conversations/${conversationId}/search`,
        null,
        { params: { query } }
      );
      return response.data.results;
    } catch (error) {
      toast.error("Search failed");
      return [];
    }
  },
}));
