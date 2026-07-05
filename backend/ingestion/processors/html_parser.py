import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify


def parse_html_to_markdown(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    title_tag = soup.find("h1")
    title_text = title_tag.text.strip() if title_tag else "Untitled"

    md = markdownify(str(soup), heading_style="ATX")

    if len(md.strip()) < 50:
        extracted = trafilatura.extract(html, include_tables=True, favor_precision=True)
        if extracted:
            md = extracted

    return md, title_text
