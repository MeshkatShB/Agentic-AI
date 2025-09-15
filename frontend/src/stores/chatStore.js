import { create } from "zustand";
import axios from "axios";
import toast from "react-hot-toast";

export const useChatStore = create((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  isStreaming: false,
  streamingMessage: "",
  currentSteps: [],

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

  loadConversation: async (conversationId) => {
    set({ isLoading: true });
    try {
      const response = await axios.get(`/chat/conversations/${conversationId}`);
      const { conversation, messages } = response.data;

      set({
        currentConversation: conversation,
        messages,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      toast.error("Failed to load conversation");
    }
  },

  sendMessage: async (conversationId, content) => {
    if (!content.trim()) return;

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isStreaming: true,
      streamingMessage: "",
      currentSteps: [],
    }));

    try {
      const response = await fetch(
        `/api/chat/conversations/${conversationId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({ content, stream: true }),
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

              if (data.type === "token") {
                set((state) => ({
                  streamingMessage: state.streamingMessage + data.content,
                }));
              } else if (data.type === "step") {
                set((state) => ({
                  currentSteps: [...state.currentSteps, data.step],
                }));
              } else if (data.type === "permission_request") {
                // Handle permission request
                const approved = await get().requestPermission(data);
                // Send approval response (in real implementation)
              } else if (data.type === "complete") {
                const assistantMessage = {
                  id: Date.now() + 1,
                  role: "assistant",
                  content: data.response.final_answer,
                  steps: data.response.steps,
                  created_at: new Date().toISOString(),
                };

                set((state) => ({
                  messages: [...state.messages, assistantMessage],
                  isStreaming: false,
                  streamingMessage: "",
                  currentSteps: [],
                }));
              } else if (data.type === "error") {
                toast.error(data.error);
                set({
                  isStreaming: false,
                  streamingMessage: "",
                  currentSteps: [],
                });
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e);
            }
          }
        }
      }
    } catch (error) {
      set({ isStreaming: false, streamingMessage: "", currentSteps: [] });
      toast.error("Failed to send message");
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
