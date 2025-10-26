import { useCallback, useEffect, useMemo, useState } from "react";
import type { DragEvent } from "react";
import { ApiClient, createEventStream } from "./api";
import type { SessionDetail, SessionSummary } from "./types";

type LogEntry = { ts: string; message: string };

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  return new Date(value).toLocaleString();
};

function DropZone({ onFiles }: { onFiles: (files: File[]) => void }) {
  const [active, setActive] = useState(false);

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setActive(false);
    const files = Array.from(event.dataTransfer.files).filter((file) => file.type.startsWith("image/"));
    if (files.length) {
      onFiles(files);
    }
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setActive(true);
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        setActive(false);
      }}
      onDrop={handleDrop}
      style={{
        border: "2px dashed #94a3b8",
        borderRadius: "0.75rem",
        padding: "1rem",
        marginBottom: "1rem",
        textAlign: "center",
        background: active ? "#e0f2fe" : "transparent",
        color: "#0f172a",
      }}
    >
      Перетащите изображения сюда или вставьте их из буфера обмена (Ctrl + V).
    </div>
  );
}

export default function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await ApiClient.listSessions();
      setSessions(list);
      if (!selectedId && list.length > 0) {
        setSelectedId(list[0].id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }, [selectedId]);

  const loadSelectedSession = useCallback(async () => {
    if (!selectedId) {
      setSelectedSession(null);
      return;
    }
    setLoading(true);
    try {
      const detail = await ApiClient.getSession(selectedId);
      setSelectedSession(detail);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    loadSelectedSession();
  }, [loadSelectedSession]);

  useEffect(() => {
    if (!selectedId) return undefined;
    const source = createEventStream(selectedId);
    source.onmessage = (event) => {
      const data = JSON.parse(event.data) as Record<string, string>;
      setLog((prev) => [
        { ts: new Date().toLocaleTimeString(), message: JSON.stringify(data) },
        ...prev.slice(0, 50),
      ]);
      if (data.event === "recognition-finished") {
        loadSelectedSession();
        refreshSessions();
      }
    };
    source.onerror = () => {
      source.close();
    };
    return () => source.close();
  }, [selectedId, loadSelectedSession, refreshSessions]);

  const [newSessionName, setNewSessionName] = useState("");

  const handleCreateSession = async () => {
    try {
      const created = await ApiClient.createSession(newSessionName || undefined);
      setSelectedId(created.id);
      setNewSessionName("");
      await refreshSessions();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleUpload = async (files: FileList | File[] | null) => {
    if (!selectedId || !files || files.length === 0) return;
    const payload = files instanceof FileList ? Array.from(files) : files;
    setLoading(true);
    try {
      const detail = await ApiClient.uploadPages(selectedId, payload);
      setSelectedSession(detail);
      refreshSessions();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    const onPaste = async (event: ClipboardEvent) => {
      if (!selectedId) return;
      const items = event.clipboardData?.items;
      if (!items) return;
      const images: File[] = [];
      for (const item of items) {
        if (item.kind === "file" && item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) images.push(file);
        }
      }
      if (images.length) {
        await handleUpload(images);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [selectedId]);

  const handleRecognize = async () => {
    if (!selectedId) return;
    try {
      await ApiClient.recognize(selectedId);
      setLog((prev) => [
        { ts: new Date().toLocaleTimeString(), message: "🚀 Recognition started" },
        ...prev,
      ]);
      refreshSessions();
      loadSelectedSession();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleExport = async (format: "docx" | "pdf" | "markdown") => {
    if (!selectedId) return;
    try {
      const { blob, filename } = await ApiClient.exportDocument(selectedId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const statusText = useMemo(() => {
    switch (selectedSession?.status) {
      case "processing":
        return "Обработка...";
      case "ready":
        return "Готово ✅";
      case "error":
        return "Ошибка ❌";
      default:
        return "Черновик";
    }
  }, [selectedSession?.status]);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Reflow OCR</h1>
          <p>Локальный OCR-процесс с максимальной точностью и экспортом DOCX/PDF/MD.</p>
        </div>
        <div className="actions">
          <input
            type="text"
            placeholder="Название сессии"
            value={newSessionName}
            onChange={(e) => setNewSessionName(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: "0.5rem", border: "none", flex: 1 }}
          />
          <button className="button" onClick={handleCreateSession}>
            + Новая сессия
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <h3>Сессии</h3>
          <div className="session-list">
            {sessions.map((session) => (
              <article
                key={session.id}
                className={`session-card ${session.id === selectedId ? "active" : ""}`}
                onClick={() => setSelectedId(session.id)}
              >
                <h4>{session.name}</h4>
                <p>{session.page_count} страниц</p>
                <span className={`status-pill ${session.status}`}>{session.status}</span>
              </article>
            ))}
            {sessions.length === 0 && <p>Сессий пока нет — создайте первую.</p>}
          </div>
        </aside>

        <main className="details">
          {error ? (
            <div className="panel">
              <strong>Ошибка:</strong> {error}
            </div>
          ) : null}
          {selectedSession ? (
            <>
              <section className="panel">
                <h3>{selectedSession.name}</h3>
                <p>Статус: {statusText}</p>
                <p>Страниц: {selectedSession.page_count}</p>
                <p>Последнее распознавание: {formatDate(selectedSession.last_recognized_at)}</p>
                {selectedSession.last_error ? <p>Ошибка: {selectedSession.last_error}</p> : null}
                <div className="actions">
                  <label className="button secondary" htmlFor="upload-input">
                    Добавить страницы
                  </label>
                  <input
                    id="upload-input"
                    className="upload-input"
                    type="file"
                    accept="image/*"
                    multiple
                    hidden
                    onChange={(e) => handleUpload(e.target.files)}
                  />
                  <button className="button" onClick={handleRecognize} disabled={loading}>
                    Запустить OCR
                  </button>
                  <button className="button secondary" onClick={() => handleExport("docx")}>
                    Экспорт DOCX
                  </button>
                  <button className="button secondary" onClick={() => handleExport("pdf")}>
                    Экспорт PDF
                  </button>
                  <button className="button secondary" onClick={() => handleExport("markdown")}>
                    Экспорт MD
                  </button>
                </div>
              </section>

              <section className="panel">
                <h3>Страницы</h3>
                <DropZone onFiles={(files) => handleUpload(files)} />
                <div className="pages-grid">
                  {selectedSession.pages.map((page) => (
                    <div key={page.id} className="page-card">
                      <strong>#{page.index + 1}</strong>
                      <p>{page.original_name}</p>
                      <p>
                        {page.metadata?.width}×{page.metadata?.height}
                      </p>
                    </div>
                  ))}
                  {selectedSession.pages.length === 0 && <p>Добавьте изображения, чтобы начать.</p>}
                </div>
              </section>

              <section className="panel">
                <h3>Лог событий</h3>
                <div className="log">
                  {log.length === 0 && <p>Нет событий.</p>}
                  {log.map((entry, idx) => (
                    <div key={idx} className="log-entry">
                      [{entry.ts}] {entry.message}
                    </div>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <section className="panel">
              <p>Выберите или создайте сессию, чтобы начать работу.</p>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
