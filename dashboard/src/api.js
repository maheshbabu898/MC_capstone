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
  const response = await fetch(`${url}${path}`, {
    headers: {
      "bypass-tunnel-reminder": "true",
      "Bypass-Tunnel-Reminder": "true",
    },
  });
  if (!response.ok) {
    const text = await response.text();
    // If localtunnel returned its HTML interstitial reminder page
    if (text.includes("Tunnel website ahead!") || response.status === 511) {
      throw new Error(`Localtunnel verification needed: Open ${url} once in a new tab, click "Click to Continue", then refresh.`);
    }
    throw new Error(`API request failed (${response.status}): ${text.slice(0, 150)}`);
  }
  return response.json();
}

export const baseUrl = getBaseUrl();
