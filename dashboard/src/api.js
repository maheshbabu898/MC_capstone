export function getBaseUrl() {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("mec_api_url");
    if (saved && saved.trim()) return saved.trim().replace(/\/+$/, "");
  }
  return (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export function setBaseUrl(url) {
  if (typeof window !== "undefined") {
    if (url && url.trim()) {
      localStorage.setItem("mec_api_url", url.trim().replace(/\/+$/, ""));
    } else {
      localStorage.removeItem("mec_api_url");
    }
  }
}

export async function apiGet(path) {
  const url = getBaseUrl();
  const response = await fetch(`${url}${path}`);
  if (!response.ok) throw new Error(`API request failed (${response.status}): ${await response.text()}`);
  return response.json();
}

export const baseUrl = getBaseUrl();
