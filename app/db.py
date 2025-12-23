import os
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

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
