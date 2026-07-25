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

// AUD0-FE-AUTH-003 / AUD0-SEC-008: le mutazioni autenticate via cookie non
// avevano alcuna difesa CSRF. Il backend emette un cookie `nexus_csrf`
// leggibile da JS (non e' un segreto di sessione, e' un binding) e pretende
// di ritrovarne il valore nell'header su ogni richiesta che modifica stato.
export const CSRF_COOKIE = "nexus_csrf";
export const CSRF_HEADER = "X-Nexus-Csrf";

export function readCsrfToken() {
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

const SAFE_METHODS = ["get", "head", "options"];

api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (!SAFE_METHODS.includes(method)) {
    const token = readCsrfToken();
    if (token) {
      config.headers = { ...config.headers, [CSRF_HEADER]: token };
    }
  }
  return config;
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
