import httpx

from siteqa_mcp.fetcher import fetch_page


def test_fetches_html_after_redirect():
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(
                301,
                headers={"location": "/new"},
            )

        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<title>New page</title>",
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = fetch_page("https://example.com/old", client)

    assert result.requested_url == "https://example.com/old"
    assert result.final_url == "https://example.com/new"
    assert result.status_code == 200
    assert result.page is not None
    assert result.page.url == "https://example.com/new"
    assert result.page.titles == ["New page"]
    assert result.error is None


def test_preserves_404_without_parsing_error_page():
    def handler(request):
        return httpx.Response(
            404,
            headers={"content-type": "text/html"},
            text="<title>Not found</title>",
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = fetch_page("https://example.com/missing", client)

    assert result.status_code == 404
    assert result.page is None
    assert result.error is None


def test_skips_non_html():
    def handler(request):
        return httpx.Response(200, json={"message": "Hello"})

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = fetch_page("https://example.com/api", client)

    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.page is None


def test_reports_timeout():
    def handler(request):
        raise httpx.ReadTimeout(
            "Server did not respond",
            request=request,
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = fetch_page("https://example.com/slow", client)

    assert result.status_code is None
    assert result.page is None
    assert result.error.startswith("ReadTimeout:")