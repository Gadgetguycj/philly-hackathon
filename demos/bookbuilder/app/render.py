"""Server rendered HTML for the read only pages."""

from html import escape

from .store import Book

HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="/static/style.css">
</head><body class="reader">
"""
FOOT = "</body></html>\n"


def _paragraphs(text: str) -> str:
    blocks = [block.strip() for block in text.split("\n\n")]
    return "".join(f"<p>{escape(block)}</p>" for block in blocks if block)


def book_page(book: Book) -> str:
    meta = book.meta
    outline = book.outline
    title = str(outline.get("title") or meta.get("title") or "Bookbuilder")
    parts = [HEAD.format(title=escape(title) + " | Bookbuilder")]
    parts.append('<header class="bar"><a class="home" href="/">Bookbuilder</a>')
    parts.append(f'<span class="crumb">{escape(title)}</span>')
    parts.append(f'<a class="ghost" href="/b/{book.id}/book.md">Markdown</a></header>')
    parts.append('<main class="sheet">')
    parts.append(f"<h1>{escape(title)}</h1>")
    facts = [
        f"{len(book.pages)} pages",
        f"{meta.get('words', 0)} words",
        f"written in {meta.get('seconds', 0)} seconds",
        f"{meta.get('words_per_second', 0)} words per second",
        escape(str(meta.get("model", ""))),
    ]
    parts.append('<p class="facts">' + " &middot; ".join(facts) + "</p>")
    if meta.get("idea"):
        parts.append(f'<p class="idea">The idea: {escape(str(meta["idea"]))}</p>')
    if meta.get("stopped"):
        parts.append('<p class="notice">This run was stopped early. These are the pages that finished.</p>')

    chapters = outline.get("chapters") or []
    parts.append('<nav class="toc"><h2>Contents</h2><ol>')
    for chapter in chapters:
        first = int(chapter.get("first_page", 1))
        if first > len(book.pages):
            continue
        last = min(int(chapter.get("last_page", first)), len(book.pages))
        parts.append(
            f'<li><a href="#p{first}">{escape(str(chapter.get("title", "")))}</a>'
            f'<span class="range">pages {first} to {last}</span></li>'
        )
    parts.append("</ol></nav>")

    starts = {int(c.get("first_page", 0)): c for c in chapters}
    for number, text in enumerate(book.pages, start=1):
        chapter = starts.get(number)
        if chapter is not None:
            parts.append(
                f'<h2 class="chapter">{chapter.get("number")}. {escape(str(chapter.get("title", "")))}</h2>'
            )
        parts.append(f'<article class="page" id="p{number}">')
        parts.append(f'<div class="page-no"><a href="#p{number}">Page {number}</a></div>')
        parts.append(_paragraphs(text))
        parts.append("</article>")
    parts.append('<p class="end"><a href="/books">Every book</a> &middot; <a href="/">Build another</a></p>')
    parts.append("</main>")
    parts.append(FOOT)
    return "".join(parts)


def books_page(books: list[dict]) -> str:
    parts = [HEAD.format(title="Books | Bookbuilder")]
    parts.append('<header class="bar"><a class="home" href="/">Bookbuilder</a>')
    parts.append('<span class="crumb">Recent books</span></header>')
    parts.append('<main class="sheet"><h1>Recent books</h1>')
    if not books:
        parts.append('<p class="idea">No book has been built yet. The first one is yours.</p>')
    else:
        parts.append('<ul class="booklist">')
        for meta in books:
            book_id = escape(str(meta.get("id", "")))
            title = escape(str(meta.get("title", "Untitled")))
            facts = (
                f"{meta.get('pages', 0)} pages &middot; {meta.get('words', 0)} words &middot; "
                f"{meta.get('words_per_second', 0)} words per second"
            )
            stopped = " &middot; stopped early" if meta.get("stopped") else ""
            parts.append(
                f'<li><a href="/b/{book_id}/">{title}</a>'
                f'<span class="range">{facts}{stopped}</span></li>'
            )
        parts.append("</ul>")
    parts.append('<p class="end"><a href="/">Build a book</a></p></main>')
    parts.append(FOOT)
    return "".join(parts)
