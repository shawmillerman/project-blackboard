#!/usr/bin/env python3
import re
from pypdf import PdfReader

# The FIXED patterns (same as in grade_batch.py)
def apply_patterns(text):
    cleaned = text
    
    # Pattern 1: Initial "Note: To edit" block - first occurrence only
    cleaned = re.sub(
        r"^Note:\s+To\s+edit\s+this\s+document[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*visible\.",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern 2: Assignment title block
    cleaned = re.sub(
        r"^Week\s+1\s+Business\s+Activity:[^\n]*\n.*?submit\s+your\s+assignment!?",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    
    # Pattern 3-5: Question prompts
    cleaned = re.sub(
        r"^1\.\s+What\s+are\s+the\s+factors\s+of\s+production\s+needed\s+by\s+a\s+surfboard\s+manufacturer\?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE
    )
    cleaned = re.sub(
        r"^2\.\s+Where\s+does\s+the\s+surfboard\s+company\s+get\s+these\s+factors\s+of\s+production\?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE
    )
    cleaned = re.sub(
        r"^3\.\s+Where\s+does\s+the\s+company\s+get\s+money\s+to\s+pay\s+for\s+additional\s+resources\?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern 6: "Answer each question..." instruction block
    cleaned = re.sub(
        r"^Answer\s+each\s+question\s+in\s+the\s+box\s+below[^\n]*\n.*?submit\s+your\s+assignment!?",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    
    return cleaned

# Load the original PDF
reader = PdfReader("data/ba101_submissions/week_1/raw_submissions/anon-001-raw.pdf")
raw_text = ""
for page in reader.pages:
    raw_text += page.extract_text() or ""

print("=" * 80)
print("ORIGINAL RAW TEXT (first 1000 chars):")
print("=" * 80)
print(raw_text[:1000])

print("\n" + "=" * 80)
print("APPLYING ALL PATTERNS WITH NEW APPROACH (limited span, first occurrence only):")
print("=" * 80)

cleaned = apply_patterns(raw_text)

# Normalize
paragraphs = cleaned.split('\n\n')
cleaned_paras = [" ".join(p.split()).strip() for p in paragraphs if p.strip()]
final = "\n\n".join(cleaned_paras)

print(f"\nOriginal length: {len(raw_text)}")
print(f"Final length: {len(final)}")
print(f"Removed: {len(raw_text) - len(final)} chars")
print(f"\nFinal paragraph count: {len(cleaned_paras)}")
print("\nFinal text:")
for i, para in enumerate(cleaned_paras, 1):
    print(f"\nPara {i}:")
    print(para[:200] + ("..." if len(para) > 200 else ""))

