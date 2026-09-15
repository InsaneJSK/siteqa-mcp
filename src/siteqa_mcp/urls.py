from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

def resolve_url(base_url: str, href: str) -> str | None:
    """Resolve an HTTP(S) destination, removing its fragment."""
    href = href.strip()
    try:
        absolute_url, _ = urldefrag(urljoin(base_url, href))
        parts = urlsplit(absolute_url)
        if parts.scheme.lower() not in ("http", "https"):
            return None
        if not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None

        # Accessing .port validates malformed port values.
        port = parts.port
        scheme = parts.scheme.lower()
        hostname = parts.hostname.lower()

        # Preserve brackets around IPv6 addresses
        host = f"[{hostname}]" if ":" in hostname else hostname
        default_port = 443 if scheme == "https" else 80

        if port is not None and port != default_port:
            host = f"{host}:{port}"

        return urlunsplit((scheme, host, parts.path or "/", parts.query, ""))
    except ValueError:
        return None

def same_origin(first_url: str, second_url: str) -> bool:
    """Compare scheme, hostname, and effective port."""
    first = resolve_url(first_url, "")
    second = resolve_url(second_url, "")

    if first is None or second is None:
        return False

    first_parts = urlsplit(first)
    second_parts = urlsplit(second)

    return (first_parts.scheme, first_parts.netloc) == (second_parts.scheme, second_parts.netloc)

def internal_link(page_url: str, hrefs = list[str]) -> list[str]:
    """Return unique same-origin destinations in discovery order"""
    current_url = resolve_url(page_url, "")
    destinations = []
    seen = set()
    if current_url is None:
        return destinations
    for href in hrefs:
        destination = resolve_url(current_url, href)
        if destination is None or destination == current_url:
            continue
        if not same_origin(current_url, destination):
            continue
        if destination not in seen:
            destinations.append(destination)
            seen.add(destination)
    return destinations

def resolve_canonical(page_url: str, href: str) -> str | None:
    """Resolve a canonical target using our basic validation rules."""
    href = href.strip()

    if not href or "#" in href:
        return None

    if any(character.isspace() for character in href):
        return None

    return resolve_url(page_url, href)
