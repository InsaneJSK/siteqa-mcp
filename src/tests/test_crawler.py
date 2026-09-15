import httpx

from siteqa_mcp.crawler import crawl_site


def test_crawls_internal_links_once_and_preserves_404():
    requested = []

    def handler(request):
        path = request.url.path
        requested.append(path)

        if path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="""
                    <title>Home</title>
                    <a href="/about">About</a>
                    <a href="/about#team">Team</a>
                    <a href="/missing">Missing</a>
                    <a href="https://other.com">External</a>
                """,
            )

        if path == "/about":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text='<title>About</title><a href="/">Home</a>',
            )

        return httpx.Response(404)

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = crawl_site("https://example.com", client)

    assert requested == ["/", "/about", "/missing"]
    assert [page.status_code for page in result.pages] == [
        200, 200, 404
    ]
    assert result.remaining_urls == []
    assert result.limit_reached is False


def test_page_limit_reports_unvisited_urls():
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text='<title>Home</title><a href="/about">About</a>',
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = crawl_site(
            "https://example.com", client, max_pages=1
        )

    assert len(result.pages) == 1
    assert result.remaining_urls == ["https://example.com/about"]
    assert result.limit_reached is True


def test_does_not_follow_external_redirect():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(
            302,
            headers={"location": "https://other.com"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = crawl_site("https://example.com", client)

    assert requested == ["https://example.com/"]
    assert result.pages[0].status_code == 302
    assert result.pages[0].error.startswith(
        "Redirect outside allowed origin:"
    )


def test_redirect_loop_stops():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "/"})

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = crawl_site("https://example.com", client)

    assert len(requested) == 6
    assert result.pages[0].error == "Redirect limit exceeded"

def test_crawls_internal_canonical_target():
    requested = []

    def handler(request):
        requested.append(request.url.path)

        if request.url.path == "/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="""
                    <html>
                      <head>
                        <title>Home</title>
                        <link rel="canonical" href="/preferred">
                      </head>
                    </html>
                """,
            )

        return httpx.Response(404)

    with httpx.Client(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = crawl_site("https://example.com", client)

    assert requested == ["/", "/preferred"]
    assert result.pages[1].status_code == 404
