from pathlib import Path
from typing import Any

from siteqa_mcp.storage import load_audit


def finding_key(finding: dict) -> tuple:
    """Match findings by rule, source page, and affected target."""
    evidence = finding.get("evidence", {})

    target = evidence.get("destination")
    if target is None:
        target = evidence.get("href", "")

    return (
        finding["code"],
        finding["page_url"],
        target,
    )


def compare_saved_audits(
    before_id: str,
    after_id: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    before = load_audit(before_id, output_dir)
    after = load_audit(after_id, output_dir)

    if before["start_url"] != after["start_url"]:
        raise ValueError("Audits must have the same starting URL")

    if before.get("schema_version") != after.get("schema_version"):
        raise ValueError("Audit schema versions differ")

    warnings = []

    before_urls = before.get("inspected_urls")
    after_urls = after.get("inspected_urls")

    if before_urls is None or after_urls is None:
        warnings.append("A report lacks inspected-page coverage.")
    elif not before_urls or not after_urls:
        warnings.append("A report contains no inspected HTML pages.")
    elif set(before_urls) != set(after_urls):
        warnings.append("The audits inspected different sets of HTML pages.")

    if (
        before.get("limit_reached")
        or after.get("limit_reached")
        or before.get("remaining_urls")
        or after.get("remaining_urls")
    ):
        warnings.append("At least one audit left discovered URLs unchecked.")

    if after.get("fetch_issues"):
        warnings.append("The later audit contains fetch issues.")

    if before.get("scope") != after.get("scope"):
        warnings.append("The audit scope descriptions differ.")

    old = {
        finding_key(finding): finding
        for finding in before["findings"]
    }
    new = {
        finding_key(finding): finding
        for finding in after["findings"]
    }

    disappeared = [
        finding for key, finding in old.items()
        if key not in new
    ]

    remaining = [
        {
            "before": old[key],
            "after": finding,
        }
        for key, finding in new.items()
        if key in old
    ]

    newly_observed = [
        finding for key, finding in new.items()
        if key not in old
    ]

    # Conservative: incomplete or changed coverage cannot prove resolution.
    resolved = disappeared if not warnings else []
    unverified = disappeared if warnings else []

    return {
        "before_id": before_id,
        "after_id": after_id,
        "start_url": before["start_url"],
        "summary": {
            "resolved": len(resolved),
            "remaining": len(remaining),
            "newly_observed": len(newly_observed),
            "unverified": len(unverified),
        },
        "resolved": resolved,
        "remaining": remaining,
        "newly_observed": newly_observed,
        "unverified": unverified,
        "coverage_warnings": warnings,
    }
