from dataclasses import dataclass
from bs4 import BeautifulSoup

@dataclass
class PageData:
    url: str
    titles: list[str]
    links: list[str]
    canonicals: list[str]

def parse_page(html: str, url: str) -> PageData:
    """Extract page metadata and raw link destinations from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    titles = [
        " ".join(title.get_text(" ", strip=True).split()) for title in soup.find_all('title')
    ]
    links = [
        tag["href"].strip() for tag in soup.find_all("a", href=True)
    ]
    canonicals = [
        tag.get("href", "").strip() for tag in soup.find_all("link")
        if "canonical" in [val.lower() for val in tag.get("rel", [])]
    ]
    
    return PageData(url=url, titles=titles, links=links, canonicals=canonicals)