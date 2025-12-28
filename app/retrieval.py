import os
from typing import Any, Dict, List, Optional
from psycopg.rows import dict_row
from psycopg.types.json import Json

from .db import get_conn

ALLOWED_TABLES = {"rubric_chunks", "feedback_library", "student_submissions", "calibration_examples"}


def _vec(v: List[float]) -> str:
    return "[" + ",".join(str(x) for x in v) + "]"


def _maybe_force_seqscan(cur) -> None:
    """
    MVP debug switch. Use ONLY for stability testing without ANN indexes.
    Set FORCE_SEQSCAN=true locally. Keep it false in prod.
    """
    if os.getenv("FORCE_SEQSCAN", "false").lower() == "true":
        cur.execute("set enable_indexscan=off")
        cur.execute("set enable_bitmapscan=off")
        cur.execute("set enable_seqscan=on")


def retrieve_similar(
    table: str,
    query_embedding: List[float],
    top_k: int = 6,
    source_filter: Optional[str] = None,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table '{table}'. Allowed: {sorted(ALLOWED_TABLES)}")

    vec = _vec(query_embedding)

    where_clauses: List[str] = []
    filter_params: List[Any] = []

    if source_filter:
        where_clauses.append("source = %s")
        filter_params.append(source_filter)

    if metadata_filter:
        where_clauses.append("metadata @> %s::jsonb")
        filter_params.append(Json(metadata_filter))

    where_sql = ("where " + " and ".join(where_clauses)) if where_clauses else ""

    sql = f"""
        select id, source, chunk_index, content, metadata,
               cosine_distance(embedding, %s::vector) as distance
        from public.{table}
        {where_sql}
        order by cosine_distance(embedding, %s::vector)
        limit %s
    """



    # Placeholder order must match:
    # 1) vec for SELECT distance
    # 2) any filter params
    # 3) vec for ORDER BY
    # 4) limit
    params: List[Any] = [vec] + filter_params + [vec, top_k]

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _maybe_force_seqscan(cur)
            cur.execute(sql, params)
            return cur.fetchall()

def retrieve_calibration_examples(
    query_embedding: List[float],
    assignment_id: str,
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    vec = _vec(query_embedding)

    where_clauses: List[str] = ["assignment_id = %s"]
    where_params: List[Any] = [assignment_id]

    if metadata_filter:
        where_clauses.append("metadata @> %s::jsonb")
        where_params.append(Json(metadata_filter))

    where_sql = "where " + " and ".join(where_clauses)

    sql = f"""
        select
            id, source, assignment_id, submission_text, feedback_text, grade_numeric, metadata,
            cosine_distance(embedding, %s::vector) as distance
        from public.calibration_examples
        {where_sql}
        order by distance
        limit %s
    """

    params: List[Any] = [vec] + where_params + [top_k]

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _maybe_force_seqscan(cur)
            cur.execute(sql, params)
            return cur.fetchall()

def retrieve_calibration_examples_by_course(
    query_embedding: List[float],
    course: str,
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    vec = _vec(query_embedding)

    where_clauses: List[str] = ["metadata @> %s::jsonb"]
    where_params: List[Any] = [Json({"course": course})]

    if metadata_filter:
        where_clauses.append("metadata @> %s::jsonb")
        where_params.append(Json(metadata_filter))

    where_sql = "where " + " and ".join(where_clauses)

    sql = f"""
        select
            id, source, assignment_id, submission_text, feedback_text, grade_numeric, metadata,
            cosine_distance(embedding, %s::vector) as distance
        from public.calibration_examples
        {where_sql}
        order by distance
        limit %s
    """

    params: List[Any] = [vec] + where_params + [top_k]

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _maybe_force_seqscan(cur)
            cur.execute(sql, params)
            return cur.fetchall()

