import { FileUp, LibraryBig, Loader2, X } from "lucide-react";
import type { ChangeEvent } from "react";
import type { DocumentRecord } from "../lib/api";

type Props = {
  documents: DocumentRecord[];
  selectedDocumentId: number | null;
  uploading: boolean;
  onUpload: (file: File) => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
};

export function UploadPanel({ documents, selectedDocumentId, uploading, onUpload, onSelect, onDelete }: Props) {
  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <section className="panel upload-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Knowledge source</span>
          <h2>Book library</h2>
        </div>
        <LibraryBig aria-hidden="true" />
      </div>

      <label className="upload-drop">
        <input accept="application/pdf" type="file" onChange={handleChange} />
        {uploading ? <Loader2 className="spin" aria-hidden="true" /> : <FileUp aria-hidden="true" />}
        <span>{uploading ? "Detecting sections and indexing vectors" : "Upload a PDF book"}</span>
      </label>

      <div className="library-note">
        <strong>Upload history</strong>
        <span>Select a saved book to ask it again, or remove books you no longer need.</span>
      </div>

      <div className="document-list">
        {documents.map((document) => (
          <div className={document.id === selectedDocumentId ? "document-row active" : "document-row"} key={document.id}>
            <button className="document-select" onClick={() => onSelect(document.id)}>
              <span>{document.title}</span>
              <small>
                {document.chapter_count} detected sections · {document.page_count} pages
              </small>
            </button>
            <button
              className="document-remove"
              onClick={() => onDelete(document.id)}
              title={`Remove ${document.title}`}
            >
              <X aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
