from typing import Optional, Dict, Any, List, Tuple
from openai import OpenAI

from .config import OPENAI_API_KEY
from .embed import embed_texts
from .retrieval import retrieve_similar, retrieve_calibration_examples

client = OpenAI(api_key=OPENAI_API_KEY)

def _format_citations(hits: Optional[List[Dict[str, Any]]], label: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Returns:
      - a context string with numbered citations
      - a citations list that maps citation numbers to chunk metadata
    """
    hits = hits or []
    ctx_lines = []
    cites = []
    for i, h in enumerate(hits, start=1):
        ctx_lines.append(f"[{label}{i}] (source={h['source']}, chunk={h['chunk_index']})\n{h['content']}\n")
        cites.append({
            "cite": f"{label}{i}",
            "source": h["source"],
            "chunk_index": h["chunk_index"],
            "id": h["id"],
            "distance": h["distance"],
        })
    return "\n".join(ctx_lines).strip(), cites

def _format_calibration(hits: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    ctx_lines = []
    cites = []
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

        cites.append({
            "cite": f"C{i}",
            "assignment_id": h.get("assignment_id"),
            "id": h.get("id"),
            "distance": h.get("distance"),
        })
    return "\n".join(ctx_lines).strip(), cites

def answer_from_rubric(question: str, top_k: int = 6) -> Dict[str, Any]:
    q_emb = embed_texts([question])[0]

    # --- retrieval happens here ---
    rubric_hits = retrieve_similar("rubric_chunks", q_emb, top_k=top_k)

    rubric_hits = rubric_hits or []
    if not rubric_hits:
        return {
            "question": question,
            "answer": "I don’t have any rubric context indexed yet, so I can’t answer from the rubric. Ingest your rubric first (rubric_chunks), then try again.",
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
    
    # Retrieve calibration examples
    calibration_hits = []
    calibration_ctx = ""
    calibration_cites = []

    if assignment_id:
        calibration_hits = retrieve_calibration_examples(
            query_embedding=q_emb,
            assignment_id=assignment_id,
            top_k=top_k_calibration,
            metadata_filter=None,  
        )
        calibration_ctx, calibration_cites = _format_calibration(calibration_hits)


    rubric_hits = retrieve_similar("rubric_chunks", q_emb, top_k=top_k_rubric)
    feedback_hits = retrieve_similar(
        "feedback_library",
        q_emb,
        top_k=top_k_feedback,
        metadata_filter=feedback_metadata_filter,
    )

    rubric_ctx, rubric_cites = _format_citations(rubric_hits, "R")
    feedback_ctx, feedback_cites = _format_citations(feedback_hits, "F")

    system = (
        "You are Project Blackboard, an instructor assistant. "
        "Your job is to draft suggested instructor feedback (not a grade). "
        "Ground everything in the rubric context and the instructor feedback examples provided. "
        "Do not assign points, letter grades, or final judgments. "
        "If evidence is insufficient, say what is missing and ask one follow-up question. "
        "Always include citations like [R1] or [F2] after the sentence they support. "
        "If the writing style seems inconsistent or overly polished compared to typical student voice, "
        "include a brief voice caution note without accusing the student."    
        "Keep it short and instructor-like. Maximum 60 words total. "
        "Write a short instructor-style feedback note, 2–3 sentences total. "
        "Sentence 1 should acknowledge one specific strength. "
        "Sentence 2 should identify the most important improvement. "
        "Sentence 3 (optional) may suggest a concrete next step. "
        "Do not use headings or labels. Write as a brief paragraph."
        "Under each heading use exactly 1 bullet, 1 sentence max per bullet. "
        "Only include Voice caution if you genuinely suspect a voice mismatch, and if included, it must be 1 bullet, 1 short sentence. "
        "Do not add extra bullets, extra sentences, or extra paragraphs. "
        "Only include Voice caution when there is strong evidence of AI-generated or copy-pasted tone mismatch, otherwise omit it. "
        "When calibration examples are provided, treat them as the authoritative standard for tone, strictness, and expectations. "
        "If there is any ambiguity, default to the patterns demonstrated in the calibration examples. "
        "Do not be more lenient than the calibration examples. "

    )

    user = f"""Input:
{question_or_submission}

Rubric context:
{rubric_ctx}

Instructor feedback examples:
{feedback_ctx}

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

    }
