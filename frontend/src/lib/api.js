const DEFAULT_BACKEND_URL = "http://localhost:8000";

function normalizeBackendUrl(value) {
  return (value || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
}

export const API_URL = normalizeBackendUrl(process.env.REACT_APP_BACKEND_URL);
export const BACKEND_URL = API_URL;
