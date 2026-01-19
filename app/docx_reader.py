# filepath: /Users/admin/ProjectBlackboard/app/docx_reader.py
#
# Runtime module.
# DOCX extraction with heading hierarchy preservation.
#

from typing import Tuple, List, Dict, Any
from docx import Document


def read_docx_with_headings(path: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Read a DOCX file and extract body text while preserving heading hierarchy.
    
    Returns:
        (chunks_text, chunks_metadata)
        - chunks_text: List of text strings (body paragraphs prefixed with heading context)
        - chunks_metadata: List of dicts with h1, h2, h3, heading_path, source_file per chunk
    """
    doc = Document(path)
    
    chunks_text = []
    chunks_metadata = []
    
    current_h1 = None
    current_h2 = None
    current_h3 = None
    
    for para in doc.paragraphs:
        style_name = para.style.name if para.style else ""
        text = para.text.strip()
        
        if not text:
            continue
        
        # Update heading context based on style
        if style_name == "Heading 1":
            current_h1 = text
            current_h2 = None
            current_h3 = None
            continue  # Don't emit headings as chunks, only track them
        elif style_name == "Heading 2":
            current_h2 = text
            current_h3 = None
            continue
        elif style_name == "Heading 3":
            current_h3 = text
            continue
        
        # Body text: build heading prefix
        heading_parts = []
        if current_h1:
            heading_parts.append(f"H1: {current_h1}")
        if current_h2:
            heading_parts.append(f"H2: {current_h2}")
        if current_h3:
            heading_parts.append(f"H3: {current_h3}")
        
        heading_prefix = "\n".join(heading_parts)
        if heading_prefix:
            heading_prefix += "\n\n"
        
        # Build chunk text with heading context
        chunk_text = heading_prefix + text
        chunks_text.append(chunk_text)
        
        # Build metadata for this chunk
        heading_path = " > ".join(filter(None, [current_h1, current_h2, current_h3]))
        metadata = {
            "source_type": "docx",
            "h1": current_h1,
            "h2": current_h2,
            "h3": current_h3,
            "heading_path": heading_path or None,
            "source_file": path.split("/")[-1],
        }
        chunks_metadata.append(metadata)
    
    return chunks_text, chunks_metadata
