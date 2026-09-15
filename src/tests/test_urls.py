import pytest

from siteqa_mcp.urls import (
    internal_link,
    resolve_url,
    same_origin,
)


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("/about", "https://example.com/about"),
        ("pricing", "https://example.com/blog/pricing"),
        ("../help", "https://example.com/help"),
        ("#fees", "https://example.com/blog/post"),
        ("?currency=inr", "https://example.com/blog/post?currency=inr"),
        ("mailto:hello@example.com", None),
        ("javascript:void(0)", None),
        ("https://example.com:bad/path", None),
    ],
)
def test_resolve_url(href, expected):
    assert resolve_url(
        "https://example.com/blog/post", href
    ) == expected


def test_normalizes_hostname_and_default_port():
    assert resolve_url(
        "https://example.com",
        "https://EXAMPLE.com:443/about#team",
    ) == "https://example.com/about"


def test_origin_comparison():
    assert same_origin(
        "https://example.com",
        "https://example.com:443/about",
    )
    assert not same_origin(
        "https://example.com",
        "http://example.com",
    )
    assert not same_origin(
        "https://example.com",
        "https://blog.example.com",
    )
    assert not same_origin(
        "http://localhost:8000",
        "http://localhost:9000",
    )


def test_internal_links_filters_and_deduplicates():
    links = [
        "/about",
        "/about#team",
        "#fees",
        "",
        "mailto:hello@example.com",
        "https://other.com/contact",
        "/pricing?currency=inr",
    ]

    assert internal_link(
        "https://example.com/", links
    ) == [
        "https://example.com/about",
        "https://example.com/pricing?currency=inr",
    ]