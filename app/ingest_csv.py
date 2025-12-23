import csv
from typing import Any, Dict, List, Optional

from .embed import embed_texts
from .db import insert_chunks

def ingest_feedback_csv(path: str, source_label: Optional[str] = None) -> int:
    source = source_label or path

    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "feedback" not in reader.fieldnames:
            raise ValueError("CSV must contain a 'feedback' column")

        for row in reader:
            feedback = (row.get("feedback") or "").strip()
            if not feedback:
                continue

            texts.append(feedback)

            md = dict(row)
            md.pop("feedback", None)
            metadatas.append(md)

    embeddings = embed_texts(texts)

    return insert_chunks(
        table="feedback_library",
        source=source,
        chunks=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
