from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from scripts.generate_profile_svg import (
    MAX_SVG,
    badge_svg,
    header_svg,
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
        graphics = (
            header_svg(),
            stats_svg("12", "4", datetime(2026, 11, 8, tzinfo=timezone.utc)),
            badge_svg("Telegram", "telegram"),
            badge_svg("Email", "email"),
        )
        for svg in graphics:
            self.assertLess(len(svg.encode("utf-8")), MAX_SVG)
            self.assertIn("prefers-color-scheme:light", svg)
            self.assertNotIn("<image", svg)
        self.assertIn("prefers-reduced-motion:reduce", graphics[0])
        self.assertIn("prefers-reduced-motion:reduce", graphics[1])
        self.assertIn("Full-stack: Python/FastAPI · React/TypeScript", graphics[0])

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
