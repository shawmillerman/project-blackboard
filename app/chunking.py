from typing import List
import tiktoken

def split_by_tokens(text: str, max_tokens: int = 500, overlap: int = 100) -> List[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk = enc.decode(tokens[start:end])
        chunks.append(chunk)
        if end == len(tokens):
            break
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]