import axios from "axios";

const api = axios.create({
  baseURL: window.location.origin,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("vyaparSathiAuthToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const hadToken = Boolean(localStorage.getItem("vyaparSathiAuthToken"));
    const isLoginRequest = error.config?.url?.includes("/api/auth/login");
    if (error.response?.status === 401 && hadToken && !isLoginRequest) {
      localStorage.removeItem("vyaparSathiAuthToken");
      localStorage.removeItem("vyaparSathiAuthEmail");
      localStorage.removeItem("vyaparSathiAuthRole");
      sessionStorage.setItem(
        "vyaparSathiAuthNotice",
        "Your session expired. Please log in again, then upload the bill."
      );
      if (window.location.pathname !== "/") {
        window.location.assign("/");
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  register: (payload) => api.post("/api/auth/register", payload),
  login: (payload) =>
    api.post("/api/auth/login", new URLSearchParams(payload), {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  logout: () => api.post("/api/auth/logout"),
  me: () => api.get("/api/auth/me"),
};

export const transactionApi = {
  getTypes: () => api.get("/api/transaction-types"),
  list: () => api.get("/api/transactions"),
  create: (payload) => api.post("/api/transactions", payload),
  update: (id, payload) => api.put(`/api/transactions/${id}`, payload),
  remove: (id) => api.delete(`/api/transactions/${id}`),
  dues: () => api.get("/api/dues"),
  recordPayment: (id, amount) => api.post(`/api/transactions/${id}/payments`, { amount }),
  summary: () => api.get("/api/dashboard/summary"),
};

export const reportApi = {
  download: (format, period = "6m") =>
    api.get(`/api/reports/export/${format}?period=${period}`, { responseType: "blob" }),
};

export const budgetApi = {
  list: (month) => api.get("/api/budgets", { params: month ? { month } : {} }),
  save: (payload) => api.post("/api/budgets", payload),
  remove: (id) => api.delete(`/api/budgets/${id}`),
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
