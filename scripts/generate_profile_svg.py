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
import math
import os
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET


USER = "Zaywoo66"
MAX_RESPONSE = 1_000_000
MAX_SVG = 150_000
SMIL_ELEMENT = re.compile(r"<animate(?:Transform|Motion)?\b[\s\S]*?/>")
METADATA_ELEMENT = re.compile(r"<metadata>.*?</metadata>", re.DOTALL)


def pacman_route(element: ET.Element, width: int, height: int) -> tuple[str, tuple[int, int], str]:
    """Keep the upstream maze route, reducing only collinear intermediate steps."""
    motion = [child for child in element if child.attrib.get("type") == "translate"
              and child.attrib.get("attributeName") == "transform"]
    if len(motion) != 1:
        raise ValueError("missing or duplicate maze route")
    animation = motion[0]
    duration = re.fullmatch(r"(\d+)ms", animation.attrib.get("dur", ""))
    positions = animation.attrib.get("values", "").split(";")
    times = animation.attrib.get("keyTimes", "").split(";")
    if not duration or not 10_000 <= int(duration[1]) <= 180_000 or not 3 <= len(positions) <= 1000:
        raise ValueError("unsupported maze animation")
    if len(positions) != len(times):
        raise ValueError("incomplete maze route")
    try:
        keys = [float(time) for time in times]
    except ValueError as exc:
        raise ValueError("invalid maze timing") from exc
    if (keys[0] != 0 or keys[-1] != 1
            or any(not math.isfinite(time) or not 0 <= time <= 1 for time in keys)
            or any(a > b for a, b in zip(keys, keys[1:]))):
        raise ValueError("invalid maze timing")
    coords = []
    for value in positions:
        match = re.fullmatch(r"(-?\d+),(-?\d+)", value)
        if match is None:
            raise ValueError("invalid maze coordinate")
        x, y = int(match[1]), int(match[2])
        if not 0 <= x <= width or not 0 <= y <= height:
            raise ValueError("maze route leaves canvas")
        coords.append((x, y))
    turns = [0]
    for index in range(1, len(coords) - 1):
        before = (coords[index][0] - coords[index - 1][0],
                  coords[index][1] - coords[index - 1][1])
        after = (coords[index + 1][0] - coords[index][0],
                 coords[index + 1][1] - coords[index][1])
        if before != after:
            turns.append(index)
    turns.append(len(coords) - 1)
    frames = "".join(
        f"{100 * index / (len(coords) - 1):.4f}%"
        f"{{transform:translate({coords[index][0]}px,{coords[index][1]}px)}}"
        for index in turns
    )
    return f"{int(duration[1]) / 1000:g}s", coords[0], frames


def pacman_css(routes: dict[str, tuple[str, tuple[int, int], str]]) -> str:
    selectors = []
    rules = []
    for actor, (duration, _start, frames) in routes.items():
        rules.append(f"@keyframes route-{actor}{{{frames}}}")
        rules.append(f"#{actor}{{animation:route-{actor} {duration} linear infinite alternate}}")
        selectors.append(f"#{actor}")
    rules.append("@media (prefers-reduced-motion:reduce){"
                 + ",".join(selectors) + "{animation:none!important}}")
    return "<style>" + "".join(rules) + "</style>"


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


def header_svg(theme: str = "dark", variant: str = "flow", static: bool = False) -> str:
    """A compact, theme-specific header with an optional saved aurora variant."""
    if theme not in ("dark", "light") or variant not in ("flow", "aurora"):
        raise ValueError("unsupported header variant")
    palette = {
        "dark": ("#0b1021", "#f5f7ff", "#76e4df", "#ed97c7", "#f3c789"),
        "light": ("#f5f7ff", "#18223d", "#087f82", "#ae397e", "#9b5b11"),
    }[theme]
    bg, text, teal, pink, amber = palette
    common_css = '''svg{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
@keyframes drift-a{50%{transform:translate(24px,-10px);opacity:.72}}
@keyframes drift-b{50%{transform:translate(-18px,12px);opacity:.55}}
.blob-a{animation:drift-a 18s ease-in-out infinite}
.blob-b{animation:drift-b 16s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){.blob-a,.blob-b,.particle,.packet,.ring{animation:none!important}.packet,.ring{opacity:0!important}}'''
    flow_css = '''@keyframes to-api{0%{transform:translate(675px,108px);opacity:1}24%{transform:translate(770px,108px);opacity:1}25%,100%{transform:translate(770px,108px);opacity:0}}
@keyframes to-db{0%,24%{transform:translate(885px,108px);opacity:0}25%{transform:translate(885px,108px);opacity:1}49%{transform:translate(980px,108px);opacity:1}50%,100%{transform:translate(980px,108px);opacity:0}}
@keyframes from-db{0%,49%{transform:translate(980px,108px);opacity:0}50%{transform:translate(980px,108px);opacity:1}74%{transform:translate(885px,108px);opacity:1}75%,100%{transform:translate(885px,108px);opacity:0}}
@keyframes from-api{0%,74%{transform:translate(770px,108px);opacity:0}75%{transform:translate(770px,108px);opacity:1}99%{transform:translate(675px,108px);opacity:1}100%{transform:translate(675px,108px);opacity:0}}
@keyframes pulse-api{0%,22%,27%,72%,77%,100%{opacity:0}24%,74%{opacity:.7}}
@keyframes pulse-db{0%,47%,52%,100%{opacity:0}49%{opacity:.7}}
@keyframes pulse-react{0%,97%{opacity:0}99%{opacity:.7}100%{opacity:0}}
.p1{animation:to-api 7s linear infinite}.p2{animation:to-db 7s linear infinite}
.p3{animation:from-db 7s linear infinite}.p4{animation:from-api 7s linear infinite}
.api-ring{animation:pulse-api 7s linear infinite}.db-ring{animation:pulse-db 7s linear infinite}
.react-ring{animation:pulse-react 7s linear infinite}'''
    aurora_css = '''@keyframes float{50%{transform:translate(0px,-11px);opacity:.85}}
.particle{animation:float 17s ease-in-out infinite}'''
    css = common_css + "\n" + (flow_css if variant == "flow" else aurora_css)
    if static:
        # SVGs embedded with <img> do not consistently inherit motion settings.
        css += "\n*{animation:none!important}.packet,.ring{display:none!important}"
    background = f'''<defs>
<linearGradient id="background" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{teal}" stop-opacity=".24"/></linearGradient>
<pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="{text}" stroke-opacity=".09"/></pattern>
<filter id="soft"><feGaussianBlur stdDeviation="32"/></filter></defs>
<rect width="1200" height="220" rx="22" fill="url(#background)"/>
<rect width="1200" height="220" rx="22" fill="url(#grid)"/>
<g filter="url(#soft)"><circle class="blob-a" cx="690" cy="34" r="82" fill="{teal}" opacity=".22"/>
<circle class="blob-b" cx="1080" cy="183" r="87" fill="{pink}" opacity=".24"/></g>'''
    name = f'''<text x="42" y="91" fill="{text}" font-size="36" font-weight="650">Alikhan</text>
<text x="42" y="126" fill="{text}" opacity=".85" font-size="18">Full-stack: Python/FastAPI · React/TypeScript</text>
<text x="42" y="151" fill="{text}" opacity=".56" font-size="13">Astana, Kazakhstan</text>'''
    if variant == "flow":
        content = f'''<g fill="none" stroke="{teal}" stroke-opacity=".52" stroke-width="2">
<path d="M675 108H770M885 108H980"/></g>
<g class="packet p1" fill="{teal}"><circle cx="-13" r="3" opacity=".25"/><circle cx="-6" r="3" opacity=".48"/><circle r="5"/></g>
<g class="packet p2" fill="{teal}"><circle cx="-13" r="3" opacity=".25"/><circle cx="-6" r="3" opacity=".48"/><circle r="5"/></g>
<g class="packet p3" fill="{amber}"><circle cx="13" r="2" opacity=".25"/><circle cx="6" r="2" opacity=".48"/><circle r="4"/></g>
<g class="packet p4" fill="{amber}"><circle cx="13" r="2" opacity=".25"/><circle cx="6" r="2" opacity=".48"/><circle r="4"/></g>
<g fill="{bg}" fill-opacity=".78" stroke="{text}" stroke-opacity=".28">
<rect x="570" y="68" width="105" height="80" rx="13"/>
<rect x="770" y="68" width="115" height="80" rx="13"/>
<rect x="980" y="68" width="145" height="80" rx="13"/></g>
<g fill="none" stroke-width="3">
<path d="M601 94h15l8 10-8 10h-15l-8-10z" stroke="{teal}"/>
<path d="M804 94h26m-26 8h18m-18 8h23" stroke="{pink}" stroke-linecap="round"/>
<ellipse cx="1025" cy="96" rx="19" ry="5" stroke="{amber}"/>
<path d="M1006 96v15c0 7 38 7 38 0V96" stroke="{amber}"/></g>
<g fill="{text}" font-size="16" font-weight="600">
<text x="586" y="135">React</text><text x="789" y="135">FastAPI</text>
<text x="996" y="135">PostgreSQL</text></g>
<g class="ring react-ring" fill="none" stroke="{teal}" stroke-width="2"><rect x="566" y="64" width="113" height="88" rx="16"/></g>
<g class="ring api-ring" fill="none" stroke="{pink}" stroke-width="2"><rect x="766" y="64" width="123" height="88" rx="16"/></g>
<g class="ring db-ring" fill="none" stroke="{amber}" stroke-width="2"><rect x="976" y="64" width="153" height="88" rx="16"/></g>'''
    else:
        particles = "".join(
            f'<circle class="particle" cx="{570 + (i * 71) % 610}" cy="{22 + (i * 47) % 173}" '
            f'r="{1 + i % 2}" fill="{teal if i % 3 else amber}" opacity=".55" '
            f'style="animation-delay:-{i % 15}s"/>'
            for i in range(26)
        )
        content = f'''<g filter="url(#soft)"><circle class="blob-a" cx="790" cy="96" r="105" fill="{pink}" opacity=".3"/>
<circle class="blob-b" cx="1040" cy="88" r="115" fill="{teal}" opacity=".34"/></g>{particles}'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 220" role="img" aria-labelledby="title desc">
<title id="title">Alikhan — full-stack developer</title>
<desc id="desc">{('React, FastAPI and PostgreSQL connected by a request and response flow.' if variant == 'flow' else 'Soft aurora and drifting particles.')}</desc>
<style>{css}</style>{background}{name}{content}</svg>'''


def mobile_header_svg(theme: str = "dark", static: bool = False,
                      variant: str = "flow") -> str:
    """Keep the actual name and stack readable when GitHub narrows the README."""
    if theme not in ("dark", "light") or variant not in ("flow", "aurora"):
        raise ValueError("unsupported mobile header theme")
    bg, text, teal, pink, amber = {
        "dark": ("#0b1021", "#f5f7ff", "#76e4df", "#ed97c7", "#f3c789"),
        "light": ("#f5f7ff", "#18223d", "#087f82", "#ae397e", "#9b5b11"),
    }[theme]
    if variant == "aurora":
        particles = "".join(
            f'<circle class="particle" cx="{18 + (i * 53) % 338}" '
            f'cy="{99 + (i * 31) % 75}" r="{1 + i % 2}" '
            f'fill="{teal if i % 3 else amber}" opacity=".65" '
            f'style="animation-delay:-{i % 15}s"/>' for i in range(24)
        )
        still = '*{animation:none!important}' if static else ''
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 375 190" role="img" aria-labelledby="title desc">
<title id="title">Alikhan — full-stack developer</title><desc id="desc">Soft aurora and drifting particles.</desc>
<style>svg{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}}
@keyframes mobile-drift{{50%{{transform:translate(12px,-8px);opacity:.7}}}}
@keyframes mobile-float{{50%{{transform:translate(0px,-9px);opacity:.9}}}}
.blob{{animation:mobile-drift 18s ease-in-out infinite}}.particle{{animation:mobile-float 17s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{.blob,.particle{{animation:none!important}}}}{still}</style>
<defs><linearGradient id="background" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{teal}" stop-opacity=".19"/></linearGradient>
<filter id="soft"><feGaussianBlur stdDeviation="22"/></filter></defs>
<rect width="375" height="190" rx="18" fill="url(#background)"/>
<g filter="url(#soft)"><circle class="blob" cx="234" cy="134" r="52" fill="{pink}" opacity=".32"/>
<circle class="blob" cx="328" cy="119" r="55" fill="{teal}" opacity=".32"/></g>
<text x="18" y="39" fill="{text}" font-size="26" font-weight="650">Alikhan</text>
<text x="18" y="65" fill="{text}" opacity=".85" font-size="13">Full-stack: Python/FastAPI · React/TypeScript</text>
<text x="18" y="84" fill="{text}" opacity=".56" font-size="11">Astana, Kazakhstan</text>{particles}</svg>'''
    css = '''svg{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
@keyframes mobile-out-a{0%{transform:translate(100px,135px);opacity:1}24%{transform:translate(146px,135px);opacity:1}25%,100%{opacity:0}}
@keyframes mobile-out-b{0%,24%{opacity:0}25%{transform:translate(228px,135px);opacity:1}49%{transform:translate(275px,135px);opacity:1}50%,100%{opacity:0}}
@keyframes mobile-back-b{0%,49%{opacity:0}50%{transform:translate(275px,135px);opacity:1}74%{transform:translate(228px,135px);opacity:1}75%,100%{opacity:0}}
@keyframes mobile-back-a{0%,74%{opacity:0}75%{transform:translate(146px,135px);opacity:1}99%{transform:translate(100px,135px);opacity:1}100%{opacity:0}}
@keyframes mobile-api-pulse{0%,23%,27%,73%,77%,100%{opacity:0}25%,75%{opacity:.75}}
@keyframes mobile-db-pulse{0%,48%,52%,100%{opacity:0}50%{opacity:.75}}
@keyframes mobile-react-pulse{0%,97%,100%{opacity:0}99%{opacity:.75}}
.p1{animation:mobile-out-a 7s linear infinite}.p2{animation:mobile-out-b 7s linear infinite}
.p3{animation:mobile-back-b 7s linear infinite}.p4{animation:mobile-back-a 7s linear infinite}
.api-ring{animation:mobile-api-pulse 7s linear infinite}
.db-ring{animation:mobile-db-pulse 7s linear infinite}
.react-ring{animation:mobile-react-pulse 7s linear infinite}
@media (prefers-reduced-motion:reduce){.packet,.ring{animation:none!important;opacity:0!important}}'''
    if static:
        css += '\n*{animation:none!important}.packet,.ring{display:none!important}'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 375 190" role="img" aria-labelledby="title desc">
<title id="title">Alikhan — full-stack developer</title>
<desc id="desc">React, FastAPI and PostgreSQL connected by a request and response flow.</desc>
<style>{css}</style>
<defs><linearGradient id="background" x2="1" y2="1"><stop stop-color="{bg}"/><stop offset="1" stop-color="{teal}" stop-opacity=".19"/></linearGradient>
<pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="{text}" stroke-opacity=".08"/></pattern></defs>
<rect width="375" height="190" rx="18" fill="url(#background)"/><rect width="375" height="190" rx="18" fill="url(#grid)"/>
<text x="18" y="39" fill="{text}" font-size="26" font-weight="650">Alikhan</text>
<text x="18" y="65" fill="{text}" opacity=".85" font-size="13">Full-stack: Python/FastAPI · React/TypeScript</text>
<text x="18" y="84" fill="{text}" opacity=".56" font-size="11">Astana, Kazakhstan</text>
<path d="M100 135h46m82 0h47" fill="none" stroke="{teal}" stroke-opacity=".6" stroke-width="2"/>
<g class="packet p1" fill="{teal}"><circle r="4"/></g><g class="packet p2" fill="{teal}"><circle r="4"/></g>
<g class="packet p3" fill="{amber}"><circle r="3"/></g><g class="packet p4" fill="{amber}"><circle r="3"/></g>
<g fill="{bg}" fill-opacity=".8" stroke="{text}" stroke-opacity=".28"><rect x="18" y="106" width="82" height="58" rx="10"/>
<rect x="146" y="106" width="82" height="58" rx="10"/><rect x="275" y="106" width="82" height="58" rx="10"/></g>
<g fill="none" stroke-width="2.5"><path d="M47 119h12l6 7-6 7H47l-6-7z" stroke="{teal}"/>
<path d="M174 120h21m-21 6h16" stroke="{pink}" stroke-linecap="round"/>
<ellipse cx="312" cy="123" rx="13" ry="4" stroke="{amber}"/><path d="M299 123v10c0 5 26 5 26 0v-10" stroke="{amber}"/></g>
<g fill="{text}" font-size="11" font-weight="600"><text x="40" y="151">React</text>
<text x="166" y="151">FastAPI</text><text x="282" y="151">PostgreSQL</text></g>
<g class="ring react-ring" fill="none" stroke="{teal}" stroke-width="2"><rect x="16" y="104" width="86" height="62" rx="12"/></g>
<g class="ring api-ring" fill="none" stroke="{pink}" stroke-width="2"><rect x="144" y="104" width="86" height="62" rx="12"/></g>
<g class="ring db-ring" fill="none" stroke="{amber}" stroke-width="2"><rect x="273" y="104" width="86" height="62" rx="12"/></g></svg>'''


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


def badge_svg(label: str, kind: str, theme: str = "dark") -> str:
    if theme not in ("dark", "light"):
        raise ValueError("unsupported contact theme")
    bg, text, accent, border = {
        "dark": ("#0b1021", "#f5f7ff", "#76e4df", "#f5f7ff"),
        "light": ("#f5f7ff", "#18223d", "#087f82", "#18223d"),
    }[theme]
    if kind == "telegram":
        mark = f'<path d="m23 38 34-14-8 32-9-10-8 8 2-12 18-13-24 12z" fill="{accent}"/>'
        detail = "Telegram @waattoo"
    elif kind == "email":
        mark = f'<rect x="23" y="26" width="34" height="25" rx="4" fill="none" stroke="{accent}" stroke-width="2.5"/><path d="m25 29 15 11 15-11" fill="none" stroke="{accent}" stroke-width="2.5"/>'
        detail = "Email Alikhan"
    elif kind == "linkedin":
        mark = f'<rect x="22" y="22" width="36" height="34" rx="6" fill="none" stroke="{accent}" stroke-width="2.5"/><circle cx="31" cy="31" r="2.5" fill="{accent}"/><path d="M31 38v11m8 0V38m0 4c2-5 10-5 10 1v6" fill="none" stroke="{accent}" stroke-width="3" stroke-linecap="round"/>'
        detail = "LinkedIn Alikhan Kokenov"
    else:
        raise ValueError("unknown badge")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 76" role="img" aria-labelledby="title desc">
<title id="title">{label}</title><desc id="desc">Contact link: {detail}</desc>
<style>svg {{ font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}</style>
<rect x="1" y="1" width="254" height="74" rx="20" fill="{bg}" stroke="{border}" stroke-opacity=".28" stroke-width="2"/>
{mark}<text x="75" y="48" fill="{text}" font-size="26" font-weight="600">{label}</text>
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
        width, height = int(canvas[1]), int(canvas[2])
        if not 600 <= width <= 2000 or not 100 <= height <= 400:
            raise ValueError(f"unexpected Pac-Man canvas size: {name}")
        root = ET.fromstring(svg)
        routes = {}
        for actor in ("pacman", "ghost0", "ghost1", "ghost2", "ghost3"):
            actors = [item for item in root.iter() if item.attrib.get("id") == actor]
            if len(actors) != 1:
                raise ValueError(f"missing or duplicate maze actor: {actor}")
            element = actors[0]
            routes[actor] = pacman_route(element, width, height)
            start = routes[actor][1]
            opening = re.search(rf'<(?:path|g)\b[^>]*\bid="{actor}"[^>]*>', svg)
            if opening is None:
                raise ValueError(f"missing maze actor tag: {actor}")
            tag = opening[0]
            initial = f'transform="translate({start[0]},{start[1]})"'
            if re.search(r'\btransform="[^"]*"', tag):
                tag = re.sub(r'\btransform="[^"]*"', initial, tag, count=1)
            else:
                tag = tag[:-1] + f" {initial}>"
            svg = svg[:opening.start()] + tag + svg[opening.end():]
        for rect in root.iter():
            if not rect.tag.endswith("rect"):
                continue
            fills = [child for child in rect if child.attrib.get("attributeName") == "fill"]
            if not fills:
                continue
            if len(fills) != 1:
                raise ValueError("ambiguous contribution cell")
            cell_id = rect.attrib.get("id", "")
            color = fills[0].attrib.get("values", "").split(";")[0]
            if not re.fullmatch(r"c-\d+-\d+", cell_id) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                raise ValueError("invalid contribution cell")
            pattern = rf'(<rect\b[^>]*\bid="{cell_id}"[^>]*\bfill=")[^"]+'
            svg, replaced = re.subn(pattern, lambda match: match[1] + color, svg, count=1)
            if replaced != 1:
                raise ValueError(f"missing contribution cell: {cell_id}")
        static_svg, removed = SMIL_ELEMENT.subn("", svg)
        static_svg = METADATA_ELEMENT.sub("", static_svg)
        if removed == 0 or re.search(r"<animate\b|<animateTransform\b|<animateMotion\b", static_svg):
            raise ValueError(f"unsupported animation element: {name}")
        ET.fromstring(static_svg)
        static_name = name.replace(".svg", "-static.svg")
        write_svg(directory / static_name, static_svg.rstrip("\n"))
        animated_svg = static_svg.replace(
            "</svg>", f"{pacman_css(routes)}</svg>", 1
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
        write_svg(args.directory / "header-light.svg", header_svg("light"))
        write_svg(args.directory / "header-static.svg", header_svg(static=True))
        write_svg(args.directory / "header-light-static.svg", header_svg("light", static=True))
        for theme, suffix in (("dark", ""), ("light", "-light")):
            write_svg(args.directory / f"header-mobile{suffix}.svg", mobile_header_svg(theme))
            write_svg(args.directory / f"header-mobile{suffix}-static.svg", mobile_header_svg(theme, True))
        write_svg(args.directory / "stats.svg", stats_svg(repos, stars, datetime.now(timezone.utc)))
        for label, kind in (("Telegram", "telegram"), ("Email", "email"), ("LinkedIn", "linkedin")):
            write_svg(args.directory / f"{kind}.svg", badge_svg(label, kind))
            write_svg(args.directory / f"{kind}-light.svg", badge_svg(label, kind, "light"))
        print(f"Generated public profile SVGs: repositories={repos}, stars={stars}")


if __name__ == "__main__":
    main()
