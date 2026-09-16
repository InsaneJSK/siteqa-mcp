import json
from pathlib import Path
import pytest
import asyncio
import httpx
from mcp import Client
import siteqa_mcp.server as server

@pytest.fixture(autouse=True)
def isolated_audit_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("SITEQA_AUDIT_DIR", str(tmp_path))

def call_audit(arguments):
    async def run():
        async with Client(
            server.mcp, raise_exceptions=True
        ) as client:
            return await client.call_tool(
                "audit_site", arguments
            )

    return asyncio.run(run())


def test_mcp_audit_returns_findings_and_http_failures(monkeypatch):
    def handler(request):
        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text='<html><body><a href="/missing">Link</a></body></html>',
            )

        return httpx.Response(404)

    monkeypatch.setattr(
        server,
        "make_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(handler)
        ),
    )

    result = call_audit({"url": "https://example.com"})

    assert not result.is_error
    report = result.structured_content

    assert report["urls_attempted"] == 2
    assert report["html_pages_inspected"] == 1
    assert report["limit_reached"] is False
    assert {f["code"] for f in report["findings"]} == {
        "missing_title",
        "broken_internal_link",
    }
    assert report["fetch_issues"][0]["status_code"] == 404

    saved_path = Path(report["report_path"])
    assert saved_path.is_file()

    saved = json.loads(saved_path.read_text(encoding="utf-8"))

    assert saved["audit_id"] == report["audit_id"]
    assert saved["findings"] == report["findings"]
    assert saved["fetch_issues"] == report["fetch_issues"]
    assert saved["schema_version"] == 1
    assert saved["max_pages"] == 10


def test_mcp_audit_exposes_incomplete_coverage(monkeypatch):
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<title>Home</title><a href="/about">About</a>',
        )

    monkeypatch.setattr(
        server,
        "make_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(handler)
        ),
    )

    result = call_audit({
        "url": "https://example.com",
        "max_pages": 1,
    })

    assert not result.is_error
    report = result.structured_content

    assert report["findings"] == []
    assert report["limit_reached"] is True
    assert report["remaining_urls"] == [
        "https://example.com/about"
    ]


def test_mcp_audit_reports_network_failure(monkeypatch):
    def handler(request):
        raise httpx.ConnectError(
            "Connection refused", request=request
        )

    monkeypatch.setattr(
        server,
        "make_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(handler)
        ),
    )

    result = call_audit({"url": "https://example.com"})

    assert not result.is_error
    report = result.structured_content

    assert report["html_pages_inspected"] == 0
    assert len(report["fetch_issues"]) == 1
    assert "ConnectError" in report["fetch_issues"][0]["reason"]


def test_mcp_rejects_invalid_page_limit(monkeypatch):
    # Any unexpected request fails rather than reaching the internet.
    def handler(request):
        raise AssertionError("Invalid input must not trigger a request")

    monkeypatch.setattr(
        server,
        "make_http_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(handler)
        ),
    )

    result = call_audit({
        "url": "https://example.com",
        "max_pages": 0,
    })

    assert result.is_error
