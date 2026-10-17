# r3dg0d.github.io

Personal site for [r3dg0d](https://r3dg0d.github.io) — purple-nebula theme matching my
[GitHub profile](https://github.com/r3dg0d): super-intelligence & FOSS, NixOS, C++,
PS5 homebrew / game modding, privacy (EFF), five featured projects, and live GitHub stats.

Static `index.html` at the repo root. `.nojekyll` disables Jekyll; no build step required.
Stats are image embeds from github-readme-stats (GitHub itself blocks iframing, so buttons link there).

MIT — see [LICENSE](LICENSE).

## Checks

`python3 scripts/check_site.py` validates structure, landmarks, metadata (title, description,
Open Graph, canonical, favicon) and in-page anchors; add `--links` to fetch every external link.
