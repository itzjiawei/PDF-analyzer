from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


OUTPUT = Path(__file__).resolve().parents[1] / "sample_data" / "aurora_operations_handbook.pdf"

CHAPTERS = [
    ("Signal Quality", "latency, freshness, precision, and recall metrics for operational evidence"),
    ("Incident Readiness", "response ownership, escalation windows, and after-action reviews"),
    ("Retrieval Strategy", "hybrid search, chapter-aware chunks, query expansion, and reranking"),
    ("Governance Controls", "policy ownership, approvals, audit trails, and review cadences"),
    ("Customer Assurance", "support handoffs, service commitments, and communication quality"),
    ("Data Lifecycle", "ingestion, retention, deletion, lineage, and validation checkpoints"),
    ("Evaluation Practice", "golden questions, answer faithfulness, citation quality, and regression tests"),
    ("Voice Experience", "microphone input, transcription confidence, turn-taking, and audio playback"),
    ("Security Model", "least privilege, secret handling, transport security, and abuse monitoring"),
    ("Executive Reporting", "operating reviews, risk summaries, decision logs, and roadmap alignment"),
]

CHAPTER_INSIGHTS = {
    3: (
        "Hybrid search is recommended because dense vectors capture conceptual matches while keyword search preserves exact terms, acronyms, and numbered procedures. "
        "Reranking is recommended because the first retrieval pass favors recall, then a smaller second pass can prioritize the passages that best answer the actual question."
    ),
    7: (
        "Answer-quality evaluation should test both retrieval hit rate and citation faithfulness. A good answer must include the right chapter, use the retrieved evidence, and avoid unsupported claims."
    ),
    8: (
        "The voice experience should keep turns short, expose the recognized transcript, and provide replayable audio so users can verify both transcription and synthesis quality."
    ),
}

CHAPTER_SECTIONS = {
    1: [
        (
            "Latency and freshness",
            "Signal quality starts with measuring whether operational evidence arrives quickly enough to support decisions. Teams track source latency, refresh age, and the point at which stale data must be excluded from an answer.",
        ),
        (
            "Precision and recall",
            "Precision shows whether retrieved passages are actually useful, while recall checks whether important evidence was missed. Reviewers compare both measures because a system can look confident while omitting a critical page.",
        ),
        (
            "Diagnostic signals",
            "Each dashboard should include a primary health metric and a secondary diagnostic signal. The diagnostic signal explains why quality changed, such as delayed ingestion, duplicated records, or noisy labels.",
        ),
        (
            "Evidence acceptance",
            "A passage should be accepted only when it contains enough context for a reader to understand the recommendation. Thin snippets, orphaned numbers, and unlabeled charts should be routed for manual review.",
        ),
        (
            "Monitoring cadence",
            "Signal reviews happen weekly for stable sources and daily for high-risk sources. A missed review is logged as an operational risk because it weakens trust in future answers.",
        ),
        (
            "Quality ownership",
            "Every signal has an accountable owner who can approve threshold changes. Ownership prevents teams from changing retrieval behavior without understanding downstream reporting impact.",
        ),
    ],
    2: [
        (
            "Response ownership",
            "Incident readiness depends on naming a response owner before an issue occurs. The owner coordinates triage, assigns investigators, and decides when the incident can move from active response to review.",
        ),
        (
            "Escalation windows",
            "Escalation windows define how long a team may investigate before involving a wider group. Severity one issues require immediate escalation, while lower-risk items may wait for the next operating review.",
        ),
        (
            "Runbook rehearsal",
            "Teams rehearse runbooks with realistic failure scenarios rather than reading the procedure passively. Rehearsal exposes missing permissions, unclear handoffs, and steps that depend on one person's memory.",
        ),
        (
            "Communication channel",
            "An incident has one primary communication channel and one decision log. This avoids scattered updates and gives executives a clear record of what changed during the response.",
        ),
        (
            "After-action review",
            "After-action reviews focus on learning, not blame. The review captures what was detected, what was delayed, what protected customers, and which preventive action has an owner.",
        ),
        (
            "Readiness metrics",
            "Readiness is measured through time to acknowledge, time to assign ownership, and time to publish the first customer-safe update. These measures show whether the team can act before the problem grows.",
        ),
    ],
    3: [
        (
            "Hybrid search",
            "Hybrid search combines vector similarity with keyword matching. Vectors capture conceptual intent, while keyword search protects exact product names, acronyms, identifiers, and numbered policies.",
        ),
        (
            "Chapter-aware chunks",
            "Chunks should preserve chapter and page boundaries whenever possible. This lets the answer cite a meaningful location instead of pointing to an arbitrary fixed-size slice of text.",
        ),
        (
            "Query expansion",
            "Query expansion adds related terms only when they improve recall without changing the user's intent. For example, incident readiness may expand to escalation, ownership, and after-action review.",
        ),
        (
            "Reranking pass",
            "The first retrieval pass favors recall by collecting several candidates. A reranker then compares the question against each passage and keeps the passages most likely to answer the specific request.",
        ),
        (
            "Evidence diversity",
            "The retrieval layer should avoid sending duplicate passages to the model. Diverse evidence helps the answer cover separate angles instead of repeating the same sentence from multiple locations.",
        ),
        (
            "Citation traceability",
            "Each final passage keeps its chapter title, page range, and chunk identifier. Traceability lets a user inspect the source and challenge the answer when the retrieval result looks weak.",
        ),
    ],
    4: [
        (
            "Policy ownership",
            "Governance controls begin with clear ownership for each policy. Owners approve changes, answer interpretation questions, and retire outdated guidance before it misleads the assistant.",
        ),
        (
            "Approval workflow",
            "High-impact changes require an approval workflow that records who reviewed the update and why it was accepted. The approval note is stored with the policy so future audits can reconstruct the decision.",
        ),
        (
            "Audit trails",
            "Audit trails should capture source uploads, indexing time, model configuration, and the evidence used for important answers. This record helps teams explain how a response was produced.",
        ),
        (
            "Review cadence",
            "Stable controls are reviewed quarterly, while controls tied to active incidents are reviewed after each incident. Review cadence keeps governance current without overwhelming owners.",
        ),
        (
            "Exception handling",
            "Exceptions must name the risk, the temporary owner, and the expiry date. Open-ended exceptions create hidden policy drift and should be escalated during operating review.",
        ),
        (
            "Change communication",
            "When a governance rule changes, teams publish a short summary of the operational impact. The summary states what changed, who is affected, and which documents should be re-indexed.",
        ),
    ],
    5: [
        (
            "Support handoffs",
            "Customer assurance depends on support handoffs that preserve context. A handoff should include the customer impact, current owner, promised next update, and any evidence already checked.",
        ),
        (
            "Service commitments",
            "Service commitments are written as measurable promises rather than vague intentions. Teams track whether response windows, escalation timing, and resolution updates meet the published standard.",
        ),
        (
            "Communication quality",
            "Customer updates should be accurate, calm, and specific about the next checkpoint. The handbook discourages overconfident estimates when the investigation is still uncertain.",
        ),
        (
            "Customer-safe language",
            "Customer-facing messages avoid internal jargon and unverified root causes. A message may describe observed impact, mitigation status, and the time of the next update.",
        ),
        (
            "Assurance evidence",
            "Assurance reviews inspect tickets, incident notes, and customer communications together. The goal is to confirm that the customer heard the same operational facts the team acted on.",
        ),
        (
            "Feedback loop",
            "Recurring customer confusion becomes input to runbook and documentation improvements. This feedback loop turns support friction into clearer evidence for future answers.",
        ),
    ],
    6: [
        (
            "Ingestion checks",
            "The data lifecycle begins with ingestion checks that verify file type, text extraction, page count, and section detection. Failed checks stop indexing before unreliable content reaches retrieval.",
        ),
        (
            "Retention rules",
            "Retention rules define how long uploaded books and derived chunks remain available. The rule should match the sensitivity of the source and the expected reuse of the knowledge.",
        ),
        (
            "Deletion handling",
            "Deleting a book removes its searchable chunks and prevents new answers from citing it. Historical QA logs may keep prior answers for audit, but they should no longer act as active evidence.",
        ),
        (
            "Lineage metadata",
            "Lineage metadata links every chunk back to filename, title, section, and page range. This makes it possible to diagnose whether a bad answer came from parsing, retrieval, or generation.",
        ),
        (
            "Validation checkpoints",
            "Validation checkpoints compare detected sections against the document structure. When section detection is uncertain, reviewers should rely more heavily on page citations than chapter counts.",
        ),
        (
            "Re-indexing triggers",
            "A document is re-indexed after material source changes, parser improvements, or embedding-model changes. Re-indexing prevents old vectors from representing a newer version of the book.",
        ),
    ],
    7: [
        (
            "Golden questions",
            "Evaluation practice uses golden questions that represent common user needs and known hard cases. Each question includes expected concepts, acceptable evidence, and failure notes.",
        ),
        (
            "Faithfulness checks",
            "Faithfulness checks compare the answer against the retrieved passages. An answer fails when it adds unsupported details, ignores stronger evidence, or contradicts the cited pages.",
        ),
        (
            "Citation quality",
            "Citation quality is judged by whether a reader can verify the claim quickly. A citation is weak if it points to a broad chapter but not to the passage that supports the answer.",
        ),
        (
            "Regression testing",
            "Regression tests run after retrieval, prompt, or model changes. The tests protect working behavior from accidental drift and reveal whether new improvements hurt existing questions.",
        ),
        (
            "Human review",
            "Human reviewers inspect a sample of answers for clarity, usefulness, and grounding. Their notes become examples for future prompt revisions and acceptance criteria.",
        ),
        (
            "Quality scorecard",
            "The scorecard separates retrieval hit rate, answer faithfulness, citation usefulness, and voice usability. Separating dimensions helps teams fix the right part of the pipeline.",
        ),
    ],
    8: [
        (
            "Microphone capture",
            "The voice experience should show when the microphone is actively recording and whether audio is being captured. A visible level meter helps users notice silent input before submitting.",
        ),
        (
            "Transcript review",
            "The recognized transcript should be editable before the question is sent. Review protects users from speech recognition errors, especially for domain terms, chapter names, and acronyms.",
        ),
        (
            "Turn design",
            "Voice turns work best when they are short and confirm one question at a time. Long multi-part prompts can be typed instead, where the user can revise them more easily.",
        ),
        (
            "Audio playback",
            "Playback should remain available after the answer appears so users can replay it. The interface should not hide the written answer when speech is playing.",
        ),
        (
            "Read-along support",
            "Read-along highlighting can help users follow long spoken answers, but exact word timing requires a TTS provider with alignment metadata. Without timestamps, the highlight should be presented as approximate.",
        ),
        (
            "Error recovery",
            "When transcription or synthesis fails, the interface should keep the text answer usable. A browser speech fallback is acceptable when cloud TTS is unavailable.",
        ),
    ],
    9: [
        (
            "Least privilege",
            "The security model applies least privilege to API keys, database accounts, and upload handling. Services should only receive the permissions required for their part of the pipeline.",
        ),
        (
            "Secret handling",
            "Secrets belong in environment files or managed secret stores, never in frontend code. Logs should avoid printing keys, raw tokens, or full request payloads containing sensitive content.",
        ),
        (
            "Transport security",
            "Production deployments should use HTTPS for microphone uploads, PDF uploads, and API responses. Local development may use localhost, but deployment should not send audio or documents over plain HTTP.",
        ),
        (
            "Abuse monitoring",
            "Abuse monitoring looks for unusually large uploads, repeated failed transcriptions, and unexpected spikes in model calls. These signals can indicate misuse or runaway automation.",
        ),
        (
            "Document sensitivity",
            "Sensitive books require clear retention rules and deletion controls. Users should know whether uploaded documents are stored, indexed, and available to other users.",
        ),
        (
            "Output safety",
            "The assistant should avoid exposing hidden prompts or unsupported claims. When evidence is insufficient, the safer behavior is to state the gap rather than invent a procedure.",
        ),
    ],
    10: [
        (
            "Operating reviews",
            "Executive reporting summarizes operating health without burying leaders in raw logs. The review highlights service risks, readiness trends, and unresolved decisions that need sponsorship.",
        ),
        (
            "Risk summaries",
            "Risk summaries should connect each risk to customer impact, likelihood, owner, and next checkpoint. This structure helps executives decide whether to accept, mitigate, or escalate the risk.",
        ),
        (
            "Decision logs",
            "Decision logs record the choice, the evidence considered, and the person accountable for follow-up. The log keeps strategic decisions connected to operational facts.",
        ),
        (
            "Roadmap alignment",
            "Roadmap alignment compares operational pain points with planned engineering work. A recurring incident theme should influence priorities if it repeatedly affects customers or support teams.",
        ),
        (
            "Narrative clarity",
            "Reports should explain what changed since the last review before listing new requests. Clear narrative prevents executives from confusing routine activity with meaningful risk movement.",
        ),
        (
            "Action tracking",
            "Every executive action has an owner and due date. Open actions are reviewed until closed, transferred, or explicitly accepted as ongoing risk.",
        ),
    ],
}


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#516366"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.75 * inch, 0.45 * inch, "Aurora Operations Handbook")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_book() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BookTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#14343A"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ChapterTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#B25445"),
            spaceBefore=10,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.8,
            leading=15.5,
            textColor=colors.HexColor("#182C31"),
            spaceAfter=9,
        )
    )

    story = [
        Paragraph("Aurora Operations Handbook", styles["BookTitle"]),
        Paragraph(
            "A synthetic 10-chapter book for testing voice-based question answering, grounded retrieval, and citation quality.",
            styles["Body"],
        ),
        PageBreak(),
    ]

    for idx, (title, _focus) in enumerate(CHAPTERS, start=1):
        story.append(Paragraph(f"Chapter {idx}: {title}", styles["ChapterTitle"]))
        if idx in CHAPTER_INSIGHTS:
            story.append(Paragraph(CHAPTER_INSIGHTS[idx], styles["Body"]))
        for section, (section_title, body) in enumerate(CHAPTER_SECTIONS[idx], start=1):
            story.append(Paragraph(f"Section {idx}.{section}: {section_title}", styles["Body"]))
            story.append(Paragraph(body, styles["Body"]))
        if idx != len(CHAPTERS):
            story.append(PageBreak())

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(OUTPUT)


if __name__ == "__main__":
    build_book()
