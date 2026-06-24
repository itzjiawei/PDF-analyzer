const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export type DocumentRecord = {
  id: number;
  filename: string;
  title: string;
  chapter_count: number;
  page_count: number;
  status: string;
};

export type Citation = {
  chunk_id: number;
  chapter_title: string;
  chapter_number: number;
  page_start: number;
  page_end: number;
  score: number;
  excerpt: string;
};

export type AskResponse = {
  question: string;
  answer: string;
  citations: Citation[];
  audio_base64?: string | null;
  audio_mime_type?: string | null;
};

export type TranscribeResponse = {
  transcript: string;
};

export type EvaluationCase = {
  question: string;
  expected_chapter: number;
  retrieved_chapters: number[];
  retrieval_pass: boolean;
  keyword_hits: string[];
  answer_excerpt: string;
  passed: boolean;
};

export type EvaluationResponse = {
  document_id: number;
  passed: number;
  total: number;
  cases: EvaluationCase[];
};

export async function listDocuments(): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) throw new Error("Could not load documents");
  return response.json();
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function deleteDocument(documentId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await response.text());
}

export async function askText(documentId: number, question: string, speak = true): Promise<AskResponse> {
  const response = await fetch(`${API_BASE}/ask/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, question, speak }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function askVoice(documentId: number, audio: Blob): Promise<AskResponse> {
  const form = new FormData();
  form.append("document_id", String(documentId));
  form.append("audio", audio, "question.webm");
  const response = await fetch(`${API_BASE}/ask/voice`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function transcribeVoice(audio: Blob): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("audio", audio, `question.${audioExtension(audio.type)}`);
  const response = await fetch(`${API_BASE}/transcribe`, { method: "POST", body: form });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function runGoldenEvaluation(documentId: number): Promise<EvaluationResponse> {
  const response = await fetch(`${API_BASE}/evaluation/golden/${documentId}`, { method: "POST" });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function audioExtension(type: string) {
  if (type.includes("mp4")) return "mp4";
  if (type.includes("ogg")) return "ogg";
  return "webm";
}
