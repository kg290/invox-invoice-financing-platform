import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 120000, // 120 seconds — vendor registration hits Sandbox APIs during verify-otp
});

// ── Request interceptor: always attach token from localStorage ──
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("invox_access_token");
  if (token && config.headers) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// ── 401 interceptor: attempt token refresh, else redirect to login ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((p) => {
    if (token) p.resolve(token);
    else p.reject(error);
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Skip auth endpoints to avoid infinite loops
    if (
      originalRequest?.url?.includes("/auth/login") ||
      originalRequest?.url?.includes("/auth/register") ||
      originalRequest?.url?.includes("/auth/verify-otp") ||
      originalRequest?.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers["Authorization"] = `Bearer ${token}`;
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("invox_refresh_token");
      if (!refreshToken) {
        // No refresh token — full logout
        localStorage.removeItem("invox_access_token");
        localStorage.removeItem("invox_refresh_token");
        localStorage.removeItem("invox_user");
        delete api.defaults.headers.common["Authorization"];
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const r = await api.post("/auth/refresh", { refresh_token: refreshToken });
        const { access_token, refresh_token: newRefresh, user } = r.data;

        localStorage.setItem("invox_access_token", access_token);
        localStorage.setItem("invox_refresh_token", newRefresh);
        localStorage.setItem("invox_user", JSON.stringify(user));
        api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

        processQueue(null, access_token);
        originalRequest.headers["Authorization"] = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem("invox_access_token");
        localStorage.removeItem("invox_refresh_token");
        localStorage.removeItem("invox_user");
        delete api.defaults.headers.common["Authorization"];
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;

/** Base URL of the backend (without /api suffix), for image URLs etc. */
export const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/api\/?$/, "");

/**
 * Convert a backend file path (e.g. "/uploads/foo.jpg") to a full URL
 * that can be used in <img src>.
 */
export function fileUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  // Ensure leading slash
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${BACKEND_URL}${cleanPath}`;
}

/**
 * Safely extract an error message string from an Axios error.
 * Handles FastAPI 422 validation errors where `detail` is an array of objects.
 */
export function getErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  const e = err as { response?: { data?: { detail?: unknown } } };
  const detail = e?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{type, loc, msg, input, ctx}]
    const msgs = detail
      .map((d: { msg?: string; loc?: (string | number)[] }) => {
        const field = d.loc ? d.loc.filter((l) => l !== "body").join(".") : "";
        return field ? `${field}: ${d.msg}` : d.msg || "";
      })
      .filter(Boolean);
    return msgs.length > 0 ? msgs.join("; ") : fallback;
  }
  return fallback;
}
