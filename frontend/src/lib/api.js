const DEFAULT_BACKEND_URL = "http://localhost:8000";

function normalizeBackendUrl(value) {
  const trimmed = (value || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
  return trimmed.endsWith("/api") ? trimmed.slice(0, -4) : trimmed;
}

export const BACKEND_URL = normalizeBackendUrl(process.env.REACT_APP_BACKEND_URL);
export const API_URL = `${BACKEND_URL}/api`;
