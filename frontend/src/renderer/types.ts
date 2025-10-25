export type SessionStatus = "draft" | "processing" | "ready" | "error";

export type SessionSummary = {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  page_count: number;
  status: SessionStatus;
};

export type TextSpan = {
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
};

export type DocumentBlock = {
  id: string;
  type: string;
  bbox: [number, number, number, number];
  spans: TextSpan[];
};

export type DocumentPage = {
  index: number;
  width: number;
  height: number;
  blocks: DocumentBlock[];
};

export type Document = {
  created_at: string;
  language_hint: string;
  pages: DocumentPage[];
};

export type SessionPage = {
  id: string;
  index: number;
  filename: string;
  original_name: string;
  source_type: string;
  metadata: {
    width?: number | null;
    height?: number | null;
  };
};

export type SessionDetail = SessionSummary & {
  autosave_enabled: boolean;
  pages: SessionPage[];
  document?: Document | null;
  last_recognized_at?: string | null;
  last_error?: string | null;
};
