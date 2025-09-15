import { create } from "zustand";
import axios from "axios";
import toast from "react-hot-toast";

const API_URL = "/api";

// Configure axios defaults
axios.defaults.baseURL = API_URL;
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const useAuthStore = create((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,

  checkAuth: () => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("user");

    if (token && user) {
      set({
        token,
        user: JSON.parse(user),
        isAuthenticated: true,
      });
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }
  },

  login: async (username, password) => {
    set({ isLoading: true });
    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await axios.post("/auth/login", formData);
      const { access_token, user } = response.data;

      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));
      axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      });

      toast.success("Welcome back!");
      return true;
    } catch (error) {
      set({ isLoading: false });
      toast.error(error.response?.data?.detail || "Login failed");
      return false;
    }
  },

  signup: async (userData) => {
    set({ isLoading: true });
    try {
      const response = await axios.post("/auth/signup", userData);
      const user = response.data;

      toast.success("Account created! Please login.");
      set({ isLoading: false });
      return true;
    } catch (error) {
      set({ isLoading: false });
      toast.error(error.response?.data?.detail || "Signup failed");
      return false;
    }
  },

  logout: async () => {
    try {
      await axios.post("/auth/logout");
    } catch (error) {
      // Ignore logout errors
    }

    localStorage.removeItem("token");
    localStorage.removeItem("user");
    delete axios.defaults.headers.common["Authorization"];

    set({
      user: null,
      token: null,
      isAuthenticated: false,
    });

    toast.success("Logged out successfully");
  },

  updateProfile: async (updates) => {
    try {
      const response = await axios.put("/auth/me", updates);
      const user = response.data;

      localStorage.setItem("user", JSON.stringify(user));
      set({ user });

      toast.success("Profile updated");
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || "Update failed");
      return false;
    }
  },

  changePassword: async (oldPassword, newPassword) => {
    try {
      await axios.post("/auth/change-password", {
        old_password: oldPassword,
        new_password: newPassword,
      });

      toast.success("Password changed successfully");
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || "Password change failed");
      return false;
    }
  },
}));
