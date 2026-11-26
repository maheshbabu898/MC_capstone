const baseUrl = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function apiGet(path) {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) throw new Error(`API request failed (${response.status}): ${await response.text()}`);
  return response.json();
}

export { baseUrl };
