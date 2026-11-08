#!/usr/bin/env python3
"""Generate the profile's own SVGs from public GitHub data.

The Pac-Man contribution graph is rendered by its existing action. Its public
contribution cells are retained; motion is converted to small CSS-only SVGs.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.request


USER = "Zaywoo66"
MAX_RESPONSE = 1_000_000
MAX_SVG = 150_000
SMIL_ELEMENT = re.compile(r"<animate(?:Transform|Motion)?\b[\s\S]*?/>")
METADATA_ELEMENT = re.compile(r"<metadata>.*?</metadata>", re.DOTALL)


def pacman_css(width: int, height: int) -> str:
    """Animate only the existing Pac-Man sprite; leave contribution data intact."""
    if not 600 <= width <= 2000 or not 100 <= height <= 400:
        raise ValueError("unexpected Pac-Man canvas")
    right = width - 60
    lower = height - 55
    return f'''<style>
@keyframes pacman-travel {{
  0% {{ transform: translate(0px, 35px); }}
  46% {{ transform: translate({right}px, 35px); }}
  54% {{ transform: translate({right}px, {lower}px); }}
  100% {{ transform: translate(0px, {lower}px); }}
}}
#pacman {{ animation: pacman-travel 24s linear infinite alternate; }}
@media (prefers-reduced-motion: reduce) {{
  #pacman {{ animation: none; transform: translate(0px, 35px); }}
}}
</style>'''


def github_json(path: str) -> object:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Zaywoo66-profile-svg",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
               if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("GitHub response exceeds the bound")
    return json.loads(raw)


def public_stats(fetch=github_json) -> tuple[str, str]:
    """Return only complete, internally consistent public counts."""
    try:
        profile = fetch(f"/users/{USER}")
        if not isinstance(profile, dict) or profile.get("login") != USER:
            raise ValueError("unexpected profile")
        count = profile.get("public_repos")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("invalid public repository count")
        public_repos = str(count)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return "n/a", "n/a"

    try:
        # With more than one page, an incomplete list must not become a total.
        if count > 100:
            raise ValueError("repository list needs another page")
        repos = fetch(f"/users/{USER}/repos?type=owner&per_page=100")
        if not isinstance(repos, list) or len(repos) != count:
            raise ValueError("incomplete repository list")
        stars = 0
        for repo in repos:
            if not isinstance(repo, dict) or repo.get("owner", {}).get("login") != USER:
                raise ValueError("unexpected repository owner")
            value = repo.get("stargazers_count")
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("invalid star count")
            stars += value
        return public_repos, str(stars)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return public_repos, "n/a"


def header_svg() -> str:
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-labelledby="title desc">
<title id="title">Alikhan — full-stack developer</title>
<desc id="desc">A dark or light terminal-inspired header with Alikhan's name and Python/FastAPI and React/TypeScript focus.</desc>
<style>
svg { --bg:#0b1021; --panel:#121b31; --text:#f5f7ff; --muted:#b9c7df; --line:#42577d; --cyan:#76e4df; --pink:#ed97c7; --gold:#f3c789; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }
@media (prefers-color-scheme:light) { svg { --bg:#f5f7ff; --panel:#e9eef9; --text:#18223d; --muted:#415575; --line:#91a5c5; --cyan:#087f82; --pink:#ae397e; --gold:#9b5b11; } }
@keyframes travel { to { stroke-dashoffset:-84; } }
@keyframes breathe { 50% { opacity:.42; } }
.trace { animation:travel 10s linear infinite; }
.glow { animation:breathe 8s ease-in-out infinite; }
@media (prefers-reduced-motion:reduce) { .trace,.glow { animation:none; } }
</style>
<rect width="760" height="300" rx="22" fill="var(--bg)"/>
<rect x="18" y="18" width="724" height="264" rx="16" fill="var(--panel)" stroke="var(--line)"/>
<circle cx="53" cy="50" r="6" fill="var(--pink)"/><circle cx="74" cy="50" r="6" fill="var(--gold)"/><circle cx="95" cy="50" r="6" fill="var(--cyan)"/>
<path d="M22 76h716" stroke="var(--line)"/>
<text x="48" y="118" fill="var(--cyan)" font-size="20" letter-spacing="3">ASTANA / KAZAKHSTAN</text>
<text x="44" y="203" fill="var(--text)" font-size="86" font-weight="750">Alikhan.</text>
<text x="48" y="250" fill="var(--muted)" font-size="28">Full-stack: Python/FastAPI · React/TypeScript</text>
<path d="M581 108h124m-94 26h94m-67 26h67" stroke="var(--line)" stroke-width="3" stroke-linecap="round"/>
<path class="trace" d="M581 108h124m-94 26h94m-67 26h67" stroke="var(--pink)" stroke-width="3" stroke-linecap="round" stroke-dasharray="42 240"/>
<circle class="glow" cx="710" cy="50" r="5" fill="var(--cyan)"/>
</svg>'''


def stats_svg(repos: str, stars: str, date: datetime) -> str:
    stamp = date.astimezone(timezone.utc).strftime("%d %b %Y UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 260" role="img" aria-labelledby="title desc">
<title id="title">Public GitHub snapshot</title>
<desc id="desc">{repos} public repositories and {stars} stars across public repositories, fetched {stamp}. n/a means GitHub data was unavailable.</desc>
<style>
svg {{ --bg:#0b1021; --panel:#121b31; --text:#f5f7ff; --muted:#b9c7df; --line:#42577d; --cyan:#76e4df; --pink:#ed97c7; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
@media (prefers-color-scheme:light) {{ svg {{ --bg:#f5f7ff; --panel:#e9eef9; --text:#18223d; --muted:#415575; --line:#91a5c5; --cyan:#087f82; --pink:#ae397e; }} }}
@keyframes draw {{ to {{ stroke-dashoffset:-120; }} }}
.rule {{ animation:draw 10s linear infinite; }}
@media (prefers-reduced-motion:reduce) {{ .rule {{ animation:none; }} }}
</style>
<rect width="600" height="260" rx="22" fill="var(--bg)"/>
<rect x="15" y="15" width="570" height="230" rx="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="36" y="61" fill="var(--muted)" font-size="19" letter-spacing="1">PUBLIC GITHUB · {stamp}</text>
<path d="M300 88v122" stroke="var(--line)"/>
<text x="36" y="151" fill="var(--cyan)" font-size="76" font-weight="700">{repos}</text>
<text x="36" y="196" fill="var(--text)" font-size="23">PUBLIC REPOSITORIES</text>
<text x="327" y="151" fill="var(--pink)" font-size="76" font-weight="700">{stars}</text>
<text x="327" y="196" fill="var(--text)" font-size="23">STARS RECEIVED</text>
<path class="rule" d="M36 220h528" stroke="var(--cyan)" stroke-width="3" stroke-dasharray="54 120"/>
</svg>'''


def badge_svg(label: str, kind: str) -> str:
    if kind == "telegram":
        mark = '<path d="m30 47 31-13-9 31-8-12-7 7 1-13 19-9-23 12z" fill="var(--accent)"/>'
        detail = "Telegram @waattoo"
    elif kind == "email":
        mark = '<rect x="29" y="37" width="32" height="24" rx="3" fill="none" stroke="var(--accent)" stroke-width="3"/><path d="m30 40 15 12 15-12" fill="none" stroke="var(--accent)" stroke-width="3"/>'
        detail = "Email Alikhan"
    else:
        raise ValueError("unknown badge")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 94" role="img" aria-labelledby="title desc">
<title id="title">{label}</title><desc id="desc">Contact link: {detail}</desc>
<style>svg {{ --bg:#121b31; --text:#f5f7ff; --line:#42577d; --accent:#76e4df; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
@media (prefers-color-scheme:light) {{ svg {{ --bg:#e9eef9; --text:#18223d; --line:#91a5c5; --accent:#087f82; }} }}</style>
<rect x="1" y="1" width="278" height="92" rx="15" fill="var(--bg)" stroke="var(--line)" stroke-width="2"/>
{mark}<text x="81" y="59" fill="var(--text)" font-size="29" font-weight="650">{label}</text>
</svg>'''


def write_svg(path: Path, content: str) -> None:
    encoded = (content + "\n").encode("utf-8")
    if len(encoded) >= MAX_SVG:
        raise ValueError(f"SVG too large: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def patch_pacman(directory: Path) -> None:
    for name in ("pacman-contribution-graph.svg", "pacman-contribution-graph-dark.svg"):
        path = directory / name
        svg = path.read_text(encoding="utf-8")
        if "<svg" not in svg or "</svg>" not in svg:
            raise ValueError(f"invalid SVG: {name}")
        canvas = re.search(r'<svg\s+width="(\d+)"\s+height="(\d+)"', svg)
        if canvas is None or 'id="pacman"' not in svg:
            raise ValueError(f"unexpected Pac-Man canvas or sprite: {name}")
        static_svg, removed = SMIL_ELEMENT.subn("", svg)
        static_svg = METADATA_ELEMENT.sub("", static_svg)
        if removed == 0 or re.search(r"<animate\b|<animateTransform\b|<animateMotion\b", static_svg):
            raise ValueError(f"unsupported animation element: {name}")
        static_name = name.replace(".svg", "-static.svg")
        write_svg(directory / static_name, static_svg.rstrip("\n"))
        animated_svg = static_svg.replace(
            "</svg>", f"{pacman_css(int(canvas[1]), int(canvas[2]))}</svg>", 1
        )
        write_svg(path, animated_svg.rstrip("\n"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "patch-pacman"))
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "patch-pacman":
        patch_pacman(args.directory)
    else:
        repos, stars = public_stats()
        write_svg(args.directory / "header.svg", header_svg())
        write_svg(args.directory / "stats.svg", stats_svg(repos, stars, datetime.now(timezone.utc)))
        write_svg(args.directory / "telegram.svg", badge_svg("Telegram", "telegram"))
        write_svg(args.directory / "email.svg", badge_svg("Email", "email"))
        print(f"Generated public profile SVGs: repositories={repos}, stars={stars}")


if __name__ == "__main__":
    main()
