# r3dg0d.github.io

Personal site for [r3dg0d](https://r3dg0d.github.io) — about, workstation specs, and public projects.

Static `index.html` at the repo root. `.nojekyll` disables Jekyll; no build step required.

MIT — see [LICENSE](LICENSE).

## Checks

`python3 scripts/check_site.py` validates structure, landmarks, metadata (title, description,
Open Graph, canonical, favicon) and in-page anchors; add `--links` to fetch every external
link. CI runs both on every push and weekly, so a renamed or deleted project repo shows up
as a failing check instead of a dead link.
