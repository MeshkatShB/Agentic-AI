import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  File,
  Loader,
} from "lucide-react";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../stores/authStore";
import { formatDistanceToNow } from "date-fns";

const Documents = () => {
  const { user } = useAuthStore();
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState(new Map()); // Track individual file uploads
  const [deletingId, setDeletingId] = useState(null);
  const [reindexingId, setReindexingId] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  // Poll for indexing status updates
  useEffect(() => {
    const hasIndexingDocs = documents.some((doc) => !doc.is_indexed);
    if (!hasIndexingDocs) return;

    const pollInterval = setInterval(() => {
      loadDocuments();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [documents]);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get("/documents/");
      setDocuments(response.data);
    } catch (error) {
      console.error("Failed to load documents:", error);
      toast.error("Failed to load documents");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    const allowedExtensions = [".pdf", ".docx", ".txt", ".md", ".html"];
    const maxSize = 50 * 1024 * 1024; // 50MB

    // Validate all files
    const validFiles = [];
    const errors = [];

    for (const file of files) {
      const fileExt = "." + file.name.split(".").pop().toLowerCase();

      if (!allowedExtensions.includes(fileExt)) {
        errors.push(`${file.name}: Unsupported file type`);
        continue;
      }

      if (file.size > maxSize) {
        errors.push(`${file.name}: File too large (max 50MB)`);
        continue;
      }

      validFiles.push(file);
    }

    // Show errors if any
    if (errors.length > 0) {
      errors.forEach((error) => toast.error(error));
    }

    // Upload valid files
    if (validFiles.length > 0) {
      await uploadDocuments(validFiles);
    }
  };

  const uploadDocuments = async (files) => {
    setIsUploading(true);
    const uploadPromises = files.map((file) => uploadDocument(file));

    try {
      await Promise.all(uploadPromises);
      toast.success(
        `Successfully uploaded ${files.length} document${
          files.length > 1 ? "s" : ""
        }. Indexing in progress...`
      );
      await loadDocuments();
    } catch (error) {
      console.error("Some uploads failed:", error);
    } finally {
      setIsUploading(false);
      setUploadingFiles(new Map());
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const uploadDocument = async (file) => {
    const fileId = `${file.name}-${file.size}-${Date.now()}`;

    try {
      // Track this file's upload
      setUploadingFiles((prev) => {
        const newMap = new Map(prev);
        newMap.set(fileId, { name: file.name, progress: 0 });
        return newMap;
      });

      const formData = new FormData();
      formData.append("file", file);

      await axios.post("/documents/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            const fileInfo = newMap.get(fileId);
            if (fileInfo) {
              newMap.set(fileId, { ...fileInfo, progress: percentCompleted });
            }
            return newMap;
          });
        },
      });

      // Remove from tracking on success
      setUploadingFiles((prev) => {
        const newMap = new Map(prev);
        newMap.delete(fileId);
        return newMap;
      });
    } catch (error) {
      console.error(`Failed to upload ${file.name}:`, error);
      const errorMessage =
        error.response?.data?.detail || `Failed to upload ${file.name}`;
      toast.error(errorMessage);

      // Remove from tracking on error
      setUploadingFiles((prev) => {
        const newMap = new Map(prev);
        newMap.delete(fileId);
        return newMap;
      });
      throw error; // Re-throw to let Promise.all handle it
    }
  };

  const handleDelete = async (documentId) => {
    if (!window.confirm("Are you sure you want to delete this document?")) {
      return;
    }

    try {
      setDeletingId(documentId);
      await axios.delete(`/documents/${documentId}`);
      toast.success("Document deleted successfully");
      await loadDocuments();
    } catch (error) {
      console.error("Failed to delete document:", error);
      toast.error("Failed to delete document");
    } finally {
      setDeletingId(null);
    }
  };

  const handleReindex = async (documentId) => {
    try {
      setReindexingId(documentId);
      await axios.post(`/documents/${documentId}/index`);
      toast.success("Document re-indexed successfully");
      await loadDocuments();
    } catch (error) {
      console.error("Failed to re-index document:", error);
      toast.error("Failed to re-index document");
    } finally {
      setReindexingId(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  const getFileIcon = (fileType) => {
    const type = fileType.toLowerCase();
    if (type === "pdf") return "📄";
    if (type === "docx") return "📝";
    if (type === "txt" || type === "md") return "📋";
    if (type === "html") return "🌐";
    return "📄";
  };

  return (
    <div className="h-full flex flex-col p-6 overflow-auto">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Documents</h1>
            <p className="text-gray-400">
              Upload and manage your documents for RAG search
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md,.html"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  <span>Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  <span>Upload Documents</span>
                </>
              )}
            </button>
            <button
              onClick={loadDocuments}
              className="p-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </motion.div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader className="w-8 h-8 animate-spin text-primary-500" />
        </div>
      ) : documents.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center h-64 glass-dark rounded-2xl p-8"
        >
          <FileText className="w-16 h-16 text-gray-500 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            No documents yet
          </h3>
          <p className="text-gray-400 mb-4 text-center">
            Upload your first document to enable RAG search through your files
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
          >
            <Upload className="w-5 h-5" />
            <span>Upload Documents</span>
          </button>
        </motion.div>
      ) : (
        <>
          {/* Show upload progress if files are being uploaded */}
          {uploadingFiles.size > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 glass-dark rounded-xl p-4"
            >
              <h3 className="text-white font-semibold mb-3">
                Uploading {uploadingFiles.size} file
                {uploadingFiles.size > 1 ? "s" : ""}...
              </h3>
              <div className="space-y-2">
                {Array.from(uploadingFiles.entries()).map(
                  ([fileId, fileInfo]) => (
                    <div key={fileId} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-300 truncate flex-1 mr-2">
                          {fileInfo.name}
                        </span>
                        <span className="text-gray-400">
                          {fileInfo.progress}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${fileInfo.progress}%` }}
                        />
                      </div>
                    </div>
                  )
                )}
              </div>
            </motion.div>
          )}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-dark rounded-xl p-4 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className="text-3xl">{getFileIcon(doc.file_type)}</div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-white font-semibold truncate">
                        {doc.original_filename}
                      </h3>
                      <p className="text-sm text-gray-400">
                        {formatFileSize(doc.file_size)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2 mb-3">
                  {doc.is_indexed ? (
                    <div className="flex items-center space-x-1 text-green-400 text-sm">
                      <CheckCircle className="w-4 h-4" />
                      <span>Indexed</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1 text-yellow-400 text-sm">
                      <AlertCircle className="w-4 h-4" />
                      <span>Indexing...</span>
                    </div>
                  )}
                </div>

                <div className="text-xs text-gray-500 mb-3">
                  Uploaded{" "}
                  {(() => {
                    // Ensure proper timezone handling
                    let dateStr = doc.created_at;
                    // If the date doesn't have timezone info, assume it's UTC
                    if (
                      !dateStr.includes("Z") &&
                      !dateStr.includes("+") &&
                      !dateStr.includes("-", 10)
                    ) {
                      dateStr = dateStr + "Z";
                    }
                    return formatDistanceToNow(new Date(dateStr), {
                      addSuffix: true,
                    });
                  })()}
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleReindex(doc.id)}
                    disabled={reindexingId === doc.id}
                    className="flex-1 flex items-center justify-center space-x-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors text-sm disabled:opacity-50"
                    title="Re-index document"
                  >
                    {reindexingId === doc.id ? (
                      <Loader className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4" />
                        <span>Re-index</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="flex items-center justify-center px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors text-sm disabled:opacity-50"
                    title="Delete document"
                  >
                    {deletingId === doc.id ? (
                      <Loader className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </>
      )}
    </div>
  );
};

export default Documents;
