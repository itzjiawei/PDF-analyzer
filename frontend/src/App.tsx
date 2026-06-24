import { Activity, BookOpenText, Database, Network, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { CitationRail } from "./components/CitationRail";
import { EvaluationPanel } from "./components/EvaluationPanel";
import { UploadPanel } from "./components/UploadPanel";
import { VoiceConsole } from "./components/VoiceConsole";
import {
  askText,
  deleteDocument,
  listDocuments,
  runGoldenEvaluation,
  transcribeVoice,
  uploadDocument,
  type AskResponse,
  type DocumentRecord,
  type EvaluationResponse,
} from "./lib/api";

export function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [lastAnswer, setLastAnswer] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  useEffect(() => {
    listDocuments()
      .then((records) => {
        setDocuments(records);
      })
      .catch(() => setError("Start the FastAPI backend to load documents."));
  }, []);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId],
  );
  const supportsSampleEvaluation = selectedDocument?.title === "Aurora Operations Handbook";

  function handleSelectDocument(documentId: number) {
    setSelectedDocumentId(documentId);
    setLastAnswer(null);
    setEvaluation(null);
  }

  async function handleUpload(file: File) {
    setUploading(true);
    setError("");
    try {
      const document = await uploadDocument(file);
      setDocuments((current) => [document, ...current]);
      setSelectedDocumentId(document.id);
      setEvaluation(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteDocument(documentId: number) {
    setError("");
    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      if (selectedDocumentId === documentId) {
        setSelectedDocumentId(null);
        setLastAnswer(null);
        setEvaluation(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove document.");
    }
  }

  async function runAskText(question: string) {
    if (!selectedDocumentId) return;
    setBusy(true);
    setError("");
    try {
      setLastAnswer(await askText(selectedDocumentId, question, true));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runTranscribeVoice(audio: Blob) {
    setBusy(true);
    setError("");
    try {
      const result = await transcribeVoice(audio);
      return result.transcript;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice transcription failed.");
      return "";
    } finally {
      setBusy(false);
    }
  }

  async function runEvaluation() {
    if (!selectedDocumentId || !supportsSampleEvaluation) return;
    setEvaluating(true);
    setError("");
    try {
      setEvaluation(await runGoldenEvaluation(selectedDocumentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setEvaluating(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><BookOpenText aria-hidden="true" /></span>
          <div>
            <strong>BookLens Voice RAG</strong>
            <small>Grounded PDF intelligence</small>
          </div>
        </div>
        <nav>
          <span><Activity aria-hidden="true" /> ASR</span>
          <span><Database aria-hidden="true" /> RAG</span>
          <span><Network aria-hidden="true" /> LLM</span>
          <span><ShieldCheck aria-hidden="true" /> TTS</span>
        </nav>
      </header>

      <section className="hero-band">
        <div className="hero-content">
          <span className="eyebrow">Enterprise document voice assistant</span>
          <h1>Turn any PDF book into a spoken QA system</h1>
          <p>
            Upload a book, ask through the microphone, and receive a grounded answer with citations and browser playback.
          </p>
          <div className="metrics-strip">
            <div className="selected-source"><strong>{selectedDocument ? selectedDocument.title : "No book selected"}</strong><span>active source</span></div>
            <div><strong>{selectedDocument?.chapter_count ?? 0}</strong><span>detected sections</span></div>
            <div><strong>{selectedDocument?.page_count ?? 0}</strong><span>pages</span></div>
          </div>
        </div>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="workspace-grid">
        <UploadPanel
          documents={documents}
          onSelect={handleSelectDocument}
          onUpload={handleUpload}
          onDelete={handleDeleteDocument}
          selectedDocumentId={selectedDocumentId}
          uploading={uploading}
        />
        <VoiceConsole
          busy={busy}
          disabled={!selectedDocumentId}
          lastAnswer={lastAnswer}
          onAskText={runAskText}
          onTranscribeVoice={runTranscribeVoice}
        />
        <CitationRail citations={lastAnswer?.citations ?? []} />
      </section>

      {supportsSampleEvaluation ? (
        <EvaluationPanel
          disabled={!selectedDocumentId}
          evaluation={evaluation}
          onRun={runEvaluation}
          running={evaluating}
        />
      ) : null}
    </main>
  );
}
