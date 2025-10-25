import type { SessionDetail, SessionSummary } from "./types";

type HttpRequestInit = globalThis.RequestInit;

const API_BASE = import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: HttpRequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const ApiClient = {
  listSessions: () => request<SessionSummary[]>("/sessions/"),
  createSession: (name?: string) =>
    request<SessionDetail>("/sessions/", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  getSession: (id: string) => request<SessionDetail>(`/sessions/${id}`),
  uploadPages: async (id: string, files: FileList | File[]) => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("files", file));
    const resp = await fetch(`${API_BASE}/sessions/${id}/pages`, {
      method: "POST",
      body: form,
    });
    if (!resp.ok) {
      throw new Error(await resp.text());
    }
    return (await resp.json()) as SessionDetail;
  },
  recognize: (id: string) =>
    request<{ taskId: string }>(`/sessions/${id}/recognize`, { method: "POST" }),
  exportDocument: async (id: string, format: "docx" | "pdf" | "markdown") => {
    const response = await fetch(`${API_BASE}/sessions/${id}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="?(.+)"?/i);
    const filename = match?.[1] ?? `document.${format === "markdown" ? "md" : format}`;
    return { blob, filename };
  },
};

export function createEventStream(sessionId: string): EventSource {
  return new EventSource(`${API_BASE}/sessions/${sessionId}/events`);
}
