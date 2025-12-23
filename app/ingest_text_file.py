# app/ingest_text_file.py
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from app.embed import embed_texts
from app.db import insert_chunks


def split_by_chars(text: str, chunk_size: int = 2000, overlap: int = 300) -> List[str]:
    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:
            break

        start = max(0, end - overlap)

    return chunks


def ingest_txt_file(
    path: str,
    source: str,
    table: str = "rubric_chunks",
    chunk_size: int = 2000,
    overlap: int = 300,
    metadata: Optional[Dict] = None,
) -> int:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")

    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise ValueError(f"File is empty: {p}")

    chunks = split_by_chars(text, chunk_size=chunk_size, overlap=overlap)
    embeddings = embed_texts(chunks)

    md = metadata or {}
    metadatas = [md for _ in chunks]

    return insert_chunks(
        table=table,
        source=source,
        chunks=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def main():
    parser = argparse.ArgumentParser(description="Ingest a .txt file into a Postgres chunk table")
    parser.add_argument("--path", required=True, help="Path to the .txt file")
    parser.add_argument("--source", required=True, help="Source label stored in DB")
    parser.add_argument("--table", default="rubric_chunks", help="Target table, default rubric_chunks")
    parser.add_argument("--chunk_size", type=int, default=2000, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=300, help="Overlap in characters")
    parser.add_argument(
        "--metadata",
        default="{}",
        help='JSON object string, ex: \'{"course":"BA101","doc_type":"syllabus"}\'',
    )
    args = parser.parse_args()

    try:
        metadata = json.loads(args.metadata)
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a JSON object")
    except Exception as e:
        raise SystemExit(f"Invalid --metadata JSON: {e}")

    n = ingest_txt_file(
        path=args.path,
        source=args.source,
        table=args.table,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        metadata=metadata,
    )
    print(f"Inserted {n} chunks into {args.table} with source={args.source}")


if __name__ == "__main__":
    main()
