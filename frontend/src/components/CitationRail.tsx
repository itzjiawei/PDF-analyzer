import { BookOpenCheck } from "lucide-react";
import type { Citation } from "../lib/api";

export function CitationRail({ citations }: { citations: Citation[] }) {
  return (
    <aside className="panel citation-rail">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Grounding</span>
          <h2>Retrieved evidence</h2>
        </div>
        <BookOpenCheck aria-hidden="true" />
      </div>
      <div className="citation-list">
        {citations.length === 0 ? (
          <p className="muted">Citations appear after a question is answered.</p>
        ) : (
          citations.map((citation) => {
            const evidence = formatEvidence(citation.excerpt, citation.chapter_title);
            return (
              <article className="citation-card" key={citation.chunk_id}>
                <div>
                  <strong>{citation.chapter_title}</strong>
                  <span>
                    Pages {citation.page_start}-{citation.page_end}
                  </span>
                </div>
                {evidence.section ? <span className="evidence-section">{evidence.section}</span> : null}
                <p>{evidence.text}</p>
              </article>
            );
          })
        )}
      </div>
    </aside>
  );
}

function formatEvidence(excerpt: string, chapterTitle: string) {
  const chapterLabel = escapeRegExp(chapterTitle);
  let text = excerpt
    .replace(/Aurora Operations Handbook\s+Page\s+\d+\s*/gi, "")
    .replace(new RegExp(`^${chapterLabel}\\s*`, "i"), "")
    .replace(/\s+/g, " ")
    .trim();

  const chapterMatch = chapterTitle.match(/^Chapter\s+\d+:\s*(.+)$/i);
  if (chapterMatch) {
    text = text.replace(new RegExp(`^${escapeRegExp(chapterMatch[1])}\\s*`, "i"), "").trim();
  }

  const sectionPrefix = text.match(/^(Section\s+\d+(?:\.\d+)?:)\s+(.+)$/i);
  if (!sectionPrefix) return { section: "", text };

  const parsed = splitRepeatedSectionTitle(sectionPrefix[2]);
  return {
    section: `${sectionPrefix[1]} ${parsed.title}`.trim(),
    text: parsed.body || text,
  };
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function splitRepeatedSectionTitle(text: string) {
  const words = text.split(/\s+/).filter(Boolean);
  for (let length = Math.floor(words.length / 2); length >= 1; length -= 1) {
    const first = words.slice(0, length).join(" ").toLowerCase();
    const second = words.slice(length, length * 2).join(" ").toLowerCase();
    if (first === second) {
      return {
        title: words.slice(0, length).join(" "),
        body: words.slice(length).join(" "),
      };
    }
  }

  const sentenceStart = words.findIndex((word, index) => index > 0 && /^[A-Z]/.test(word));
  if (sentenceStart > 0) {
    return {
      title: words.slice(0, sentenceStart).join(" "),
      body: words.slice(sentenceStart).join(" "),
    };
  }

  return { title: "", body: text };
}
