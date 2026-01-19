#
# Runtime module.
# Canonical FastAPI app, routes, and request flow live here.
#

import os
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from .embed import embed_texts

load_dotenv()

def _pg_conn_string():
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_DSN")
    if not url:
        raise RuntimeError(
            "Set DATABASE_URL or SUPABASE_DB_DSN to your Supabase Postgres connection string"
        )
    return url

def get_conn():
    return psycopg.connect(_pg_conn_string(), autocommit=True)

def ensure_calibration_table():
    """
    Stores instructor-calibrated examples:
      - submission_text (student work)
      - feedback_text (what instructor wrote)
      - grade_numeric (optional)
      - embedding (pgvector)
      - metadata (jsonb) for course, assignment_id, rubric_version, etc.
    """
    sql = """
    create table if not exists public.calibration_examples (
        id uuid primary key default gen_random_uuid(),
        source text,
        assignment_id text not null,
        submission_text text not null,
        feedback_text text,
        grade_numeric double precision,
        embedding vector(1536),
        metadata jsonb default '{}'::jsonb,
        created_at timestamptz default now()
    );

    create index if not exists calibration_examples_assignment_idx
      on public.calibration_examples (assignment_id);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

def insert_chunks(
    table: str,
    source: str,
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict] | None = None,
) -> int:
    if metadatas is None:
        metadatas = [{} for _ in chunks]

    if not (len(chunks) == len(embeddings) == len(metadatas)):
        raise ValueError("chunks, embeddings, and metadatas must be same length")

    sql = f"""
        insert into public.{table}
        (source, chunk_index, content, embedding, metadata)
        values (%s, %s, %s, %s, %s)
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            for i, (chunk, emb, md) in enumerate(zip(chunks, embeddings, metadatas)):
                cur.execute(sql, (source, i, chunk, emb, Jsonb(md)))

    return len(chunks)
def insert_calibration_examples(
    source: str,
    assignment_id: str,
    submission_texts: list[str],
    embeddings: list[list[float]],
    feedback_texts: list[str] | None = None,
    grade_numerics: list[float] | None = None,
    metadatas: list[dict] | None = None,
) -> int:
    if feedback_texts is None:
        feedback_texts = [""] * len(submission_texts)
    if grade_numerics is None:
        grade_numerics = [None] * len(submission_texts)  # type: ignore
    if metadatas is None:
        metadatas = [{} for _ in submission_texts]

    if not (len(submission_texts) == len(embeddings) == len(feedback_texts) == len(grade_numerics) == len(metadatas)):
        raise ValueError("All calibration inputs must be same length")

    sql = """
        insert into public.calibration_examples
        (source, assignment_id, submission_text, feedback_text, grade_numeric, embedding, metadata)
        values (%s, %s, %s, %s, %s, %s, %s)
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            for sub, emb, fb, grade, md in zip(submission_texts, embeddings, feedback_texts, grade_numerics, metadatas):
                cur.execute(sql, (source, assignment_id, sub, fb, grade, emb, Jsonb(md)))

    return len(submission_texts)
def upsert_rubric(
    rubric_id: str,
    title: str | None = None,
    criteria_json: dict | None = None,
    weights_json: dict | None = None,
    philosophy_text: str | None = None,
) -> dict:
    """
    Insert or update a rubric by rubric_id.
    Returns the inserted/updated rubric as a dict.
    """
    conn = get_conn()
    try:
        result = conn.execute(
            """
            INSERT INTO public.rubrics 
            (rubric_id, title, criteria_json, weights_json, philosophy_text)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (rubric_id) DO UPDATE SET
                title = EXCLUDED.title,
                criteria_json = EXCLUDED.criteria_json,
                weights_json = EXCLUDED.weights_json,
                philosophy_text = EXCLUDED.philosophy_text,
                updated_at = now()
            RETURNING id, rubric_id, title, criteria_json, weights_json, philosophy_text, created_at, updated_at;
            """,
            (rubric_id, title, Jsonb(criteria_json), Jsonb(weights_json), philosophy_text),
        ).fetchone()
        
        if result:
            return {
                "id": str(result[0]),
                "rubric_id": result[1],
                "title": result[2],
                "criteria_json": result[3],
                "weights_json": result[4],
                "philosophy_text": result[5],
                "created_at": result[6],
                "updated_at": result[7],
            }
        else:
            raise ValueError(f"Failed to upsert rubric {rubric_id}")
    finally:
        conn.close()


def get_rubric_by_id(rubric_id: str) -> dict | None:
    """
    Retrieve a rubric by rubric_id.
    Returns the rubric as a dict, or None if not found.
    """
    conn = get_conn()
    try:
        result = conn.execute(
            """
            SELECT id, rubric_id, title, criteria_json, weights_json, philosophy_text, created_at, updated_at
            FROM public.rubrics
            WHERE rubric_id = %s;
            """,
            (rubric_id,),
        ).fetchone()
        
        if result:
            return {
                "id": str(result[0]),
                "rubric_id": result[1],
                "title": result[2],
                "criteria_json": result[3],
                "weights_json": result[4],
                "philosophy_text": result[5],
                "created_at": result[6],
                "updated_at": result[7],
            }
        else:
            return None
    finally:
        conn.close()

def insert_grading_trace(
    request_id: str,
    assignment_id: str,
    student_submission_text: str,
    model_output_feedback: str | None = None,
    model_output_score_low: float | None = None,
    model_output_score_high: float | None = None,
    rubric_id: str | None = None,
    course: str | None = None,
    grader_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Insert a grading trace (labeled example from AI suggestion).
    Returns the inserted trace as a dict.
    """
    conn = get_conn()
    try:
        result = conn.execute(
            """
            INSERT INTO public.grading_traces
            (request_id, assignment_id, student_submission_text, model_output_feedback, 
             model_output_score_low, model_output_score_high, rubric_id, course, grader_id, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, request_id, assignment_id, student_submission_text, model_output_feedback,
                      model_output_score_low, model_output_score_high, rubric_id, course, 
                      promoted_to_calibration, created_at;
            """,
            (request_id, assignment_id, student_submission_text, model_output_feedback,
             model_output_score_low, model_output_score_high, rubric_id, course, grader_id, Jsonb(metadata or {})),
        ).fetchone()
        
        if result:
            return {
                "id": str(result[0]),
                "request_id": result[1],
                "assignment_id": result[2],
                "student_submission_text": result[3],
                "model_output_feedback": result[4],
                "model_output_score_low": result[5],
                "model_output_score_high": result[6],
                "rubric_id": result[7],
                "course": result[8],
                "promoted_to_calibration": result[9],
                "created_at": result[10],
            }
        else:
            raise ValueError(f"Failed to insert grading trace {request_id}")
    finally:
        conn.close()


def update_trace_with_instructor_feedback(
    request_id: str,
    instructor_final_feedback: str,
    instructor_final_score: float | None = None,
) -> dict:
    """
    Update a grading trace with instructor feedback/score override.
    Returns the updated trace.
    """
    conn = get_conn()
    try:
        result = conn.execute(
            """
            UPDATE public.grading_traces
            SET instructor_final_feedback = %s,
                instructor_final_score = %s,
                updated_at = now()
            WHERE request_id = %s
            RETURNING id, request_id, assignment_id, instructor_final_feedback, instructor_final_score, 
                      promoted_to_calibration, created_at, updated_at;
            """,
            (instructor_final_feedback, instructor_final_score, request_id),
        ).fetchone()
        
        if result:
            return {
                "id": str(result[0]),
                "request_id": result[1],
                "assignment_id": result[2],
                "instructor_final_feedback": result[3],
                "instructor_final_score": result[4],
                "promoted_to_calibration": result[5],
                "created_at": result[6],
                "updated_at": result[7],
            }
        else:
            raise ValueError(f"Trace not found: {request_id}")
    finally:
        conn.close()


def promote_trace_to_calibration(trace_id: str) -> dict:
    """
    Promote a grading trace to calibration_examples.
    Copies instructor_final_* from trace into calibration_examples.
    Enforces assignment_id matching (no cross-assignment mixing).
    Returns the calibration example dict.
    """
    conn = get_conn()
    try:
        # 1. Fetch the trace
        trace = conn.execute(
            """
            SELECT id, request_id, assignment_id, student_submission_text, 
                   instructor_final_feedback, instructor_final_score, rubric_id, metadata
            FROM public.grading_traces
            WHERE id = %s;
            """,
            (trace_id,),
        ).fetchone()
        
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        
        trace_id, request_id, assignment_id, submission_text, feedback, score, rubric_id, trace_metadata = trace
        
        if not feedback or score is None:
            raise ValueError(f"Trace {request_id} is incomplete: missing instructor feedback or score")
        
        # 2. Embed the feedback
        embeddings = embed_texts([feedback])
        embedding_vec = embeddings[0] if embeddings else None
        
        # 3. Build calibration metadata (preserve assignment_id + rubric_id)
        cal_metadata = trace_metadata or {}
        cal_metadata["trace_id"] = str(trace_id)
        cal_metadata["trace_request_id"] = request_id
        cal_metadata["rubric_id"] = rubric_id
        
        # 4. Insert into calibration_examples with assignment_id enforcement
        cal_result = conn.execute(
            """
            INSERT INTO public.calibration_examples
            (source, assignment_id, submission_text, feedback_text, grade_numeric, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, assignment_id, grade_numeric, created_at;
            """,
            ("grading_trace", assignment_id, submission_text, feedback, score, embedding_vec, Jsonb(cal_metadata)),
        ).fetchone()
        
        if not cal_result:
            raise ValueError(f"Failed to insert calibration example from trace {request_id}")
        
        # 5. Mark trace as promoted
        conn.execute(
            """
            UPDATE public.grading_traces
            SET promoted_to_calibration = true,
                promotion_timestamp = now()
            WHERE id = %s;
            """,
            (trace_id,),
        )
        
        return {
            "calibration_example_id": str(cal_result[0]),
            "assignment_id": cal_result[1],
            "grade_numeric": cal_result[2],
            "created_at": cal_result[3],
            "trace_id": str(trace_id),
        }
    finally:
        conn.close()