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

// Components
import PrivateRoute from "./components/PrivateRoute";
import Layout from "./components/Layout";

function App() {
  const { checkAuth } = useAuthStore();
  const { theme } = useThemeStore();

  useEffect(() => {
    // Check if user is authenticated on mount
    checkAuth();

    // Apply theme
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
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
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default App;
