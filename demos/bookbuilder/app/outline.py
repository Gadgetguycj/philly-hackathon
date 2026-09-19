"""The outline request, and a strict parser for the reply."""

import json
import re
from dataclasses import dataclass, field

PAGES_PER_CHAPTER = 8
MAX_SUMMARY_CHARS = 400
_FENCE = re.compile(r"^```[a-zA-Z0-9]*\s*|\s*```$")


class OutlineError(Exception):
    """The reply did not have the shape we asked for."""


@dataclass
class Chapter:
    number: int
    title: str
    summary: str
    pages: int
    first_page: int = 0

    @property
    def last_page(self) -> int:
        return self.first_page + self.pages - 1


@dataclass
class Outline:
    title: str
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def total_pages(self) -> int:
        return sum(chapter.pages for chapter in self.chapters)

    def chapter_for_page(self, page: int) -> Chapter:
        for chapter in self.chapters:
            if chapter.first_page <= page <= chapter.last_page:
                return chapter
        raise IndexError(page)

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "chapters": [
                {
                    "number": c.number,
                    "title": c.title,
                    "summary": c.summary,
                    "pages": c.pages,
                    "first_page": c.first_page,
                    "last_page": c.last_page,
                }
                for c in self.chapters
            ],
        }

    def compact_lines(self) -> str:
        return "\n".join(
            f"{c.number}. {c.title} (pages {c.first_page} to {c.last_page}): {c.summary}"
            for c in self.chapters
        )


def from_dict(payload: dict) -> Outline:
    chapters = [
        Chapter(
            number=int(c["number"]),
            title=str(c["title"]),
            summary=str(c["summary"]),
            pages=int(c["pages"]),
            first_page=int(c["first_page"]),
        )
        for c in payload["chapters"]
    ]
    return Outline(title=str(payload["title"]), chapters=chapters)


def messages(idea: str, title: str, pages: int, firmer: bool = False) -> list[dict]:
    wanted = max(1, round(pages / PAGES_PER_CHAPTER))
    title_rule = (
        f'Use exactly this title: "{title}".'
        if title
        else "Invent a title that fits the idea."
    )
    system = (
        "You plan books. You answer with one JSON object and no other text. "
        "No prose before it, no prose after it, no code fence."
    )
    user = (
        f"Book idea from the reader: {idea}\n\n"
        f"Plan a book of exactly {pages} pages, where a page is about 300 words.\n"
        f"{title_rule}\n"
        f"Use about {wanted} chapters. Every chapter needs at least 1 page. "
        f"The pages field of every chapter must add up to exactly {pages}.\n\n"
        "Answer with this JSON object and nothing else:\n"
        '{"title": "the book title", "chapters": [{"title": "chapter title", '
        '"summary": "one sentence on what happens in this chapter", "pages": 8}]}'
    )
    if firmer:
        user += (
            "\n\nYour last answer could not be parsed. Output starts with { and ends with }. "
            "No markdown, no code fence, no explanation, no trailing comma. "
            'Every chapter object has exactly the keys "title", "summary" and "pages".'
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _strip_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = _FENCE.sub("", text).strip()
    return text


def _require_text(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OutlineError(f"{what} is missing or is not a non empty string.")
    return " ".join(value.split())


def parse(raw: str, pages: int, given_title: str = "") -> Outline:
    """Parse the outline reply strictly. Raise OutlineError on anything else."""
    text = _strip_fence(raw)
    if not text:
        raise OutlineError("The reply was empty.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise OutlineError(f"The reply was not JSON: {error.msg} at position {error.pos}.") from None
    if not isinstance(payload, dict):
        raise OutlineError("The reply was not a JSON object.")

    title = given_title.strip() or _require_text(payload.get("title"), "title")

    raw_chapters = payload.get("chapters")
    if not isinstance(raw_chapters, list) or not raw_chapters:
        raise OutlineError("chapters is missing or is not a non empty list.")
    if len(raw_chapters) > pages:
        raise OutlineError(
            f"The reply has {len(raw_chapters)} chapters for {pages} pages, "
            "so at least one chapter would have no page."
        )

    chapters: list[Chapter] = []
    for position, item in enumerate(raw_chapters, start=1):
        if not isinstance(item, dict):
            raise OutlineError(f"Chapter {position} is not a JSON object.")
        chapter_title = _require_text(item.get("title"), f"Chapter {position} title")
        summary = _require_text(item.get("summary"), f"Chapter {position} summary")[:MAX_SUMMARY_CHARS]
        count = item.get("pages")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise OutlineError(f"Chapter {position} pages is not a whole number of at least 1.")
        chapters.append(Chapter(number=position, title=chapter_title, summary=summary, pages=count))

    _fit_pages(chapters, pages)
    return Outline(title=title, chapters=chapters)


def _fit_pages(chapters: list[Chapter], pages: int) -> None:
    """Scale the chapter page counts so they add up to the requested total.

    The shape came from the model. This is arithmetic on the numbers it gave, keeping
    their proportions, so the book is exactly the length the reader asked for.
    """
    total = sum(chapter.pages for chapter in chapters)
    if total != pages:
        shares = [chapter.pages / total * pages for chapter in chapters]
        floors = [max(1, int(share)) for share in shares]
        while sum(floors) > pages:
            index = max(range(len(floors)), key=lambda i: floors[i])
            if floors[index] == 1:
                break
            floors[index] -= 1
        remainders = sorted(
            range(len(shares)), key=lambda i: shares[i] - int(shares[i]), reverse=True
        )
        spare = pages - sum(floors)
        position = 0
        while spare > 0 and remainders:
            floors[remainders[position % len(remainders)]] += 1
            spare -= 1
            position += 1
        for chapter, count in zip(chapters, floors):
            chapter.pages = count
    page = 1
    for chapter in chapters:
        chapter.first_page = page
        page += chapter.pages
