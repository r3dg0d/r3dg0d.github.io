#!/usr/bin/env python3
"""Render data/projects.json into index.html (and optionally a profile README).

  python3 scripts/sync_projects.py                    # rewrite the generated block in index.html
  python3 scripts/sync_projects.py --check            # exit 1 if index.html is out of date
  python3 scripts/sync_projects.py --readme PATH      # also rewrite the block in a profile README.md
  python3 scripts/sync_projects.py --check --readme PATH

Generated regions sit between "projects:start/end" and "more:start/end" markers
(HTML comments), so everything else in those files stays hand-written.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "projects.json"


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def url(owner: str, name: str) -> str:
    return f"https://github.com/{owner}/{name}"


def cards_html(d: dict) -> str:
    out = []
    for p in d["featured"]:
        tags = "".join(f"<li>{html.escape(t)}</li>" for t in p["tags"])
        out.append(
            "            <li class=\"card\">\n"
            f"              <p class=\"cat\">{html.escape(p['category'])}</p>\n"
            f"              <h3><a class=\"name\" href=\"{url(d['owner'], p['name'])}\">{html.escape(p['name'])}"
            "<span class=\"visually-hidden\"> on GitHub</span></a></h3>\n"
            f"              <p class=\"desc\">{html.escape(p['description'])}</p>\n"
            f"              <ul class=\"tags\" aria-label=\"Technologies\">{tags}</ul>\n"
            "            </li>"
        )
    return "\n".join(out)


def more_html(d: dict) -> str:
    items = [
        f"<li><a href=\"{url(d['owner'], p['name'])}\">{html.escape(p['name'])}</a>"
        f"<span> — {html.escape(p['description'])}</span></li>"
        for p in d["more"]
    ]
    return "\n".join("            " + i for i in items)


def readme_md(d: dict) -> str:
    lines = []
    for p in d["featured"]:
        tags = " · ".join(p["tags"])
        lines.append(f"- [**{p['name']}**]({url(d['owner'], p['name'])}) — {p['description']} <sub>{tags}</sub>")
    return "\n".join(lines)


def splice(text: str, key: str, body: str, md: bool = False) -> str:
    start, end = f"<!-- {key}:start -->", f"<!-- {key}:end -->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        raise SystemExit(f"marker {start} not found")
    return pat.sub(lambda _m: f"{start}\n{body}\n{'' if md else '          '}{end}", text, count=1)


def render(path: Path, regions: dict[str, str], md: bool = False) -> tuple[str, str]:
    old = path.read_text(encoding="utf-8")
    new = old
    for key, body in regions.items():
        new = splice(new, key, body, md)
    return old, new


def main(argv: list[str]) -> int:
    check = "--check" in argv
    d = load()
    jobs = [(ROOT / "index.html", {"projects": cards_html(d), "more": more_html(d)}, False)]
    if "--readme" in argv:
        jobs.append((Path(argv[argv.index("--readme") + 1]), {"projects": readme_md(d)}, True))
    stale = False
    for path, regions, md in jobs:
        old, new = render(path, regions, md)
        if old != new:
            if check:
                print(f"STALE {path}: run python3 scripts/sync_projects.py" + (" --readme ..." if md else ""))
                stale = True
            else:
                path.write_text(new, encoding="utf-8")
                print(f"updated {path}")
        elif not check:
            print(f"unchanged {path}")
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
