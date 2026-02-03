import React, { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./stores/authStore";
import { useThemeStore } from "./stores/themeStore";

// Pages
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";
import Tools from "./pages/Tools";
import Documents from "./pages/Documents";
import BrowserUse from "./pages/BrowserUse";
import AddTool from "./pages/AddTool";
import EditTool from "./pages/EditTool";
import MCPServers from "./pages/MCPServers";

// Components
import PrivateRoute from "./components/PrivateRoute";
import Layout from "./components/Layout";

function App() {
  console.log("App component rendering");

  // Wrap store access in try-catch
  let authStore = null;
  let themeStore = null;
  try {
    authStore = useAuthStore();
    themeStore = useThemeStore();
    console.log("Stores initialized:", { authStore, themeStore });
  } catch (error) {
    console.error("Error initializing stores:", error);
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="glass-dark rounded-2xl p-8 max-w-2xl w-full">
          <h1 className="text-2xl font-bold text-red-500 mb-4">
            Store Initialization Error
          </h1>
          <pre className="text-white overflow-auto p-4 bg-gray-800 rounded">
            {error.toString()}
          </pre>
        </div>
      </div>
    );
  }

  const { checkAuth } = authStore;
  const { theme } = themeStore;

  useEffect(() => {
    console.log("App useEffect running");
    const initializeApp = async () => {
      try {
        // Check if user is authenticated on mount
        await checkAuth();

        // Apply theme
        if (theme === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      } catch (error) {
        console.error("Error in useEffect:", error);
      }
    };

    initializeApp();
  }, [checkAuth, theme]);

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: theme === "dark" ? "#1f2937" : "#ffffff",
            color: theme === "dark" ? "#f3f4f6" : "#111827",
            border: `1px solid ${theme === "dark" ? "#374151" : "#e5e7eb"}`,
            borderRadius: "0.75rem",
            backdropFilter: "blur(10px)",
          },
        }}
      />

      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        <Route element={<PrivateRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat/:conversationId" element={<Chat />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/browser-use" element={<BrowserUse />} />
            <Route path="/add-tool" element={<AddTool />} />
            <Route path="/edit-tool/:toolId" element={<EditTool />} />
            <Route path="/mcp-servers" element={<MCPServers />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;
