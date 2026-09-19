"""The per page request. One page of prose at a time, with a small rolling context."""

from .outline import Chapter, Outline

WORDS_LOW = 220
WORDS_HIGH = 260
# A page is about 400 tokens of prose. The budget is far above that because a reasoning
# model spends tokens thinking before it writes, and a page that runs out of budget
# mid sentence is worse than one that finishes early.
MAX_TOKENS = 1600
# The rolling context is the tail of the last page plus a shorter tail of the page before
# it. The 256K context of the default endpoint could hold the whole book, but a small
# prompt is a fast prompt, and speed is the point of this demo.
PREVIOUS_TAIL_CHARS = 900
OLDER_TAIL_CHARS = 350

SYSTEM = (
    "You write books one page at a time. A page is a continuous piece of prose. "
    f"Write between {WORDS_LOW} and {WORDS_HIGH} words. "
    "Never write a heading, a chapter number, a page number, a title, a list or a note to the reader. "
    "Never say what you are about to do. Start writing the page immediately and stop when it is full. "
    "It is fine to end a page in the middle of a scene, because the next page carries on."
)


def _tail(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[-limit:]
    space = cut.find(" ")
    return cut[space + 1 :] if 0 <= space < 120 else cut


def rolling_context(previous: str, older: str) -> str:
    """The recap sent with the next page, built from the tails of the last two pages."""
    parts = []
    if older:
        parts.append("Earlier on the page before last:\n" + _tail(older, OLDER_TAIL_CHARS))
    if previous:
        parts.append("The page you are continuing from ended like this:\n" + _tail(previous, PREVIOUS_TAIL_CHARS))
    return "\n\n".join(parts)


def messages(
    outline: Outline,
    chapter: Chapter,
    page: int,
    idea: str,
    recap: str,
    previous_chapter: Chapter | None,
) -> list[dict]:
    page_in_chapter = page - chapter.first_page + 1
    lines = [
        f'Book title: "{outline.title}".',
        f"The reader asked for a book about: {idea}",
        "",
        "Chapters:",
        outline.compact_lines(),
        "",
        f"You are writing page {page} of {outline.total_pages}.",
        f'It is page {page_in_chapter} of {chapter.pages} in chapter {chapter.number}, "{chapter.title}".',
        f"This chapter covers: {chapter.summary}",
    ]
    if recap:
        lines += ["", recap]
    elif previous_chapter is not None:
        lines += [
            "",
            f'The previous chapter, "{previous_chapter.title}", covered: {previous_chapter.summary}',
            "Open this chapter in a new moment. Do not recap what the reader has already read.",
        ]
    else:
        lines += ["", "This is the first page of the book. Open the story."]
    if page == chapter.last_page and chapter.number == len(outline.chapters):
        lines += ["", "This is the last page of the book. Bring the story to an end."]
    elif page == chapter.last_page:
        lines += ["", "This is the last page of the chapter. Close this part of the story."]
    lines += ["", f"Write page {page} now. Prose only, {WORDS_LOW} to {WORDS_HIGH} words."]
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "\n".join(lines)},
    ]


def word_count(text: str) -> int:
    return len(text.split())
