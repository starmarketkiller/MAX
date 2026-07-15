import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth uses httpOnly cookies set by the backend on /auth/login. The browser
// includes them automatically when withCredentials is true. No tokens are
// stored in JS-readable storage (XSS-resistant).
const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // /auth/me e' la chiamata con cui AuthProvider controlla "sono loggato?"
    // ad ogni avvio: per un visitatore anonimo risponde 401 SEMPRE, per
    // design — non e' una sessione scaduta, e' la risposta normale "no".
    // Reindirizzarla forzava chiunque atterrasse sulla landing dritto sulla
    // pagina di login, senza mai vedere la landing.
    const isAuthCheck = err?.config?.url?.endsWith("/auth/me");
    if (err?.response?.status === 401 && !isAuthCheck && !window.location.pathname.endsWith("/login")) {
      window.location.href = "/app/login";
    }
    return Promise.reject(err);
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default api;
