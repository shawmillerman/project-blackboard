import json
from typing import Any, Dict, List, Optional

from .embed import embed_texts
from .db import insert_chunks

def ingest_feedback_json(path: str, source_label: Optional[str] = None) -> int:
    """
    Accepts either:
      - JSONL (one json object per line)
      - JSON array (list of objects)
    Each object must contain a 'feedback' field (string). Everything else becomes metadata.
    """
    source = source_label or path

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    items: List[Dict[str, Any]] = []
    # JSONL detection: multiple lines that each parse
    if "\n" in raw and raw.lstrip().startswith("{"):
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    else:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            items = parsed
        else:
            raise ValueError("JSON must be a list of objects or JSONL lines")

    texts: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for obj in items:
        if "feedback" not in obj or not isinstance(obj["feedback"], str) or not obj["feedback"].strip():
            continue
        texts.append(obj["feedback"].strip())

        md = dict(obj)
        # Don't duplicate the main text in metadata
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
