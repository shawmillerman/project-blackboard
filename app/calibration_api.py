from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from .embed import embed_texts
from .db import insert_calibration_examples  # you should already have this from earlier steps

router = APIRouter(prefix="/calibration", tags=["calibration"])


class CalibrationExample(BaseModel):
    submission_text: str = Field(..., min_length=3)
    feedback_text: str = Field(..., min_length=3)
    grade_numeric: Optional[float] = None
    component_scores: Optional[Dict[str, float]] = Field(None, description="Component-level scores (directions, content, style)")
    metadata: Optional[Dict[str, Any]] = None


class CalibrationIngestRequest(BaseModel):
    assignment_id: str = Field(..., min_length=1)
    course: Optional[str] = None
    rubric_version: Optional[str] = None
    source: Optional[str] = None
    examples: List[CalibrationExample] = Field(..., min_items=1)


@router.post("/ingest")
def ingest_calibration(payload: CalibrationIngestRequest):
    # Embed the student submission text, this is what you want similarity search on
    texts = [ex.submission_text for ex in payload.examples]
    embeddings = embed_texts(texts)

    metadatas: List[Dict[str, Any]] = []
    for ex in payload.examples:
        md = dict(ex.metadata or {})
        if payload.course:
            md.setdefault("course", payload.course)
        if payload.rubric_version:
            md.setdefault("rubric_version", payload.rubric_version)
        # Include component scores in metadata if provided
        if ex.component_scores:
            md["component_scores"] = ex.component_scores
        metadatas.append(md)

    inserted = insert_calibration_examples(
        assignment_id=payload.assignment_id,
        source=payload.source or "manual",
        submission_texts=[ex.submission_text for ex in payload.examples],
        feedback_texts=[ex.feedback_text for ex in payload.examples],
        grade_numerics=[ex.grade_numeric for ex in payload.examples],
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return {"status": "ok", "inserted": inserted, "assignment_id": payload.assignment_id}
