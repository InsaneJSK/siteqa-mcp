import json
import os, re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def save_audit(
    report: dict,
    max_pages: int,
    output_dir: Path | None = None,
) -> dict:
    """Save one report and return the complete saved document."""
    directory = (
        output_dir
        if output_dir is not None
        else Path(os.environ.get("SITEQA_AUDIT_DIR", "audits"))
    )
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc)
    audit_id = (
        created_at.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex
    )
    path = directory / f"{audit_id}.json"

    document = {
        **report,
        "schema_version": 1,
        "audit_id": audit_id,
        "created_at": created_at.isoformat(),
        "report_path": str(path),
        "max_pages": max_pages,
    }

    # Serialize before opening the file so serialization errors
    # cannot leave an empty report behind.
    payload = json.dumps(document, indent=2, ensure_ascii=False)

    with path.open("x", encoding="utf-8") as file:
        file.write(payload + "\n")

    return document

def load_audit(
    audit_id: str,
    output_dir: Path | None = None,
) -> dict:
    """Load a report by ID from the configured audit directory."""
    if not re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{32}", audit_id):
        raise ValueError("Invalid audit ID")

    directory = (
        output_dir
        if output_dir is not None
        else Path(os.environ.get("SITEQA_AUDIT_DIR", "audits"))
    )

    path = directory.resolve() / f"{audit_id}.json"
    document = json.loads(path.read_text(encoding="utf-8"))

    if document.get("audit_id") != audit_id:
        raise ValueError("Report ID does not match its filename")

    return document
