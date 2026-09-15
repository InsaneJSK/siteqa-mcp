from dataclasses import dataclass
import httpx
from siteqa_mcp.parser import parse_page, PageData
from siteqa_mcp.urls import resolve_url, same_origin
@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status_code: int | None
    content_type: str | None
    page: PageData | None
    error: str | None = None

def fetch_page(
    url: str,
    client: httpx.Client,
    allowed_origin: str | None = None,
) -> FetchResult:
    """Fetch HTML, optionally keeping every request on one origin."""
    current_url = resolve_url(url, "")

    if current_url is None:
        return FetchResult(
            url, None, None, None, None, "Invalid HTTP(S) URL"
        )

    # At most five redirects: six requests including the initial one.
    for attempt in range(6):
        if allowed_origin and not same_origin(
            allowed_origin, current_url
        ):
            return FetchResult(
                url, None, None, None, None,
                "Destination is outside the allowed origin",
            )

        try:
            response = client.get(
                current_url,
                follow_redirects=False,
                timeout=10.0,
            )
        except (httpx.RequestError, httpx.InvalidURL) as exc:
            return FetchResult(
                url, None, None, None, None,
                f"{type(exc).__name__}: {exc}",
            )

        content_type = (
            response.headers.get("content-type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        result = FetchResult(
            requested_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            page=None,
        )

        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            target = (
                resolve_url(str(response.url), location)
                if location else None
            )

            if target is None:
                result.error = "Redirect has no valid HTTP(S) destination"
                return result

            if allowed_origin and not same_origin(
                allowed_origin, target
            ):
                result.error = f"Redirect outside allowed origin: {target}"
                return result

            if attempt == 5:
                result.error = "Redirect limit exceeded"
                return result

            current_url = target
            continue

        if response.is_success and content_type == "text/html":
            result.page = parse_page(
                response.text, str(response.url)
            )

        return result

    raise RuntimeError("Unexpected end of redirect loop")

if __name__ == "__main__":
    # Example usage
    with httpx.Client() as client:
        result = fetch_page("https://example.com", client)
        print(result)