from dataclasses import dataclass

from siteqa_mcp.crawler import CrawlResult
from siteqa_mcp.urls import internal_link, resolve_url, resolve_canonical, same_origin


@dataclass
class Finding:
    code: str
    page_url: str
    message: str
    evidence: dict[str, str | int | list[str]]


def audit_crawl(crawl: CrawlResult) -> list[Finding]:
    """Identify title defects and confirmed broken internal links."""
    findings = []
    pages = {}
    responses = {}

    for result in crawl.pages:
        requested_url = resolve_url(result.requested_url, "")
        if requested_url is not None:
            responses[requested_url] = result

        if result.page is not None:
            # Multiple requested URLs can redirect to the same page.
            pages[result.page.url] = result.page

    titles_to_urls = {}

    for page in pages.values():
        if len(page.canonicals) > 1:
            findings.append(
                Finding(
                    code="multiple_canonicals",
                    page_url=page.url,
                    message="Page contains multiple canonical tags; review them.",
                    evidence={"canonicals": page.canonicals},
                )
            )

        for href in dict.fromkeys(page.canonicals):
            target = resolve_canonical(page.url, href)

            if target is None:
                findings.append(
                    Finding(
                        code="invalid_canonical",
                        page_url=page.url,
                        message=(
                            "Canonical is empty, contains whitespace or a "
                            "fragment, or cannot resolve to an HTTP(S) URL."
                        ),
                        evidence={"href": href},
                    )
                )
                continue

            if not same_origin(page.url, target):
                continue  # External target: not checked.

            response = responses.get(target)

            if response is not None and response.status_code in {404, 410}:
                findings.append(
                    Finding(
                        code="broken_canonical",
                        page_url=page.url,
                        message="Canonical points to a missing page.",
                        evidence={
                            "href": href,
                            "destination": target,
                            "status_code": response.status_code,
                            "final_url": response.final_url or target,
                        },
                    )
                )

        if not page.titles or not any(page.titles):
            findings.append(
                Finding(
                    code="missing_title",
                    page_url=page.url,
                    message="Page has no non-empty title.",
                    evidence={"titles": page.titles},
                )
            )

        if len(page.titles) > 1:
            findings.append(
                Finding(
                    code="multiple_titles",
                    page_url=page.url,
                    message="Page contains multiple title tags.",
                    evidence={
                        "count": len(page.titles),
                        "titles": page.titles,
                    },
                )
            )

        # Compare only pages with one usable title.
        if len(page.titles) == 1 and page.titles[0]:
            title = page.titles[0]
            titles_to_urls.setdefault(title, []).append(page.url)

        for destination in internal_link(page.url, page.links):
            response = responses.get(destination)

            if response is None:
                continue  # Not fetched; its status is unknown.

            if response.status_code in {404, 410}:
                findings.append(
                    Finding(
                        code="broken_internal_link",
                        page_url=page.url,
                        message="Internal link leads to a missing page.",
                        evidence={
                            "destination": destination,
                            "status_code": response.status_code,
                            "final_url": response.final_url or destination,
                        },
                    )
                )

    for title, urls in titles_to_urls.items():
        if len(urls) < 2:
            continue

        for url in urls:
            findings.append(
                Finding(
                    code="duplicate_title",
                    page_url=url,
                    message="Another inspected page uses the same title.",
                    evidence={
                        "title": title,
                        "other_pages": [
                            other for other in urls if other != url
                        ],
                    },
                )
            )

    return findings