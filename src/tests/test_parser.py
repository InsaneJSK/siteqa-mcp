from siteqa_mcp.parser import parse_page


def test_extracts_metadata_and_preserves_raw_links():
    html = """
    <html>
      <head>
        <title>  Fintech
          Demo  </title>
        <link rel="canonical" href="/pricing">
      </head>
      <body>
        <a href="/about">About</a>
        <a href="#fees">Fees</a>
        <a href="mailto:hello@example.com">Email</a>
        <a>No destination</a>
      </body>
    </html>
    """

    page = parse_page(html, "https://example.com/pricing")

    assert page.url == "https://example.com/pricing"
    assert page.titles == ["Fintech Demo"]
    assert page.canonicals == ["/pricing"]
    assert page.links == [
        "/about",
        "#fees",
        "mailto:hello@example.com",
    ]


def test_missing_metadata():
    page = parse_page("<html><body>Hello</body></html>",
                      "https://example.com")

    assert page.titles == []
    assert page.canonicals == []
    assert page.links == []


def test_preserves_empty_and_multiple_metadata():
    html = """
    <title> </title>
    <title>Another title</title>
    <link rel="CANONICAL" href="">
    <link rel="alternate canonical" href="/preferred">
    """

    page = parse_page(html, "https://example.com")

    assert page.titles == ["", "Another title"]
    assert page.canonicals == ["", "/preferred"]