import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Users as UsersIcon,
  Plus,
  Trash2,
  Shield,
  UserCheck,
  UserX,
  Mail,
  Calendar,
  Loader2,
  X,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";

const Users = ({ embedded = false }) => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  useEffect(() => {
    if (!embedded && user && !user.is_superuser) {
      toast.error("Admin access required");
      navigate("/chat", { replace: true });
    }
  }, [embedded, user, navigate]);
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    username: "",
    email: "",
    password: "",
    full_name: "",
    is_superuser: false,
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get("/auth/users");
      setUsers(response.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error("Admin access required");
      } else {
        toast.error(error.response?.data?.detail || "Failed to load users");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (user) => {
    if (user.is_superuser && users.filter((u) => u.is_superuser).length <= 1) {
      toast.error("Cannot delete the last admin");
      return;
    }
    if (!window.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return;
    setDeletingId(user.id);
    try {
      await axios.delete(`/auth/users/${user.id}`);
      toast.success("User deleted");
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete user");
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (!createForm.username.trim() || !createForm.email.trim() || !createForm.password) {
      toast.error("Username, email and password are required");
      return;
    }
    setCreateSubmitting(true);
    try {
      await axios.post("/auth/users", {
        username: createForm.username.trim(),
        email: createForm.email.trim(),
        password: createForm.password,
        full_name: createForm.full_name.trim() || null,
        is_superuser: createForm.is_superuser,
      });
      toast.success("User created");
      setShowCreateModal(false);
      setCreateForm({ username: "", email: "", password: "", full_name: "", is_superuser: false });
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create user");
    } finally {
      setCreateSubmitting(false);
    }
  };

  return (
    <div className={embedded ? "flex flex-col" : "h-full flex flex-col p-6 overflow-auto"}>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 ${embedded ? "mb-4" : "mb-6"}`}
      >
        <div>
          <h2 className={`font-bold text-white flex items-center gap-2 ${embedded ? "text-xl" : "text-2xl"}`}>
            <UsersIcon className={embedded ? "w-5 h-5 text-primary-400" : "w-7 h-7 text-primary-400"} />
            User Management
          </h2>
          {!embedded && <p className="text-gray-400 mt-1">View, create and remove users (admin only).</p>}
        </div>
        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create user
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex-1 glass-dark rounded-xl border border-gray-700/50 overflow-hidden"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-10 h-10 text-primary-400 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-700/50 bg-white/5">
                  <th className="px-4 py-3 text-gray-400 font-medium">User</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Email</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Role</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Status</th>
                  <th className="px-4 py-3 text-gray-400 font-medium">Created</th>
                  <th className="px-4 py-3 text-gray-400 font-medium w-24">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-gray-700/30 hover:bg-white/5 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">{user.username}</span>
                        {user.full_name && (
                          <span className="text-gray-500 text-sm">({user.full_name})</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-300 flex items-center gap-2">
                      <Mail className="w-4 h-4 text-gray-500" />
                      {user.email}
                    </td>
                    <td className="px-4 py-3">
                      {user.is_superuser ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          <Shield className="w-3.5 h-3.5" />
                          Admin
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400 border border-gray-500/30">
                          <UsersIcon className="w-3.5 h-3.5" />
                          User
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {user.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400">
                          <UserCheck className="w-4 h-4" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-500">
                          <UserX className="w-4 h-4" /> Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 flex items-center gap-1">
                      <Calendar className="w-4 h-4 text-gray-500" />
                      {user.created_at
                        ? new Date(user.created_at).toLocaleDateString(undefined, {
                            dateStyle: "short",
                          })
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => handleDelete(user)}
                        disabled={deletingId === user.id}
                        className="p-2 rounded-lg text-red-400 hover:bg-red-500/20 disabled:opacity-50 transition-colors"
                        title="Delete user"
                      >
                        {deletingId === user.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && !isLoading && (
              <div className="text-center py-12 text-gray-500">No users found.</div>
            )}
          </div>
        )}
      </motion.div>

      {/* Create user modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-dark rounded-xl border border-gray-700/50 w-full max-w-md shadow-xl"
          >
            <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
              <h2 className="text-lg font-semibold text-white">Create user</h2>
              <button
                type="button"
                onClick={() => !createSubmitting && setShowCreateModal(false)}
                className="p-2 rounded-lg text-gray-400 hover:bg-white/10 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Username *</label>
                <input
                  type="text"
                  value={createForm.username}
                  onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-gray-600 text-white placeholder-gray-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  placeholder="johndoe"
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Email *</label>
                <input
                  type="email"
                  value={createForm.email}
                  onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-gray-600 text-white placeholder-gray-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  placeholder="john@example.com"
                  autoComplete="email"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Password *</label>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-gray-600 text-white placeholder-gray-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Full name</label>
                <input
                  type="text"
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, full_name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-gray-600 text-white placeholder-gray-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
                  placeholder="John Doe"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="create-is-superuser"
                  checked={createForm.is_superuser}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, is_superuser: e.target.checked }))
                  }
                  className="rounded border-gray-600 bg-white/5 text-primary-500 focus:ring-primary-500"
                />
                <label htmlFor="create-is-superuser" className="text-sm text-gray-400">
                  Admin (superuser)
                </label>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => !createSubmitting && setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="flex-1 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {createSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating…
                    </>
                  ) : (
                    "Create user"
                  )}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default Users;
