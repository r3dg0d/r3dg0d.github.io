#!/usr/bin/env python3
"""Sanity checks for the static site. Standard library only.

  python3 scripts/check_site.py            # structure + metadata + anchors
  python3 scripts/check_site.py --links    # also fetch every external link (network)
  python3 scripts/check_site.py --readme PATH   # also check the profile repo's README.md
                                                # (banned references, featured-project parity)
"""

from __future__ import annotations

import datetime
import json
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_projects  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VOID = {"meta", "link", "br", "img", "input", "hr", "source", "area", "base", "col", "embed", "wbr"}

# Names and phrases that must not reappear anywhere in the site or the profile README.
# Plain "C++" stays legal (blurcam really is C++); only personal-preference claims are banned.
BANNED = {
    "deleted repo MatrixShot": r"matrix[-_ ]?shot",
    "deleted repo vanillaamericamc": r"vanilla[-_ ]?america(?:n)?[-_ ]?mc",
    "deleted repo matrix-sddm-theme": r"matrix[-_ ]sddm[-_ ]theme",
    "retired GitHub org business-forge": r"business[-_ ]?forge",
    "C++ preference claim": r"(?:favou?rite\s+(?:programming\s+)?language|mostly\s+c\+\+|primarily\s+a\s+c\+\+|c\+\+\s+(?:is\s+)?(?:old\s+and\s+proven|my\s+favou?rite)|c\+\+\s*[—-]+\s*favou?rite)",
    "old standalone xAI branding": r"\bxAI\b",
}
OWNER = "r3dg0d"
ALLOWED_HOSTS = {"github.com", "www.eff.org", "r3dg0d.github.io", "github-readme-stats.vercel.app", "schema.org"}
TOOLS = ["Claude Code", "ChatGPT Codex", "Gemini", "SpaceXSI Grok Bot", "Cursor"]
TEXT_FILES = ["index.html", "README.md", "data/projects.json", "sitemap.xml", "robots.txt"]


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
        self.headings: list[int] = []
        self.imgs: list[dict] = []
        self.jsonld: list[str] = []
        self._in_ld = False

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
        if len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self.headings.append(int(tag[1]))
        if tag == "img":
            self.imgs.append(a)
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.jsonld.append("")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_ld = False
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"mismatched </{tag}> (open: {self.stack[-3:]})")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self.jsonld[-1] += data


def check_links(hrefs: list[str]) -> list[str]:
    problems = []
    for url in sorted({h for h in hrefs if h.startswith("http")}):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "site-check"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status >= 400:
                    problems.append(f"{r.status} {url}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 405, 501):  # some hosts reject HEAD; retry with GET
                try:
                    urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "site-check"}), timeout=20).close()
                    continue
                except OSError as e2:
                    problems.append(f"{getattr(e2, 'code', 'unreachable')} {url}")
                    continue
            problems.append(f"{e.code} {url}")
        except OSError as e:
            problems.append(f"unreachable {url} ({e})")
    return problems


def png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def check_banned(label: str, text: str) -> list[str]:
    return [f"{label}: {why} ({m.group(0)!r})" for why, pat in BANNED.items() for m in re.finditer(pat, text, re.I)]


def check_metadata(page: Page) -> list[str]:
    p: list[str] = []
    m = page.meta
    for a, b in (("og:title", "twitter:title"), ("og:description", "twitter:description"),
                 ("og:image", "twitter:image"), ("og:image:alt", "twitter:image:alt"),
                 ("og:title", None), ("og:description", "description")):
        if b is None:
            if m.get(a, "").strip() != page.title.strip():
                p.append("og:title differs from <title>")
        elif m.get(a) != m.get(b):
            p.append(f"{a} and {b} differ")
    if m.get("og:url") != page.links.get("canonical"):
        p.append("og:url differs from canonical")
    for k in ("og:image:alt", "twitter:image:alt"):
        if not m.get(k):
            p.append(f"missing {k}")
    if len(m.get("description", "")) > 200:
        p.append("description longer than 200 characters")
    img = m.get("og:image", "")
    mm = re.match(r"https://r3dg0d\.github\.io/([^?#]+)", img)
    if not mm or not (ROOT / mm.group(1)).is_file():
        p.append(f"og:image {img!r} does not point at a file in this repo")
    else:
        size = png_size(ROOT / mm.group(1))
        want = (int(m.get("og:image:width", 0)), int(m.get("og:image:height", 0)))
        if size != want or size != (1200, 630):
            p.append(f"og-image is {size}, meta says {want}, expected (1200, 630)")
    for loc in (page.links.get("icon"), page.links.get("apple-touch-icon")):
        if loc and not (ROOT / loc.lstrip("/")).is_file():
            p.append(f"missing file for <link href={loc}>")
    # structured data
    if not page.jsonld:
        p.append("no JSON-LD block")
    for blob in page.jsonld:
        try:
            ld = json.loads(blob)
        except ValueError as e:
            p.append(f"JSON-LD does not parse: {e}")
            continue
        nodes = ld.get("@graph", [ld])
        person = [n for n in nodes if n.get("@type") == "Person"]
        site = [n for n in nodes if n.get("@type") == "WebSite"]
        if not person or f"https://github.com/{OWNER}" not in person[0].get("sameAs", []):
            p.append("JSON-LD Person missing or sameAs lacks the GitHub profile")
        if not site or site[0].get("description") != m.get("description"):
            p.append("JSON-LD WebSite description differs from meta description")
    return p


def check_a11y(page: Page) -> list[str]:
    p: list[str] = []
    prev = 0
    for h in page.headings:
        if prev and h > prev + 1:
            p.append(f"heading level jumps from h{prev} to h{h}")
        prev = h
    for im in page.imgs:
        if not im.get("width") or not im.get("height"):
            p.append(f"<img {im.get('src', '')[:40]}...> needs width and height (layout shift)")
    return p


def check_links_policy(hrefs: list[str]) -> list[str]:
    p = []
    for h in hrefs:
        if not h.startswith("http"):
            continue
        u = urllib.parse.urlparse(h)
        if u.netloc not in ALLOWED_HOSTS:
            p.append(f"unexpected external host in link: {h}")
        elif u.netloc == "github.com" and not (u.path == f"/{OWNER}" or u.path.startswith(f"/{OWNER}/")):
            p.append(f"GitHub link outside the personal account: {h}")
    return p


def check_projects(text: str) -> list[str]:
    p: list[str] = []
    d = sync_projects.load()
    if d.get("owner") != OWNER:
        p.append(f"projects.json owner is {d.get('owner')!r}, expected {OWNER!r}")
    names = [x["name"] for x in d["featured"]]
    if not 5 <= len(names) <= 6:
        p.append(f"expected 5-6 featured projects, found {len(names)}")
    old, new = sync_projects.render(ROOT / "index.html", {"projects": sync_projects.cards_html(d), "more": sync_projects.more_html(d)})
    if old != new:
        p.append("index.html project cards are out of date: run python3 scripts/sync_projects.py")
    for t in TOOLS:
        if t not in text:
            p.append(f"index.html does not mention {t}")
    return p


def check_readme(path: Path) -> list[str]:
    p: list[str] = []
    if not path.is_file():
        return [f"profile README not found: {path}"]
    text = path.read_text(encoding="utf-8")
    p += check_banned(str(path), text)
    d = sync_projects.load()
    known = {x["name"] for x in d["featured"]} | {x["name"] for x in d["more"]} | {"r3dg0d.github.io", OWNER}
    for x in d["featured"]:
        if f"https://github.com/{OWNER}/{x['name']}" not in text:
            p.append(f"README is missing featured project {x['name']}")
    for repo in re.findall(rf"github\.com/{OWNER}/([A-Za-z0-9_.-]+)", text):
        if repo not in known:
            p.append(f"README links to a repo that is not in data/projects.json: {repo}")
    for needle in TOOLS + ["https://www.eff.org", "https://r3dg0d.github.io"]:
        if needle not in text:
            p.append(f"README does not mention {needle}")
    old, new = sync_projects.render(path, {"projects": sync_projects.readme_md(d)}, md=True)
    if old != new:
        p.append("README featured projects are out of date: run sync_projects.py --readme PATH")
    return p


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

    problems += check_metadata(page) + check_a11y(page) + check_links_policy(page.hrefs) + check_projects(text)
    for name in TEXT_FILES:
        f = ROOT / name
        if f.is_file():
            problems += check_banned(name, f.read_text(encoding="utf-8"))
    if "--readme" in sys.argv:
        problems += check_readme(Path(sys.argv[sys.argv.index("--readme") + 1]))

    if "--links" in sys.argv:
        problems += check_links(page.hrefs)

    for p in problems:
        print("FAIL", p)
    if not problems:
        print(f"ok: {len(page.hrefs)} links, {len(page.ids)} ids" + (", links fetched" if "--links" in sys.argv else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
