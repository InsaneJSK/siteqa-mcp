# SiteQA MCP

A Python MCP server for deterministic website QA. It checks HTML titles, internal links, and canonical URLs, saves structured audit reports, and compares findings across runs.

An MCP-compatible agent can request audits and interpret the evidence. Detection and comparison do not require an LLM or API key.

## Features

- Same-origin crawling with a configurable URL limit.
- Redirect checks that prevent following redirects outside the starting origin.
- Seven finding types:
  - Missing or empty title
  - Multiple title tags
  - Duplicate titles across inspected pages
  - Broken internal links returning HTTP 404 or 410
  - Multiple canonical tags
  - Invalid canonical values
  - Broken internal canonical targets returning HTTP 404 or 410
- Timestamped JSON reports with unique audit IDs.
- Before/after comparison with resolved, remaining, newly observed, and unverified findings.
- Coverage checks that prevent incomplete audits from falsely proving resolution.

## Setup

Requires Python 3.11+ and uv. Development uses Python 3.11.9.

From the repository root:

```powershell
uv sync --frozen
uv run pytest -q
```

The current suite contains 44 tests covering parsing, fetching, crawling, findings, MCP calls, storage, and comparison.

## Run an audit

```powershell
uv run python -m siteqa_mcp.cli http://127.0.0.1:8000/ --max-pages 10
```

Reports are saved under `audits/` by default. The terminal displays the audit ID, saved path, and counts.

Choose another output folder:

```powershell
uv run python -m siteqa_mcp.cli http://127.0.0.1:8000/ --output-dir reports
```

`SITEQA_AUDIT_DIR` sets the default storage directory for both CLI and MCP calls. An explicit CLI output directory takes precedence.

## MCP tools

### audit_site(url, max_pages=10)

Crawls the starting origin, evaluates supported rules, saves a report, and returns findings, coverage, fetch issues, audit ID, and report path.

The URL limit accepts values from 1 to 100. Redirect requests are counted separately and capped at five redirects per fetch.

### compare_audits(before_id, after_id)

Loads two reports from the configured audit directory and returns:

- **Resolved:** absent from the later report, with comparable coverage.
- **Remaining:** present in both reports, including before/after evidence.
- **Newly observed:** present only in the later report.
- **Unverified:** absent later, but coverage differences or fetch issues prevent confirming resolution.

Use IDs in chronological before/after order. Both reports must have the same starting URL and schema version.

## Connect to Goose

Add a custom **Standard IO** extension named `SiteQA`.

Use this command, replacing the project path:

```text
uv --directory "<absolute-project-path>" run python -m siteqa_mcp.server
```

Goose starts the MCP server automatically. Set the extension timeout to 120 seconds for the local demo.

Example request:

> Use audit_site to audit http://127.0.0.1:8000/ with max_pages=10. Report the actual findings and coverage. Do not edit files.

Restart the extension after changing the server code.

## Reproduce the demo

The repository contains two fixtures:

- `src/siteqa_mcp/demo-site`: deliberately broken.
- `src/siteqa_mcp/demo-site-fixed`: corrected version.

Start the broken fixture:

```powershell
uv run python -m http.server 8000 --bind 127.0.0.1 --directory src/siteqa_mcp/demo-site
```

In another terminal, run an audit and retain its ID. Expected: **4 HTML pages inspected, 8 findings, and 2 expected 404 responses**.

Stop the website server and serve the fixed fixture on the same address:

```powershell
uv run python -m http.server 8000 --bind 127.0.0.1 --directory src/siteqa_mcp/demo-site-fixed
```

Run another audit. Expected: **4 HTML pages inspected, 0 findings, and 0 fetch issues**.

Compare the saved IDs:

```powershell
uv run python -c "import json; from siteqa_mcp.comparison import compare_saved_audits; print(json.dumps(compare_saved_audits('BEFORE_ID', 'AFTER_ID'), indent=2))"
```

Expected: **8 resolved**, zero remaining, newly observed, or unverified findings, and no coverage warnings.

## Scope and limitations (future scope)

- Inspects fetched HTML; does not execute JavaScript.
- Does not support HTML `<base>` elements or HTTP Link-header canonicals.
- Does not discover pages through sitemaps or implement robots.txt handling.
- External destinations are not checked.
- Missing canonical tags are not treated as defects.
- Duplicate titles do not establish duplicate content or ranking harm.
- Crawl limits, unreachable pages, and undiscovered URLs limit coverage.
- Comparison is conservative: changed HTML-page coverage prevents confirmed resolution.
- Findings describe technical checks, not SEO rankings or overall site health.
- Intended for local use on trusted, user-selected sites; it is not a hardened public crawling service.

## Architecture

```text
CLI / MCP
    ↓
Audit runner
    ↓
Crawler → HTTP fetcher → HTML parser
    ↓
Deterministic audit rules
    ↓
JSON storage → Report comparison
```