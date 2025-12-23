from typing import Any, Dict, Optional, List
from pypdf import PdfReader
from .chunking import split_by_tokens
from .embed import embed_texts
from .db import insert_chunks

def read_pdf_plaintext(path: str) -> str:
    reader = PdfReader(path)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)

def ingest_pdf(
    path: str,
    table: str,
    source_label: Optional[str] = None,
    base_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    source = source_label or path
    base_metadata = base_metadata or {}

    raw_text = read_pdf_plaintext(path)
    chunks = split_by_tokens(raw_text)
    embeddings = embed_texts(chunks)

    metadatas: List[Dict[str, Any]] = []
    for i in range(len(chunks)):
        md = dict(base_metadata)
        md["chunk_index"] = i
        metadatas.append(md)

    return insert_chunks(
        table=table,
        source=source,
        chunks=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
