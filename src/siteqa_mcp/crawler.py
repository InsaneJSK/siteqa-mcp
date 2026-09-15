from collections import deque
from dataclasses import dataclass

import httpx

from siteqa_mcp.fetcher import FetchResult, fetch_page
from siteqa_mcp.urls import internal_link, resolve_url, resolve_canonical


@dataclass
class CrawlResult:
    start_url: str
    pages: list[FetchResult]
    remaining_urls: list[str]
    limit_reached: bool


def crawl_site(
    start_url: str,
    client: httpx.Client,
    max_pages: int = 10,
) -> CrawlResult:
    """Visit up to max_pages distinct queued URLs on one origin."""
    if not 1 <= max_pages <= 100:
        raise ValueError("max_pages must be between 1 and 100")

    start = resolve_url(start_url, "")
    if start is None:
        raise ValueError("start_url must be a valid HTTP(S) URL")

    queue = deque([start])
    discovered = {start}
    visited = set()
    pages = []

    while queue and len(pages) < max_pages:
        url = queue.popleft()

        if url in visited:
            continue

        visited.add(url)
        result = fetch_page(url, client, allowed_origin=start)
        pages.append(result)

        if result.page is None:
            continue

        # A redirect may land on an already inspected page.
        final_url = result.page.url
        already_inspected = final_url in visited and final_url != url
        visited.add(final_url)
        discovered.add(final_url)

        if already_inspected:
            continue

        canonical_targets = [
            target
            for href in result.page.canonicals
            if (target := resolve_canonical(final_url, href)) is not None
        ]

        candidates = result.page.links + canonical_targets

        for destination in internal_link(final_url, candidates):
            if destination not in discovered:
                discovered.add(destination)
                queue.append(destination)
    remaining = [url for url in queue if url not in visited]

    return CrawlResult(
        start_url=start,
        pages=pages,
        remaining_urls=remaining,
        limit_reached=bool(remaining),
    )