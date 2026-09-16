import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from siteqa_mcp.server import audit_site

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a website.")
    parser.add_argument("url", help="Starting URL")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=Path("audits"))
    args = parser.parse_args()

    report = audit_site(args.url, max_pages=args.max_pages)

    created_at = datetime.now(timezone.utc)
    audit_id = (
        created_at.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )

    document = {
        "schema_version": 1,
        "audit_id": audit_id,
        "created_at": created_at.isoformat(),
        "max_pages": args.max_pages,
        **asdict(report),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{audit_id}.json"

    with output_path.open("x", encoding="utf-8") as file:
        json.dump(document, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Saved audit: {output_path.resolve()}")
    print(
        f"{report.html_pages_inspected} HTML pages inspected | "
        f"{len(report.findings)} findings | "
        f"{len(report.fetch_issues)} fetch issues"
    )

    if report.limit_reached:
        print(f"Page limit reached: {len(report.remaining_urls)} URLs unchecked.")


if __name__ == "__main__":
    main()
