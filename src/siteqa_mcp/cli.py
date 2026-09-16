import argparse
from pathlib import Path

from siteqa_mcp.server import run_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a website.")
    parser.add_argument("url", help="Starting URL")
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    report = run_audit(
        args.url,
        max_pages=args.max_pages,
        output_dir=args.output_dir,
    )

    print(f"Audit ID: {report.audit_id}")
    print(f"Saved audit: {report.report_path}")
    print(
        f"{report.html_pages_inspected} HTML pages inspected | "
        f"{len(report.findings)} findings | "
        f"{len(report.fetch_issues)} fetch issues"
    )

    if report.limit_reached:
        print(
            f"Page limit reached: "
            f"{len(report.remaining_urls)} URLs unchecked."
        )


if __name__ == "__main__":
    main()
