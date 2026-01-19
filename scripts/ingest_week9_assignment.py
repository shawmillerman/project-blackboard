import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ingest import ingest_by_extension

PDF_PATH = "/Users/admin/Desktop/Blackboard Collateral (locked)/Week 9 Business Activity Assignment.docx"


rows = ingest_by_extension(
    path=PDF_PATH,
    table="rubric_chunks",
    source_label="BA101 Week 9 Business Activity Assignment",
    base_metadata={
        "course": "BA101",
        "assignment_id": "ba101_week_9",
        "rubric_id": "ba101_business_activity_core",
        "type": "assignment_context",
    },
)

print(f"Ingested {rows} rubric chunks")
