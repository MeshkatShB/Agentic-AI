import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Clock,
  Trash2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Calendar,
  Zap,
  Filter,
  Bell,
  Check,
  Repeat,
  History,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";

const CronJobs = () => {
  const [jobs, setJobs] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [jobTypeFilter, setJobTypeFilter] = useState("");
  const [deletingId, setDeletingId] = useState(null);
  const [runsForId, setRunsForId] = useState(null);
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    loadJobs();
  }, [statusFilter, jobTypeFilter]);

  const loadJobs = async () => {
    try {
      setIsLoading(true);
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (jobTypeFilter) params.job_type = jobTypeFilter;
      const response = await axios.get("/cron-jobs/", { params });
      setJobs(response.data);
      loadNotifications();
    } catch (error) {
      console.error("Failed to load cron jobs:", error);
      toast.error("Failed to load cron jobs");
    } finally {
      setIsLoading(false);
    }
  };

  const loadNotifications = async () => {
    try {
      const response = await axios.get("/cron-jobs/notifications", {
        params: { limit: 20 },
      });
      setNotifications(response.data);
    } catch (error) {
      console.error("Failed to load notifications:", error);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await axios.patch(`/cron-jobs/notifications/${id}`);
      loadNotifications();
    } catch (error) {
      toast.error("Failed to mark as read");
    }
  };

  const toggleRuns = async (jobId) => {
    if (runsForId === jobId) {
      setRunsForId(null);
      setRuns([]);
      return;
    }
    try {
      const res = await axios.get(`/cron-jobs/${jobId}/runs`, {
        params: { limit: 20 },
      });
      setRunsForId(jobId);
      setRuns(res.data);
    } catch (error) {
      toast.error("Failed to load run history");
    }
  };

  const handleCancel = async (id) => {
    try {
      await axios.patch(`/cron-jobs/${id}`, { status: "cancelled" });
      toast.success("Job cancelled");
      loadJobs();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to cancel job");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this job?")) return;
    setDeletingId(id);
    try {
      await axios.delete(`/cron-jobs/${id}`);
      toast.success("Job deleted");
      loadJobs();
    } catch (error) {
      toast.error("Failed to delete job");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const statusBadge = (status) => {
    const map = {
      scheduled: {
        icon: Clock,
        label: "Scheduled",
        className: "bg-amber-500/20 text-amber-400 border-amber-500/30",
      },
      running: {
        icon: Zap,
        label: "Running",
        className: "bg-blue-500/20 text-blue-400 border-blue-500/30",
      },
      completed: {
        icon: CheckCircle,
        label: "Done",
        className: "bg-green-500/20 text-green-400 border-green-500/30",
      },
      failed: {
        icon: AlertCircle,
        label: "Failed",
        className: "bg-red-500/20 text-red-400 border-red-500/30",
      },
      cancelled: {
        icon: XCircle,
        label: "Cancelled",
        className: "bg-gray-500/20 text-gray-400 border-gray-500/30",
      },
    };
    const c = map[status] || {
      icon: AlertCircle,
      label: status,
      className: "bg-gray-500/20 text-gray-400",
    };
    const Icon = c.icon;
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${c.className}`}
      >
        <Icon className="w-3.5 h-3.5" />
        {c.label}
      </span>
    );
  };

  const jobTypeLabel = (type) => {
    const labels = { reminder: "Reminder", notification: "Notification" };
    return labels[type] || type;
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Cron Jobs</h1>
          <p className="text-gray-400">
            Background jobs created by the chatbot (e.g. &quot;remind me to X on
            Friday at 5pm&quot;). When due, reminders are delivered here in-app
            and to Telegram if you&apos;ve paired in Settings → Telegram.
          </p>
          <p className="text-gray-500 text-sm mt-2">
            Reminders run at the scheduled time only while the app server is
            running. If the server was stopped at that time, they run when you
            next start it.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <span className="text-sm text-gray-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-glass text-white text-sm py-1.5 px-3 rounded-lg"
            >
              <option value="">All</option>
              <option value="scheduled">Scheduled</option>
              <option value="running">Running</option>
              <option value="completed">Done</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Type:</span>
            <select
              value={jobTypeFilter}
              onChange={(e) => setJobTypeFilter(e.target.value)}
              className="input-glass text-white text-sm py-1.5 px-3 rounded-lg"
            >
              <option value="">All</option>
              <option value="reminder">Reminder</option>
              <option value="notification">Notification</option>
            </select>
          </div>
        </div>

        {notifications.length > 0 && (
          <div className="glass-dark rounded-xl overflow-hidden mb-6">
            <h2 className="text-lg font-semibold text-white px-4 py-3 border-b border-gray-700/50 flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary-400" />
              Delivered to you
            </h2>
            <ul className="divide-y divide-gray-700/50">
              {notifications.map((n) => (
                <li
                  key={n.id}
                  className={`p-4 hover:bg-white/5 transition-colors ${
                    !n.read_at ? "bg-primary-500/5" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-white">{n.title}</p>
                      {n.body && (
                        <p className="text-sm text-gray-400 mt-1">{n.body}</p>
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {formatDate(n.created_at)}
                      </p>
                    </div>
                    {!n.read_at && (
                      <button
                        type="button"
                        onClick={() => handleMarkRead(n.id)}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-primary-400 hover:bg-primary-500/20 rounded"
                        title="Mark as read"
                      >
                        <Check className="w-4 h-4" />
                        Mark read
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="glass-dark rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-400">
              Loading cron jobs…
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No cron jobs. Ask the chatbot to schedule something, e.g.
              &quot;Remind me to call John on Friday at 3pm&quot;.
            </div>
          ) : (
            <ul className="divide-y divide-gray-700/50">
              {jobs.map((j) => (
                <li
                  key={j.id}
                  className="p-4 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-white">
                          {j.title}
                        </span>
                        {statusBadge(j.status)}
                        <span className="text-xs text-gray-500">
                          {jobTypeLabel(j.job_type)}
                        </span>
                        {(j.source === "telegram" || j.source === "chat") && (
                          <span className="text-xs text-gray-500">
                            ({j.source})
                          </span>
                        )}
                        {j.cron_expression && (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs border bg-blue-500/20 text-blue-400 border-blue-500/30"
                            title={`Cron: ${j.cron_expression}${
                              j.schedule_timezone
                                ? ` (${j.schedule_timezone})`
                                : ""
                            }`}
                          >
                            <Repeat className="w-3.5 h-3.5" />
                            Recurring
                          </span>
                        )}
                      </div>
                      {j.cron_expression && (
                        <p className="text-xs text-gray-500 mt-1">
                          Cron: {j.cron_expression}
                          {j.schedule_timezone && ` · ${j.schedule_timezone}`}
                        </p>
                      )}
                      {j.payload?.body && (
                        <p className="text-sm text-gray-400 mt-1">
                          {j.payload.body}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
                        <Calendar className="w-4 h-4" />
                        Next run: {formatDate(j.next_run_at)}
                        {j.completed_at && (
                          <>
                            <span>· Done {formatDate(j.completed_at)}</span>
                          </>
                        )}
                        {j.error_message && (
                          <span className="text-amber-400/90 text-xs block mt-1">
                            {j.error_message}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => toggleRuns(j.id)}
                        className="p-2 text-gray-400 hover:bg-white/10 rounded-lg"
                        title="Run history"
                      >
                        <History className="w-5 h-5" />
                      </button>
                      {j.status === "scheduled" && (
                        <button
                          type="button"
                          onClick={() => handleCancel(j.id)}
                          className="p-2 text-amber-400 hover:bg-amber-500/20 rounded-lg"
                          title="Cancel job"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDelete(j.id)}
                        disabled={deletingId === j.id}
                        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg disabled:opacity-50"
                        title="Delete"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                  {runsForId === j.id && runs.length > 0 && (
                    <div className="mt-2 pl-4 border-l-2 border-gray-600">
                      <p className="text-xs font-medium text-gray-400 mb-1">
                        Run history
                      </p>
                      <ul className="space-y-1 text-xs text-gray-500">
                        {runs.map((r) => (
                          <li key={r.id} className="flex items-center gap-2">
                            {r.success ? (
                              <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                            ) : (
                              <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                            )}
                            {formatDate(r.run_at)}
                            {r.error_message && (
                              <span
                                className="text-amber-400 truncate"
                                title={r.error_message}
                              >
                                · {r.error_message}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="text-sm text-gray-500 mt-4">
          Enable the &quot;schedule_job&quot; tool in Chat (Tools / AI Settings)
          and ask e.g. &quot;Remind me to buy milk tomorrow at 9am&quot;.
        </p>
      </div>
    </div>
  );
};

export default CronJobs;
