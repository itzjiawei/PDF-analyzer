import { CheckCircle2, FlaskConical, Loader2, XCircle } from "lucide-react";
import type { EvaluationResponse } from "../lib/api";

type Props = {
  disabled: boolean;
  evaluation: EvaluationResponse | null;
  running: boolean;
  onRun: () => void;
};

export function EvaluationPanel({ disabled, evaluation, running, onRun }: Props) {
  const score = evaluation ? `${evaluation.passed}/${evaluation.total}` : "--";
  const statusText = evaluation
    ? "checks passed"
    : disabled
      ? "select the Aurora sample"
      : "ready to run";

  return (
    <section className="panel evaluation-panel">
      <div className="evaluation-header">
        <div>
          <span className="eyebrow">Sample evaluation</span>
          <h2>Aurora golden question scorecard</h2>
          <p>Runs the included sample book through known questions to check retrieval relevance and answer coverage.</p>
        </div>
        <button className="evaluation-action" disabled={disabled || running} onClick={onRun}>
          {running ? <Loader2 className="spin" aria-hidden="true" /> : <FlaskConical aria-hidden="true" />}
          {running ? "Evaluating" : "Run evaluation"}
        </button>
      </div>

      <div className="evaluation-score">
        <strong>{score}</strong>
        <span>{statusText}</span>
      </div>

      {evaluation ? (
        <div className="evaluation-list">
          {evaluation.cases.map((item) => (
            <article className={item.passed ? "evaluation-case pass" : "evaluation-case fail"} key={item.question}>
              {item.passed ? <CheckCircle2 aria-hidden="true" /> : <XCircle aria-hidden="true" />}
              <div>
                <strong>{item.question}</strong>
                <span>
                  Expected chapter {item.expected_chapter} · retrieved {item.retrieved_chapters.join(", ") || "none"}
                </span>
                <p>{item.keyword_hits.length ? `Matched: ${item.keyword_hits.join(", ")}` : "No expected answer terms matched."}</p>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
