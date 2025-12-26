#
# Runtime module.
# Canonical FastAPI app, routes, and request flow live here.
#
import uuid
import time
import logging
from .calibration_api import router as calibration_router
from collections import deque
from typing import Optional, Any, Dict, List
from fastapi import FastAPI, Query, Request, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from .db import ensure_calibration_table, insert_calibration_examples
from .embed import embed_texts
from .qa import answer_from_rubric, suggest_feedback
from contextlib import asynccontextmanager
from app.calibration_api import router as calibration_router

# -------------------------------------------------
# Environment + App
# -------------------------------------------------

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_calibration_table()
    yield

app = FastAPI(
    title="Project Blackboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(calibration_router)

# -------------------------------------------------
# Logging
# -------------------------------------------------

logger = logging.getLogger("project_blackboard")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# -------------------------------------------------
# Rate Limiting (simple, in-memory)
# -------------------------------------------------

RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_REQUESTS = 20  # per IP per window
_ip_hits: dict[str, deque[float]] = {}


def _rate_limit_or_raise(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    q = _ip_hits.get(ip)
    if q is None:
        q = deque()
        _ip_hits[ip] = q

    while q and (now - q[0]) > RATE_LIMIT_WINDOW_SEC:
        q.popleft()

    if len(q) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again soon")

    q.append(now)


# -------------------------------------------------
# Models
# -------------------------------------------------

class FeedbackSuggestRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Student submission text or instructor prompt")
    course: Optional[str] = Field(None, description="Course identifier, e.g., BA101")
    assignment_id: Optional[str] = Field(None, description="Assignment id for calibration examples, ex: business_activity_weekly")
    assignment_type: Optional[str] = Field(None, description="Assignment type, e.g., reflection or case_study")
    category: Optional[str] = Field(None, description="Feedback category, e.g., clarity or missing_examples")
    severity: Optional[str] = Field(None, description="Severity level, e.g., minor or major")
    top_k_rubric: int = Field(6, ge=1, le=20)
    top_k_feedback: int = Field(6, ge=1, le=20)

class FeedbackSuggestResponse(BaseModel):
    request_id: str
    input: str
    suggested_feedback: str
    citations: List[Dict[str, Any]]
    score_range_text: Optional[str] = None
    score_low: Optional[float] = None
    score_high: Optional[float] = None
    points_possible: Optional[float] = 40.0

# -------------------------------------------------
# Health
# -------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "Project Blackboard API is live"}


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------------------------------
# Tier 1 MVP – Rubric Answer
# -------------------------------------------------
@app.get("/tier1/rubric-answer", include_in_schema=False)
@app.get("/tier1/course-answer")
def tier1_rubric_answer(
    request: Request,
    question: str = Query(..., min_length=3),
    top_k: int = 6,
):
    request_id = str(uuid.uuid4())
    t0 = time.time()

    _rate_limit_or_raise(request)

    try:
        result = answer_from_rubric(question=question, top_k=top_k)

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(
            "tier1_rubric_answer ok request_id=%s ip=%s text_len=%s top_k=%s citations=%s elapsed_ms=%s",
            request_id,
            request.client.host if request.client else None,
            len(question or ""),
            top_k,
            len(result.get("citations", [])),
            elapsed_ms,
        )

        result["request_id"] = request_id
        return result

    except Exception:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.exception(
            "tier1_rubric_answer failed request_id=%s ip=%s elapsed_ms=%s",
            request_id,
            request.client.host if request.client else None,
            elapsed_ms,
        )
        raise


# -------------------------------------------------
# Tier 2 MVP – Feedback Suggestion (GET – dev/testing)
# -------------------------------------------------

@app.get("/tier2/feedback-suggest")
def tier2_feedback_suggest(
    text: str = Query(..., min_length=3),
    top_k_rubric: int = 6,
    top_k_feedback: int = 6,
):
    return suggest_feedback(
        question_or_submission=text,
        top_k_rubric=top_k_rubric,
        top_k_feedback=top_k_feedback,
    )


# -------------------------------------------------
# Tier 2 MVP – Feedback Suggestion (POST – product)
# -------------------------------------------------

app.post("/tier2/feedback-suggest", response_model=FeedbackSuggestResponse)
def tier2_feedback_suggest_post(request: Request, payload: FeedbackSuggestRequest):
    request_id = str(uuid.uuid4())
    t0 = time.time()

    _rate_limit_or_raise(request)

    # ---- metadata filtering ----
    metadata = {"course": (payload.course or "BA101")}
    if payload.assignment_type:
        metadata["assignment_type"] = payload.assignment_type
    if payload.category:
        metadata["category"] = payload.category
    if payload.severity:
        metadata["severity"] = payload.severity

    # ---- core feedback generation ----
    try:
        result = suggest_feedback(
            question_or_submission=payload.text,
            top_k_rubric=payload.top_k_rubric,
            top_k_feedback=payload.top_k_feedback,
            feedback_metadata_filter=metadata,
            assignment_id=payload.assignment_id,
        )
        result["request_id"] = request_id

    except Exception as e:
        logger.exception(
            "tier2_feedback_suggest failed request_id=%s ip=%s",
            request_id,
            request.client.host if request.client else None,
        )
        raise HTTPException(status_code=500, detail="Feedback generation failed")

    # ---- optional grading pipeline (OFF for MVP) ----
    ENABLE_SCORE_RANGE = False

    if ENABLE_SCORE_RANGE:
        points_possible = float(getattr(payload, "points_possible", 40.0))
        low, high, score_text = compute_score_range_from_feedback_hits(
            result.get("feedback_hits", []),
            points_possible,
        )
        result["score_range_text"] = score_text
        result["score_low"] = low
        result["score_high"] = high
        result["points_possible"] = points_possible

    # ---- logging + cleanup ----
    elapsed_ms = int((time.time() - t0) * 1000)
    logger.info(
        "tier2_feedback_suggest ok request_id=%s ip=%s course=%s assignment_type=%s category=%s severity=%s text_len=%s top_k_rubric=%s top_k_feedback=%s citations=%s elapsed_ms=%s",
        request_id,
        request.client.host if request.client else None,
        metadata.get("course"),
        metadata.get("assignment_type"),
        metadata.get("category"),
        metadata.get("severity"),
        len(payload.text or ""),
        payload.top_k_rubric,
        payload.top_k_feedback,
        len(result.get("citations", [])),
        elapsed_ms,
    )

    result.pop("feedback_hits", None)
    return result


    





