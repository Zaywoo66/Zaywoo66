from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.generate_profile_svg import (
    MAX_SVG,
    badge_svg,
    header_svg,
    mobile_header_svg,
    patch_pacman,
    public_stats,
    stats_svg,
    write_svg,
)


class ProfileSvgTests(unittest.TestCase):
    def test_public_counts_are_from_complete_owned_repository_list(self):
        def fetch(path):
            if path.startswith("/users/Zaywoo66/repos?"):
                return [
                    {"owner": {"login": "Zaywoo66"}, "stargazers_count": 2},
                    {"owner": {"login": "Zaywoo66"}, "stargazers_count": 3},
                ]
            return {"login": "Zaywoo66", "public_repos": 2}

        self.assertEqual(public_stats(fetch), ("2", "5"))

    def test_partial_or_foreign_data_cannot_become_a_star_total(self):
        def partial(path):
            if "repos?" in path:
                return [{"owner": {"login": "Zaywoo66"}, "stargazers_count": 9}]
            return {"login": "Zaywoo66", "public_repos": 2}

        self.assertEqual(public_stats(partial), ("2", "n/a"))

        def failed(_path):
            raise OSError("unavailable")

        self.assertEqual(public_stats(failed), ("n/a", "n/a"))

    def test_local_graphics_are_small_theme_aware_and_reduced_motion_safe(self):
        headers = tuple(header_svg(theme, variant) for theme in ("dark", "light")
                        for variant in ("flow", "aurora"))
        graphics = headers + (
            stats_svg("12", "4", datetime(2026, 11, 8, tzinfo=timezone.utc)),
        ) + tuple(badge_svg(label, kind, theme) for label, kind in
                  (("Telegram", "telegram"), ("Email", "email"), ("LinkedIn", "linkedin"))
                  for theme in ("dark", "light"))
        for svg in graphics:
            self.assertLess(len(svg.encode("utf-8")), MAX_SVG)
            ET.fromstring(svg)
            self.assertNotIn("<image", svg)
            self.assertNotIn("<script", svg)
            self.assertIn("system-ui", svg)
        for svg in headers:
            self.assertIn('viewBox="0 0 1200 220"', svg)
            self.assertIn("prefers-reduced-motion:reduce", svg)
            self.assertIn("Astana, Kazakhstan", svg)
        self.assertIn("Full-stack: Python/FastAPI · React/TypeScript", graphics[0])
        self.assertIn("@keyframes to-api", headers[0])
        self.assertIn("PostgreSQL", headers[0])
        self.assertEqual(headers[1].count('class="particle"'), 26)
        self.assertIn("prefers-reduced-motion:reduce", graphics[4])
        for theme in ("dark", "light"):
            still = header_svg(theme, static=True)
            ET.fromstring(still)
            self.assertIn("*{animation:none!important}", still)
            self.assertIn(".packet,.ring{display:none!important}", still)
            mobile = mobile_header_svg(theme)
            self.assertIn('viewBox="0 0 375 190"', mobile)
            self.assertIn("prefers-reduced-motion:reduce", mobile)
            self.assertLess(len(mobile.encode("utf-8")), MAX_SVG)
            self.assertIn("*{animation:none!important}", mobile_header_svg(theme, True))
            aurora_mobile = mobile_header_svg(theme, variant="aurora")
            self.assertEqual(aurora_mobile.count('class="particle"'), 24)
            self.assertIn("prefers-reduced-motion:reduce", aurora_mobile)
            self.assertIn("*{animation:none!important}",
                          mobile_header_svg(theme, True, "aurora"))

    def test_pacman_output_is_checked_and_motion_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ("pacman-contribution-graph.svg", "pacman-contribution-graph-dark.svg"):
                (directory / name).write_text(
                    '<svg width="1166" height="184"><rect width="1"><animate '
                    'attributeName="fill" dur="147600ms" repeatCount="indefinite" '
                    'values="red;blue"/></rect><path id="pacman"><animateTransform '
                    'attributeName="transform" type="translate" dur="147600ms" '
                    'values="0,0;10,0"/></path></svg>',
                    encoding="utf-8",
                )
            patch_pacman(directory)
            for path in directory.iterdir():
                svg = path.read_text(encoding="utf-8")
                self.assertNotRegex(svg, r"<animate(?:Transform|Motion)?\b")
                if path.name.endswith("-static.svg"):
                    self.assertNotIn("@keyframes", svg)
                else:
                    self.assertIn("prefers-reduced-motion: reduce", svg)
                    self.assertIn("@keyframes pacman-travel", svg)
                self.assertLess(path.stat().st_size, MAX_SVG)

    def test_missing_pacman_file_and_oversized_graphic_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                patch_pacman(Path(temporary))
            with self.assertRaises(ValueError):
                write_svg(Path(temporary) / "big.svg", "x" * MAX_SVG)


if __name__ == "__main__":
    unittest.main()
