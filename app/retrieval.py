from typing import Any, Dict, List, Optional
from psycopg.rows import dict_row
from psycopg.types.json import Json

from .db import get_conn

ALLOWED_TABLES = {"rubric_chunks", "feedback_library", "student_submissions", "calibration_examples"}


def _vec(v: List[float]) -> str:
    return "[" + ",".join(str(x) for x in v) + "]"


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
    params: List[Any] = []

    # for (embedding <=> %s::vector) in SELECT
    params.append(vec)

    if source_filter:
        where_clauses.append("source = %s")
        params.append(source_filter)

    if metadata_filter:
        # jsonb containment: metadata has at least these key/value pairs
        where_clauses.append("metadata @> %s::jsonb")
        params.append(Json(metadata_filter))

    where_sql = ""
    if where_clauses:
        where_sql = "where " + " and ".join(where_clauses)

    sql = f"""
        select id, source, chunk_index, content, metadata,
               (embedding <=> %s::vector) as distance
        from public.{table}
        {where_sql}
        order by embedding <=> %s::vector
        limit %s
    """

    # for ORDER BY distance + LIMIT
    params.append(vec)
    params.append(top_k)

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # MVP stability: force sequential scan (no ANN indexes)
            cur.execute("set enable_indexscan=off")
            cur.execute("set enable_bitmapscan=off")
            cur.execute("set enable_seqscan=on")

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
    params: List[Any] = [assignment_id]

    if metadata_filter:
        where_clauses.append("metadata @> %s::jsonb")
        params.append(Json(metadata_filter))

    where_sql = "where " + " and ".join(where_clauses)

    sql = f"""
        select id, source, assignment_id, submission_text, feedback_text, grade_numeric, metadata,
               (embedding <=> %s::vector) as distance
        from public.calibration_examples
        {where_sql}
        order by embedding <=> %s::vector
        limit %s
    """

    params_for_select = [vec] + params + [vec, top_k]

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("set enable_indexscan=off")
            cur.execute("set enable_bitmapscan=off")
            cur.execute("set enable_seqscan=on")

            cur.execute(sql, params_for_select)
            return cur.fetchall()
