#
# Runtime module.
# Canonical FastAPI app, routes, and request flow live here.
#
import os
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI

from .config import OPENAI_API_KEY
from .embed import embed_texts
from .retrieval import (
    retrieve_similar,
    retrieve_calibration_examples,
    retrieve_calibration_examples_by_course,
)

logger = logging.getLogger("project_blackboard.qa")

client = OpenAI(api_key=OPENAI_API_KEY)


def _normalize_for_dedupe(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    # remove quotes and punctuation that cause trivial diffs
    s = re.sub(r"[\"'“”‘’.,;:!?()\[\]{}]", "", s)
    return s


def _dedupe_hits(hits: List[Dict[str, Any]], max_unique: int) -> List[Dict[str, Any]]:
    """
    Keeps first occurrence (closest distance) while enforcing:
      - unique (source, chunk_index)
      - unique normalized content
    Assumes hits are already ordered best-to-worst.
    """
    seen_sc = set()
    seen_content = set()
    out: List[Dict[str, Any]] = []

    for h in hits or []:
        sc = (h.get("source"), h.get("chunk_index"))
        if sc in seen_sc:
            continue
        seen_sc.add(sc)

        content_key = _normalize_for_dedupe(h.get("content", ""))
        if not content_key or content_key in seen_content:
            continue
        seen_content.add(content_key)

        out.append(h)
        if len(out) >= max_unique:
            break

    return out


def _preview(text: str, n: int = 80) -> str:
    t = (text or "").replace("\n", " ").strip()
    return (t[:n] + "…") if len(t) > n else t


def _debug_retrieval_log(
    rubric_hits: List[Dict[str, Any]],
    feedback_hits: List[Dict[str, Any]],
    calibration_hits: List[Dict[str, Any]],
    metadata_filter: Optional[Dict[str, Any]],
    assignment_id: Optional[str],
    calibration_mode: Optional[str] = None,
) -> None:
    if os.getenv("DEBUG_RETRIEVAL", "false").lower() != "true":
        return

    logger.info(
        "retrieval_debug assignment_id=%s calibration_mode=%s metadata_filter=%s rubric_hits=%s feedback_hits=%s calibration_hits=%s",
        assignment_id,
        calibration_mode,
        metadata_filter,
        len(rubric_hits or []),
        len(feedback_hits or []),
        len(calibration_hits or []),
    )

    for i, h in enumerate((rubric_hits or [])[:3], start=1):
        logger.info(
            "rubric[%s] source=%s chunk_index=%s distance=%s preview=%s",
            i,
            h.get("source"),
            h.get("chunk_index"),
            h.get("distance"),
            _preview(h.get("content", "")),
        )

    for i, h in enumerate((feedback_hits or [])[:3], start=1):
        logger.info(
            "feedback[%s] source=%s chunk_index=%s distance=%s preview=%s",
            i,
            h.get("source"),
            h.get("chunk_index"),
            h.get("distance"),
            _preview(h.get("content", "")),
        )

    for i, h in enumerate((calibration_hits or [])[:3], start=1):
        logger.info(
            "calibration[%s] assignment_id=%s distance=%s submission_preview=%s",
            i,
            h.get("assignment_id"),
            h.get("distance"),
            _preview(h.get("submission_text", "")),
        )


def _format_citations(
    hits: Optional[List[Dict[str, Any]]],
    label: str,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns:
      - a context string with numbered citations
      - a citations list that maps citation numbers to chunk metadata
    """
    hits = hits or []
    ctx_lines: List[str] = []
    cites: List[Dict[str, Any]] = []

    for i, h in enumerate(hits, start=1):
        source = h.get("source", "unknown")
        chunk_index = h.get("chunk_index", -1)
        content = h.get("content", "")
        row_id = h.get("id")
        distance = h.get("distance")

        ctx_lines.append(f"[{label}{i}] (source={source}, chunk={chunk_index})\n{content}\n")

        cites.append(
            {
                "cite": f"{label}{i}",
                "source": source,
                "chunk_index": chunk_index,
                "id": row_id,
                "distance": distance,
            }
        )

    return "\n".join(ctx_lines).strip(), cites


def _format_calibration(hits: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    ctx_lines: List[str] = []
    cites: List[Dict[str, Any]] = []
    for i, h in enumerate(hits, start=1):
        # Keep it compact, these are anchors, not full context dumps
        submission = (h.get("submission_text") or "").strip()
        feedback = (h.get("feedback_text") or "").strip()
        grade = h.get("grade_numeric", None)

        ctx_lines.append(
            f"[C{i}] grade={grade}\n"
            f"Student submission:\n{submission}\n\n"
            f"Instructor feedback:\n{feedback}\n"
        )

        cites.append(
            {
                "cite": f"C{i}",
                "assignment_id": h.get("assignment_id"),
                "id": h.get("id"),
                "distance": h.get("distance"),
            }
        )
    return "\n".join(ctx_lines).strip(), cites


def answer_from_rubric(question: str, top_k: int = 6) -> Dict[str, Any]:
    q_emb = embed_texts([question])[0]

    # --- retrieval happens here ---
    rubric_hits = retrieve_similar("rubric_chunks", q_emb, top_k=top_k) or []

    if not rubric_hits:
        return {
            "question": question,
            "answer": (
                "I don’t have any rubric context indexed yet, so I can’t answer from the rubric. "
                "Ingest your rubric first (rubric_chunks), then try again."
            ),
            "citations": [],
        }

    rubric_ctx, rubric_cites = _format_citations(rubric_hits, "R")

    system = (
        "You are Project Blackboard, an instructor assistant. "
        "Answer the question using only the provided rubric context. "
        "Do not provide feedback, suggestions, or grading. "
        "If the rubric context does not contain the answer, say what is missing and ask one follow-up question. "
        "Always include citations like [R1], [R2] after the sentence they support."
    )

    user = f"""Question:
{question}

Rubric context:
{rubric_ctx}
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )

    return {
        "question": question,
        "answer": resp.choices[0].message.content,
        "citations": rubric_cites,
    }


def suggest_feedback(
    question_or_submission: str,
    top_k_rubric: int = 6,
    top_k_feedback: int = 6,
    feedback_metadata_filter: Optional[Dict[str, Any]] = None,
    assignment_id: Optional[str] = None,
    top_k_calibration: int = 4,
) -> Dict[str, Any]:
    q_emb = embed_texts([question_or_submission])[0]

    # -------------------------------------------------
    # Calibration retrieval: week-first, course-fallback
    # -------------------------------------------------
    MIN_WEEK_HITS = 3  # minimum anchors to trust week-specific calibration

    calibration_hits: List[Dict[str, Any]] = []
    calibration_mode: Optional[str] = None  # "week" | "course" | None

    # 1) Week-specific (assignment_id) calibration
    if assignment_id:
        calibration_hits = (
            retrieve_calibration_examples(
                query_embedding=q_emb,
                assignment_id=assignment_id,
                top_k=top_k_calibration,
                metadata_filter=None,
            )
            or []
        )
        if len(calibration_hits) >= MIN_WEEK_HITS:
            calibration_mode = "week"

    # 2) Course-level fallback calibration (only if week is insufficient)
    if calibration_mode is None:
        course = (feedback_metadata_filter or {}).get("course")
        if course:
            calibration_hits = (
                retrieve_calibration_examples_by_course(
                    query_embedding=q_emb,
                    course=course,
                    top_k=top_k_calibration,
                    metadata_filter=None,
                )
                or []
            )
            if calibration_hits:
                calibration_mode = "course"

    rubric_hits = retrieve_similar("rubric_chunks", q_emb, top_k=top_k_rubric) or []
    feedback_hits = retrieve_similar(
        "feedback_library",
        q_emb,
        top_k=top_k_feedback,
        metadata_filter=feedback_metadata_filter,
    ) or []

    # ---- de-dupe feedback hits (prevents near-identical examples) ----
    feedback_hits = _dedupe_hits(feedback_hits, max_unique=top_k_feedback)

    # Debug logging
    _debug_retrieval_log(
        rubric_hits=rubric_hits,
        feedback_hits=feedback_hits,
        calibration_hits=calibration_hits,
        metadata_filter=feedback_metadata_filter,
        assignment_id=assignment_id,
        calibration_mode=calibration_mode,
    )

    # Guardrail: must have rubric OR calibration anchors
    if len(rubric_hits) == 0 and len(calibration_hits) == 0:
        return {
            "input": question_or_submission,
            "suggested_feedback": (
                "I don’t have enough rubric or calibration context indexed to give reliable feedback yet. "
                "Please share the assignment prompt or the rubric criteria you want me to use."
            ),
            "citations": [],
            "feedback_hits": [],
            "calibration_hits": [],
        }

    # Format contexts
    rubric_ctx, rubric_cites = _format_citations(rubric_hits, "R")
    feedback_ctx, feedback_cites = _format_citations(feedback_hits, "F")

    calibration_ctx = ""
    calibration_cites: List[Dict[str, Any]] = []
    if calibration_hits:
        calibration_ctx, calibration_cites = _format_calibration(calibration_hits)

    # Tell the model explicitly when there are no instructor feedback examples
    feedback_note = ""
    if len(feedback_hits) == 0:
        feedback_note = "No instructor feedback examples were retrieved, rely on rubric context only. "

    system = (
        "You are Project Blackboard, an instructor assistant. "
        f"{feedback_note}"
        "Your job is to draft suggested instructor feedback (not a grade). "
        "Ground everything in the rubric context and the instructor feedback examples provided. "
        "Do not assign points, letter grades, or final judgments. "
        "If evidence is insufficient, say what is missing and ask one follow-up question. "
        "Always include citations like [R1] or [F2] after the sentence they support. "
        "Write a short instructor-style feedback note, 2–3 sentences total, Maximum 60 words total. "
        "Sentence 1 should acknowledge one specific strength. "
        "Sentence 2 should identify the most important improvement. "
        "Sentence 3 (optional) may suggest a concrete next step. "
        "Do not use headings or labels. Write as a brief paragraph. "
        "When calibration examples are provided, treat them as the authoritative standard for tone, strictness, and expectations. "
        "If there is any ambiguity, default to the patterns demonstrated in the calibration examples. "
        "Do not be more lenient than the calibration examples. "
        "If the writing style seems inconsistent or overly polished compared to typical student voice, "
        "include a brief voice caution note without accusing the student. "
        "Only include Voice caution when there is strong evidence of AI-generated or copy-pasted tone mismatch, otherwise omit it. "
    )

    if len(feedback_hits) > 0:
        feedback_section = f"\nInstructor feedback examples:\n{feedback_ctx}\n"
    else:
        feedback_section = "\nInstructor feedback examples:\n(none retrieved)\n"

    user = f"""Input:
{question_or_submission}

Rubric context:
{rubric_ctx}
{feedback_section}
Calibration examples (anchors):
{calibration_ctx}
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )

    return {
        "input": question_or_submission,
        "suggested_feedback": resp.choices[0].message.content,
        "citations": rubric_cites + feedback_cites + calibration_cites,
        "feedback_hits": feedback_hits,
        "calibration_hits": calibration_hits,
    }
