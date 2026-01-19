import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ingest import ingest_by_extension

# Week 1 assignment file path
WEEK1_PATH = "/Users/admin/Desktop/Blackboard Collateral (locked)/Week 1"

# Find all .docx files in the Week 1 folder
week1_files = list(Path(WEEK1_PATH).glob("*.docx"))

if not week1_files:
    print(f"No .docx files found in {WEEK1_PATH}")
    sys.exit(1)

print(f"Found {len(week1_files)} Week 1 file(s) to ingest:\n")
for f in week1_files:
    print(f"  - {f.name}")

total_chunks = 0

for docx_file in week1_files:
    print(f"\nIngesting: {docx_file.name}...")
    
    rows = ingest_by_extension(
        path=str(docx_file),
        table="rubric_chunks",
        source_label=f"BA101 Week 1 Assignment - {docx_file.stem}",
        base_metadata={
            "course": "BA101",
            "assignment_id": "ba101_week_1",
            "rubric_id": "ba101_business_activity_core",
            "type": "assignment_context",
        },
    )
    
    print(f"  ✓ Ingested {rows} chunks from {docx_file.name}")
    total_chunks += rows

print(f"\n✓ Week 1 ingestion complete: {total_chunks} total chunks ingested")
print(f"  - assignment_id: ba101_week_1")
print(f"  - rubric_id: ba101_business_activity_core")
print(f"  - course: BA101")
