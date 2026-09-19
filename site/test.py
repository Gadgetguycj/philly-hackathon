#!/usr/bin/env python3
"""Check a running container against GUIDE.md.

  python3 site/test.py [base-url]        default http://127.0.0.1:8080

Three things matter and are checked here. The page serves. Every fenced code
block, the step 5 paste block above all, is present character for character.
No repository-relative link survives in the output.
"""

import html
import os
import re
import subprocess
import sys

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.join(os.path.dirname(SITE_DIR), "GUIDE.md")
BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8080"

FENCE = re.compile(r"^```[^\n]*\n(.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE)
CODE_BLOCK = re.compile(r"<pre><code[^>]*>(.*?)</code></pre>", re.DOTALL)
ATTR = re.compile(r'(?:href|src)="([^"]*)"')
HAS_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("{} {}{}".format("PASS" if ok else "FAIL", name, "  " + detail if detail else ""))


def curl(path, *extra):
    command = ["curl", "-sS", "-o", "-", "-w", "\\n%{http_code}", BASE + path]
    command.extend(extra)
    out = subprocess.run(command, capture_output=True, text=True, check=False).stdout
    body, _, status = out.rpartition("\n")
    return status.strip(), body


def guide_fences(source):
    return [match.group(1) for match in FENCE.finditer(source)]


def step5_fence(source):
    head = re.search(r"^### 5\..*$", source, re.MULTILINE)
    if not head:
        raise SystemExit("no step 5 heading in GUIDE.md")
    match = FENCE.search(source, head.end())
    if not match:
        raise SystemExit("no fenced block after the step 5 heading")
    return match.group(1)


def main():
    with open(GUIDE, encoding="utf-8") as handle:
        source = handle.read()

    # 1. The page serves.
    status, page = curl("/")
    check("page serves 200", status == "200", "status " + status)
    check("page has content", len(page) > 10000, "{} bytes".format(len(page)))
    heading = re.search(r"<h1[^>]*>([^<]+)", page)
    check("page carries the guide heading", bool(heading),
          heading.group(1) if heading else "no h1")

    status, health = curl("/health")
    check("/health returns 200", status == "200" and health.strip() == "ok",
          "status {} body {!r}".format(status, health.strip()))

    # 2. Every fenced block survives verbatim, step 5 named on its own.
    served = [html.unescape(body) for body in CODE_BLOCK.findall(page)]
    fences = guide_fences(source)
    check("code block count matches the guide",
          len(served) == len(fences),
          "{} served, {} in GUIDE.md".format(len(served), len(fences)))
    missing = [text[:40] for text in fences if text not in served]
    check("every fenced block is verbatim", not missing, "missing " + repr(missing))

    step5 = step5_fence(source)
    exact = [text for text in served if text == step5]
    check("step 5 paste block is character for character identical",
          len(exact) == 1,
          "{} of {} chars matched".format(len(step5) if exact else 0, len(step5)))

    blocks = len(re.findall(r'<div class="code">', page))
    buttons = len(re.findall(r'<button class="copy"', page))
    check("a copy button on every code block",
          blocks == buttons == len(fences),
          "{} blocks, {} buttons".format(blocks, buttons))

    # 3. No repository-relative link survives.
    relative = [
        value for value in ATTR.findall(page)
        if value and not value.startswith("#") and not value.startswith("//")
        and not HAS_SCHEME.match(value)
    ]
    check("no relative link or image in the output", not relative, repr(relative[:5]))

    # Proof the rewriter works, on a fixture the guide does not currently cover.
    selftest = subprocess.run(
        [sys.executable, os.path.join(SITE_DIR, "build.py"), "--selftest"],
        capture_output=True, text=True, check=False,
    )
    check("relative link rewriter selftest", selftest.returncode == 0,
          selftest.stdout.strip() or selftest.stderr.strip())

    # Typography, because these get pasted into a terminal.
    bad = {"—": "em dash", "–": "en dash", "‘": "left quote",
           "’": "right quote", "“": "left double quote",
           "”": "right double quote", "…": "ellipsis"}
    hits = sorted({name for char, name in bad.items() if char in page})
    check("no smart quotes or dashes in the served bytes", not hits, repr(hits))

    # No external resource: everything the browser must fetch is in this file.
    fetched = re.findall(r'<script[^>]*\ssrc="([^"]*)"', page)
    fetched += re.findall(r'<link[^>]*\srel="stylesheet"[^>]*>', page)
    fetched += re.findall(r'<img[^>]*\ssrc="([^"]*)"', page)
    fetched += re.findall(r"@import[^;]*;", page)
    fetched += re.findall(r"url\(\s*['\"]?https?:", page)
    check("nothing is fetched from outside the page", not fetched, repr(fetched[:5]))

    failed = [name for name, ok, _ in results if not ok]
    print("\n{} checks, {} failed".format(len(results), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
