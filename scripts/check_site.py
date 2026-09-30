#!/usr/bin/env python3
"""Sanity checks for the static site. Standard library only.

  python3 scripts/check_site.py            # structure + metadata + anchors
  python3 scripts/check_site.py --links    # also fetch every external link (network)
"""

from __future__ import annotations

import datetime
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"meta", "link", "br", "img", "input", "hr", "source", "area", "base", "col", "embed", "wbr"}


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.tags: dict[str, int] = {}
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.lang = ""
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if tag == "html":
            self.lang = a.get("lang", "")
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        if tag == "link" and a.get("rel"):
            self.links[a["rel"]] = a.get("href", "")
        if tag == "title":
            self._in_title = True
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"mismatched </{tag}> (open: {self.stack[-3:]})")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def check_links(hrefs: list[str]) -> list[str]:
    problems = []
    for url in sorted({h for h in hrefs if h.startswith("http")}):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "site-check"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status >= 400:
                    problems.append(f"{r.status} {url}")
        except urllib.error.HTTPError as e:
            problems.append(f"{e.code} {url}")
        except OSError as e:
            problems.append(f"unreachable {url} ({e})")
    return problems


def main() -> int:
    page = Page()
    page.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    problems = list(page.errors) + [f"unclosed <{t}>" for t in page.stack]

    if not page.lang:
        problems.append("<html> has no lang attribute")
    if not page.title.strip() or page.title.strip().lower() == "r3dg0d":
        problems.append("title is missing or too generic")
    for key in ("description", "viewport", "og:title", "og:description", "og:url", "twitter:card"):
        if not page.meta.get(key):
            problems.append(f"missing <meta {key}>")
    for rel in ("canonical", "icon"):
        if rel not in page.links:
            problems.append(f'missing <link rel="{rel}">')
    if page.tags.get("h1") != 1:
        problems.append(f"expected exactly one <h1>, found {page.tags.get('h1', 0)}")
    for landmark in ("header", "main", "footer", "nav"):
        if page.tags.get(landmark) != 1:
            problems.append(f"expected exactly one <{landmark}>, found {page.tags.get(landmark, 0)}")
    for href in page.hrefs:
        if href.startswith("#") and href[1:] not in page.ids:
            problems.append(f"anchor {href} has no matching id")
    text = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r'\sstyle="', text):
        problems.append("inline style attributes found (use a class)")
    if re.search(r"<img\b(?![^>]*\balt=)", text):
        problems.append("<img> without alt")

    m = re.search(r'id="age"\s+data-birthday="(\d{4})-(\d{2})-(\d{2})">(\d+)<', text)
    if not m:
        problems.append("age element with data-birthday not found")
    else:
        by, bm, bd, shown = (int(x) for x in m.groups())
        today = datetime.date.today()
        expected = today.year - by - ((today.month, today.day) < (bm, bd))
        if shown != expected:
            problems.append(f"no-JS age fallback says {shown} but the age is {expected}; update index.html")

    if "--links" in sys.argv:
        problems += check_links(page.hrefs)

    for p in problems:
        print("FAIL", p)
    if not problems:
        print(f"ok: {len(page.hrefs)} links, {len(page.ids)} ids" + (", links fetched" if "--links" in sys.argv else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
