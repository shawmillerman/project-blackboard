#!/usr/bin/env python3
"""
Re-ingest the corrected BA101 Business Activity core rubric.
Clears old rubric data first, then ingests the new version.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import get_conn
from app.ingest import ingest_by_extension

RUBRIC_PATH = "data/ba101_documents/ba101_businessactivity_core_rubric.docx"
RUBRIC_ID = "ba101_business_activity_core"

def clear_old_rubric():
    """Delete existing rubric chunks with this rubric_id"""
    sql = """
        DELETE FROM public.rubric_chunks
        WHERE metadata->>'rubric_id' = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (RUBRIC_ID,))
            deleted = cur.rowcount
    return deleted

def main():
    print(f"Re-ingesting rubric: {RUBRIC_PATH}")
    print(f"Rubric ID: {RUBRIC_ID}\n")
    
    # Step 1: Clear old rubric data
    print("Step 1: Clearing old rubric chunks...")
    deleted = clear_old_rubric()
    print(f"  ✓ Deleted {deleted} old chunks\n")
    
    # Step 2: Ingest new rubric
    print("Step 2: Ingesting corrected rubric...")
    rows = ingest_by_extension(
        path=RUBRIC_PATH,
        table="rubric_chunks",
        source_label=f"BA101 Business Activity Core Rubric",
        base_metadata={
            "course": "BA101",
            "rubric_id": RUBRIC_ID,
            "type": "rubric",
        },
    )
    
    print(f"  ✓ Ingested {rows} new chunks\n")
    print("=" * 60)
    print("✓ Rubric re-ingestion complete!")
    print(f"  - Removed: {deleted} old chunks")
    print(f"  - Added: {rows} new chunks")
    print(f"  - Rubric ID: {RUBRIC_ID}")

if __name__ == "__main__":
    main()
