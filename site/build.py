#!/usr/bin/env python3
"""Render GUIDE.md into site/dist/index.html.

The guide is the only source of prose. Everything here is layout: a copy button
on every fenced code block, a table of contents from the headings, absolute
GitHub URLs in place of repository-relative links, and one self contained HTML
file with the stylesheet and script inlined so the page needs no network.
"""

import argparse
import html
import os
import re
import sys
from xml.etree.ElementTree import Element

import markdown
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SITE_DIR)
GUIDE = os.path.join(REPO_DIR, "GUIDE.md")
OUT_DIR = os.path.join(SITE_DIR, "dist")

REPO_URL = "https://github.com/Gadgetguycj/philly-hackathon"
DECK_URL = "https://gadgetguycj.github.io/philly-hackathon/"
SITE_URL = "https://runpodtrack.galaxygate.app"

# Text inside these tags is copied into a terminal, so it is never touched.
SKIP_TAGS = {"code", "pre", "a", "script", "style"}
BARE_URL = re.compile(r"https?://[^\s<>()\[\]\"']+")
TRAILING = ".,;:!?"
HAS_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _tokenize(text):
    """Split text into a leading string plus <a> elements holding the rest."""
    if not text or "http" not in text:
        return text, []
    # Each match becomes a link; the text after it rides on that link's tail.
    leading = None
    links = []
    pos = 0
    for match in BARE_URL.finditer(text):
        url = match.group(0).rstrip(TRAILING)
        segment = text[pos:match.start()]
        if leading is None:
            leading = segment
        else:
            links[-1].tail = segment
        link = Element("a")
        link.set("href", url)
        link.text = url
        link.tail = ""
        links.append(link)
        pos = match.start() + len(url)
    if not links:
        return text, []
    links[-1].tail = text[pos:]
    return leading, links


class Linkify(Treeprocessor):
    """Turn bare http(s) URLs in prose into links. Skips code and links."""

    def run(self, root):
        self._walk(root)

    def _walk(self, element):
        if element.tag in SKIP_TAGS:
            return
        children = []
        element.text, found = _tokenize(element.text)
        children.extend(found)
        for child in list(element):
            self._walk(child)
            child.tail, found = _tokenize(child.tail)
            children.append(child)
            children.extend(found)
        for child in list(element):
            element.remove(child)
        for child in children:
            element.append(child)


class AbsoluteLinks(Treeprocessor):
    """Rewrite repository-relative links and images to absolute GitHub URLs."""

    def run(self, root):
        for element in root.iter():
            for attribute in ("href", "src"):
                value = element.get(attribute)
                if value is None:
                    continue
                fixed = absolute_url(value)
                if fixed != value:
                    element.set(attribute, fixed)


def absolute_url(value):
    """Map a repository path to its GitHub URL. Absolute values pass through.

    A last segment with a file extension is a file and gets a blob URL,
    anything else is a folder and gets a tree URL. The rule reads only the
    string, so the container build and a host build agree.
    """
    if not value or value.startswith("#") or value.startswith("//"):
        return value
    if HAS_SCHEME.match(value):
        return value
    path, sep, suffix = value.partition("#")
    if not sep:
        path, sep, suffix = value.partition("?")
    path = re.sub(r"^\./", "", path).lstrip("/")
    if not path:
        return value
    kind = "blob" if re.search(r"\.[A-Za-z0-9]{1,8}$", path) else "tree"
    return "{}/{}/main/{}{}{}".format(REPO_URL, kind, path, sep, suffix)


CODE_BLOCK = re.compile(
    r'<pre><code(?P<attrs>[^>]*)>(?P<body>.*?)</code></pre>', re.DOTALL
)


class CopyableCode(Postprocessor):
    """Wrap every code block in a bar carrying its language and a copy button.

    A postprocessor, because fenced blocks are held out of the element tree
    until the raw HTML is substituted back at the end of the run.
    """

    def run(self, text):
        def wrap(match):
            attrs = match.group("attrs")
            language = re.search(r'class="language-([^"]+)"', attrs)
            return (
                '<div class="code">'
                '<div class="code-bar">'
                '<span class="code-lang">{lang}</span>'
                '<button class="copy" type="button">Copy</button>'
                "</div>"
                "<pre><code{attrs}>{body}</code></pre>"
                "</div>"
            ).format(
                lang=html.escape(language.group(1)) if language else "text",
                attrs=attrs,
                body=match.group("body"),
            )

        return CODE_BLOCK.sub(wrap, text)


H2 = re.compile(r"<h2\b[^>]*>(?P<inner>.*?)</h2>", re.DOTALL)
H2_ID = re.compile(r'id="([^"]+)"')
TOOL_HEADING = "Using "


class ToolDropdowns(Postprocessor):
    """Wrap each "Using <tool>" section in a closed details element.

    Runs after the code blocks are back in the text, so a section carries its
    own copy blocks. The heading keeps its id, so a contents link still lands
    on it; app.js opens the section that link points into.
    """

    def run(self, text):
        heads = list(H2.finditer(text))
        pieces = []
        cursor = 0
        for index, head in enumerate(heads):
            inner = re.sub(
                r'<a class="headerlink".*?</a>', "", head.group("inner"), flags=re.DOTALL
            )
            label = re.sub(r"<[^>]+>", "", inner).strip()
            if not label.startswith(TOOL_HEADING):
                continue
            end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
            anchor = H2_ID.search(head.group(0))
            pieces.append(text[cursor:head.start()])
            pieces.append(
                '<details class="tool">\n'
                '<summary><h2 id="{id}">{label}</h2></summary>\n'
                '<div class="tool-body">\n{body}\n</div>\n'
                "</details>\n".format(
                    id=anchor.group(1) if anchor else "",
                    label=html.escape(label),
                    body=text[head.end():end].strip(),
                )
            )
            cursor = end
        pieces.append(text[cursor:])
        return "".join(pieces)


class GuideExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(Linkify(md), "guide_linkify", 8)
        md.treeprocessors.register(AbsoluteLinks(md), "guide_absolute", 7)
        md.postprocessors.register(CopyableCode(md), "guide_code", 10)
        md.postprocessors.register(ToolDropdowns(md), "guide_tools", 5)


def render(source):
    """Return the guide as HTML plus its heading tree."""
    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "sane_lists",
            "toc",
            GuideExtension(),
        ],
        extension_configs={
            "toc": {"permalink": "#", "toc_depth": "2-3"},
        },
    )
    body = md.convert(source)
    return body, md.toc_tokens


def table_of_contents(tokens):
    """Nested list markup for the contents panel."""
    if not tokens:
        return ""
    items = []
    for token in tokens:
        inner = table_of_contents(token["children"])
        items.append(
            '<li><a href="#{}">{}</a>{}</li>'.format(
                token["id"], html.escape(token["name"]), inner
            )
        )
    return "<ul>{}</ul>".format("".join(items))


def page_title(body):
    match = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.DOTALL)
    if not match:
        return "Hackathon guide"
    inner = re.sub(r'<a class="headerlink".*?</a>', "", match.group(1), flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", inner)
    return html.unescape(text).strip()


def build():
    with open(GUIDE, encoding="utf-8") as handle:
        source = handle.read()
    body, tokens = render(source)
    with open(os.path.join(SITE_DIR, "style.css"), encoding="utf-8") as handle:
        css = handle.read()
    with open(os.path.join(SITE_DIR, "app.js"), encoding="utf-8") as handle:
        js = handle.read()

    title = page_title(body)
    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="canonical" href="{site}">
<style>
{css}
</style>
</head>
<body>
<header class="top">
<details class="toc" id="toc">
<summary>Contents</summary>
<nav aria-label="Contents">
{toc}
</nav>
</details>
</header>
<main id="guide">
{body}
</main>
<footer class="foot">
<a href="{repo}">Repository</a>
<a href="{deck}">Slide deck</a>
</footer>
<script>
{js}
</script>
</body>
</html>
""".format(
        title=html.escape(title),
        site=SITE_URL,
        css=css.strip(),
        toc=table_of_contents(tokens),
        body=body,
        repo=REPO_URL,
        deck=DECK_URL,
        js=js.strip(),
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(page)
    print("wrote {} ({} bytes)".format(out, len(page.encode("utf-8"))))
    return out


FIXTURE = """# Fixture

A link to [the demo](demos/sketch) and to [the agent file](AGENT.md#step-12),
a [dotted path](./qr/guide.png), an [anchor](#fixture), an
[absolute link](https://runpod.galaxygate.app) and ![an image](slides/deck.pdf).
"""


def selftest():
    """Prove the relative link rewriter on a fixture the guide does not cover."""
    body, _ = render(FIXTURE)
    expected = [
        REPO_URL + "/tree/main/demos/sketch",
        REPO_URL + "/blob/main/AGENT.md#step-12",
        REPO_URL + "/blob/main/qr/guide.png",
        "#fixture",
        "https://runpod.galaxygate.app",
        REPO_URL + "/blob/main/slides/deck.pdf",
    ]
    found = re.findall(r'(?:href|src)="([^"]+)"', body)
    found = [value for value in found if not value.startswith("#fixture-")]
    missing = [value for value in expected if value not in found]
    if missing:
        print("selftest FAIL, missing: {}".format(missing), file=sys.stderr)
        print("found: {}".format(found), file=sys.stderr)
        return 1
    print("selftest pass, rewrote {} links and images".format(len(expected)))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    build()
