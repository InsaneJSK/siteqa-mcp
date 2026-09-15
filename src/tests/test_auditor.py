from siteqa_mcp.auditor import audit_crawl
from siteqa_mcp.crawler import CrawlResult
from siteqa_mcp.fetcher import FetchResult
from siteqa_mcp.parser import PageData


def html_result(path, titles, links=None):
    url = f"https://example.com{path}"

    return FetchResult(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        page=PageData(
            url=url,
            titles=titles,
            links=links or [],
            canonicals=[],
        ),
    )


def make_crawl(pages, remaining=None):
    return CrawlResult(
        start_url="https://example.com/",
        pages=pages,
        remaining_urls=remaining or [],
        limit_reached=bool(remaining),
    )


def test_finds_missing_empty_and_multiple_titles():
    crawl = make_crawl([
        html_result("/", []),
        html_result("/empty", [""]),
        html_result("/multiple", ["First", "Second"]),
    ])

    findings = audit_crawl(crawl)

    assert {(f.code, f.page_url) for f in findings} == {
        ("missing_title", "https://example.com/"),
        ("missing_title", "https://example.com/empty"),
        ("multiple_titles", "https://example.com/multiple"),
    }


def test_duplicate_titles_include_other_page_evidence():
    crawl = make_crawl([
        html_result("/", ["Fintech Demo"]),
        html_result("/about", ["Fintech Demo"]),
    ])

    findings = audit_crawl(crawl)

    assert len(findings) == 2
    assert all(f.code == "duplicate_title" for f in findings)
    assert findings[0].evidence["other_pages"] == [
        "https://example.com/about"
    ]


def test_broken_link_points_to_source_page():
    missing = FetchResult(
        requested_url="https://example.com/missing",
        final_url="https://example.com/missing",
        status_code=404,
        content_type="text/html",
        page=None,
    )

    crawl = make_crawl([
        html_result("/", ["Home"], ["/missing"]),
        missing,
    ])

    findings = audit_crawl(crawl)

    assert len(findings) == 1
    assert findings[0].code == "broken_internal_link"
    assert findings[0].page_url == "https://example.com/"
    assert findings[0].evidence["status_code"] == 404


def test_unvisited_link_is_not_reported_as_broken():
    crawl = make_crawl(
        [html_result("/", ["Home"], ["/unchecked"])],
        remaining=["https://example.com/unchecked"],
    )

    assert audit_crawl(crawl) == []


def test_redirect_alias_does_not_create_duplicate_title():
    destination = html_result("/about", ["About"])
    alias = FetchResult(
        requested_url="https://example.com/old-about",
        final_url=destination.final_url,
        status_code=200,
        content_type="text/html",
        page=destination.page,
    )

    assert audit_crawl(make_crawl([destination, alias])) == []


def test_invalid_canonical_values():
    for href in ["", "javascript:void(0)", "/bad path", "/about#team"]:
        page = html_result("/", ["Home"])
        page.page.canonicals = [href]

        findings = audit_crawl(make_crawl([page]))

        assert len(findings) == 1
        assert findings[0].code == "invalid_canonical"
        assert findings[0].evidence["href"] == href


def test_multiple_canonical_tags():
    page = html_result("/", ["Home"])
    page.page.canonicals = ["/", "/preferred"]

    findings = audit_crawl(make_crawl([page]))

    assert [f.code for f in findings] == ["multiple_canonicals"]


def test_broken_canonical():
    page = html_result("/", ["Home"])
    page.page.canonicals = ["/removed"]

    removed = FetchResult(
        requested_url="https://example.com/removed",
        final_url="https://example.com/removed",
        status_code=410,
        content_type="text/html",
        page=None,
    )

    findings = audit_crawl(make_crawl([page, removed]))

    assert len(findings) == 1
    assert findings[0].code == "broken_canonical"
    assert findings[0].evidence["status_code"] == 410


def test_unchecked_canonical_is_not_reported_as_broken():
    for href in ["/unchecked", "https://other.com/preferred"]:
        page = html_result("/", ["Home"])
        page.page.canonicals = [href]

        assert audit_crawl(make_crawl([page])) == []