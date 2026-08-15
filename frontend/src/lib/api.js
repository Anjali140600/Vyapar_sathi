import axios from "axios";

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL?.trim();

const api = axios.create({
  baseURL: configuredApiUrl
    ? configuredApiUrl.replace(/\/$/, "")
    : window.location.origin,
});

api.interceptors.request.use((config) => {
  config.headers["ngrok-skip-browser-warning"] = "true";
  const token = localStorage.getItem("vyaparSathiAuthToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  register: (payload) => api.post("/api/auth/register", payload),
  login: (payload) =>
    api.post("/api/auth/login", new URLSearchParams(payload), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  logout: () => api.post("/api/auth/logout"),
};

export const transactionApi = {
  getTypes: () => api.get("/api/transaction-types"),
  list: () => api.get("/api/transactions"),
  create: (payload) => api.post("/api/transactions", payload),
  update: (id, payload) => api.put(`/api/transactions/${id}`, payload),
  remove: (id) => api.delete(`/api/transactions/${id}`),
  summary: () => api.get("/api/dashboard/summary"),
};

export const chatApi = {
  send: (payload) => api.post("/api/chat", payload),
  sessions: () => api.get("/api/chat/sessions"),
  history: (sessionId) => api.get(`/api/chat/history/${sessionId}`),
  delete: (sessionId) => api.delete(`/api/chat/${sessionId}`),
};

export const multimodalApi = {
  // ── existing upload-then-process flow ──────────────────────────────────
  upload: (file, sessionId = "") => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/api/upload?sessionId=${sessionId}`, formData);
  },
  ocr: (fileId) => api.post(`/api/ocr?fileId=${fileId}`),
  stt: (fileId) => api.post(`/api/stt?fileId=${fileId}`),

  // ── step-2 style: direct input endpoints (no prior upload needed) ──────
  /** Text pass-through → {recognizedText} */
  inputText: (text) => api.post("/api/input/text", { text }),

  /**
   * Send raw audio Blob (from browser MediaRecorder) directly to Whisper.
   * @param {Blob} blob  - audio/webm or audio/mp4
   * @param {string} filename - e.g. "recording.webm"
   */
  inputVoice: (blob, filename = "recording.webm") => {
    const formData = new FormData();
    formData.append("audio", blob, filename);
    return api.post("/api/input/voice", formData);
  },

  /**
   * Send raw image File directly to Tesseract OCR.
   * @param {File} file
   */
  inputImage: (file) => {
    const formData = new FormData();
    formData.append("image", file, file.name);
    return api.post("/api/input/image", formData);
  },

  /** Service health / config */
  health: () => api.get("/api/multimodal/health"),
};

export default api;
