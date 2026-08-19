"""Turns raw fetched HTML into plain text safe to store, display, and pass
to an LLM. Fetched web content is untrusted: this module strips executable
and non-content elements and caps length, but the *real* prompt-injection
defense is in analyzer.py, which frames this text as inert data the model
must never treat as instructions.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

MAX_TEXT_CHARS = 8000


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "template", "svg"]):
        tag.decompose()
    # Drop hidden elements often used to hide injected instructions from human readers.
    for tag in soup.find_all(style=lambda v: v and "display:none" in v.replace(" ", "").lower()):
        tag.decompose()
    for tag in soup.find_all(attrs={"hidden": True}):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = " ".join(text.split())
    return text[:MAX_TEXT_CHARS]


def classify_page_type(url: str, html: str) -> str:
    lower_url = url.lower()
    if any(seg in lower_url for seg in ("/about",)):
        return "about"
    if any(seg in lower_url for seg in ("/service", "/product", "/solutions")):
        return "services"
    if any(seg in lower_url for seg in ("/contact",)):
        return "contact"
    return "home"
