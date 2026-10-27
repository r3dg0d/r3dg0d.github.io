# r3dg0d.github.io

Personal site for [r3dg0d](https://r3dg0d.github.io): an open-source software creator who works SI-natively
(Claude Code, ChatGPT Codex, Gemini, SpaceXSI Grok Bot, Cursor), with NixOS, Linux, privacy (EFF),
game modding and PS5 homebrew. Purple-nebula theme matching the [GitHub profile](https://github.com/r3dg0d).

Static `index.html` at the repo root. `.nojekyll` disables Jekyll; no build step, no frameworks, no third-party scripts.
The GitHub stats card is an optional image from github-readme-stats that only loads when the visitor opens it.

## Layout

| Path | What |
|------|------|
| `index.html` | The whole site (inline CSS, small JS for the starfield; works without JS) |
| `data/projects.json` | Source of truth for the featured projects and the "Also on GitHub" list |
| `scripts/sync_projects.py` | Renders `projects.json` into `index.html` (and, with `--readme`, into the profile README) |
| `scripts/check_site.py` | Structure, metadata, accessibility and stale-reference checks |
| `scripts/og-image.html` | Source for `og-image.png` (render command is in the file) |

## Updating featured projects

1. Edit `data/projects.json` (verify the repo is public, not archived, and has a README).
2. `python3 scripts/sync_projects.py` for `index.html`.
3. `python3 scripts/sync_projects.py --readme ../r3dg0d/README.md` for the profile repo ([r3dg0d/r3dg0d](https://github.com/r3dg0d/r3dg0d)), then commit both.

## Checks

```sh
python3 scripts/check_site.py                              # structure, metadata, a11y, banned references
python3 scripts/check_site.py --links                      # also fetch every external link (network)
python3 scripts/check_site.py --readme ../r3dg0d/README.md # also check the profile README for parity
```

The checks fail on references to deleted projects, personal language-preference claims, non-personal GitHub
links, mismatched Open Graph / Twitter / JSON-LD metadata, a wrong-sized `og-image.png`, and stale project cards.
CI runs them on every push and weekly.

MIT — see [LICENSE](LICENSE).
