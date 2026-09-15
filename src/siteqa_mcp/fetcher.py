from dataclasses import dataclass
import httpx
from siteqa_mcp.parser import parse_page, PageData

@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int | None
    content_type: str | None
    page: PageData | None
    error: str | None = None

def fetch_page(url: str, client: httpx.Client) -> FetchResult:
    """Fetch a URL and parse successful HTML responses."""
    try:
        response = client.get(url, follow_redirects=True, timeout=10.0)
    except (httpx.RequestError, httpx.InvalidURL) as e:
        return FetchResult(
            requested_url=url,
            final_url=None,
            status_code=None,
            content_type=None,
            page=None,
            error=f"{type(e).__name__}: {e}",
        )
    content_type = (response.headers.get("content-type", "").split(";", 1)[0].strip().lower())
    page = None
    if response.is_success and content_type == "text/html":
        page = parse_page(response.text, str(response.url))
    return FetchResult(
        requested_url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=content_type,
        page=page,
    )

if __name__ == "__main__":
    # Example usage
    with httpx.Client() as client:
        result = fetch_page("https://example.com", client)
        print(result)