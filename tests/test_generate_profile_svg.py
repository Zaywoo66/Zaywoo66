from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import copy
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.generate_profile_svg import (
    MAX_SVG,
    badge_svg,
    contribution_svg,
    contribution_weeks,
    header_svg,
    mobile_header_svg,
    public_stats,
    stats_svg,
    write_svg,
)


class ProfileSvgTests(unittest.TestCase):
    @staticmethod
    def calendar_payload():
        start = date(2025, 11, 9)
        days = [{"date": (start + timedelta(days=index)).isoformat(),
                 "contributionCount": index % 11}
                for index in range(366)]
        return {"data": {"user": {"contributionsCollection": {
            "restrictedContributionsCount": 0,
            "contributionCalendar": {
                "totalContributions": sum(day["contributionCount"] for day in days),
                "weeks": [{"contributionDays": days[index:index + 7]}
                          for index in range(0, len(days), 7)],
            },
        }}}}

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

    def test_contributions_use_only_complete_verified_public_weeks(self):
        payload = self.calendar_payload()
        weeks = contribution_weeks(lambda: payload, date(2026, 11, 9))
        self.assertEqual(len(weeks), 26)
        self.assertEqual(weeks[0][0][0], date(2026, 5, 10))
        self.assertEqual(weeks[-1][-1][0], date(2026, 11, 7))
        self.assertEqual(sum(count for week in weeks for _, count in week), 920)

        for mutation in ("private", "missing", "duplicate", "wrong-total", "stale", "graphql-error"):
            bad = copy.deepcopy(payload)
            calendar = bad["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            if mutation == "private":
                bad["data"]["user"]["contributionsCollection"]["restrictedContributionsCount"] = 1
            elif mutation == "missing":
                calendar["weeks"][20]["contributionDays"].pop()
            elif mutation == "duplicate":
                calendar["weeks"][20]["contributionDays"][1]["date"] = calendar["weeks"][20]["contributionDays"][0]["date"]
            elif mutation == "wrong-total":
                calendar["totalContributions"] += 1
            elif mutation == "stale":
                calendar["weeks"][-1]["contributionDays"].pop()
                calendar["weeks"][-1]["contributionDays"].pop()
            else:
                bad["errors"] = [{"message": "unavailable"}]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                contribution_weeks(lambda: bad, date(2026, 11, 9))

    def test_both_activity_graphics_are_truthful_and_reduced_motion_safe(self):
        weeks = contribution_weeks(self.calendar_payload, date(2026, 11, 9))
        total = sum(count for week in weeks for _, count in week)
        for theme in ("dark", "light"):
            for kind in ("calendar", "trend"):
                svg = contribution_svg(weeks, theme, kind)
                ET.fromstring(svg)
                self.assertLess(len(svg.encode("utf-8")), MAX_SVG)
                self.assertIn(f"{total} public contributions", svg)
                self.assertIn("prefers-reduced-motion:reduce", svg)
                self.assertNotIn("<script", svg)
                self.assertNotIn("<image", svg)
                self.assertNotIn("href=", svg)
                if kind == "calendar":
                    self.assertEqual(svg.count('class="week"'), 26)
                    self.assertEqual(svg.count('width="15"'), 182)
                else:
                    self.assertIn("Weekly counts, earliest to latest:", svg)
                    self.assertIn("@keyframes trace", svg)
                static_svg = contribution_svg(weeks, theme, kind, True)
                ET.fromstring(static_svg)
                self.assertNotIn("@keyframes", static_svg)
                if kind == "trend":
                    self.assertIn(".trace{stroke-dashoffset:0;opacity:1}", static_svg)

    def test_oversized_graphic_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                write_svg(Path(temporary) / "big.svg", "x" * MAX_SVG)


if __name__ == "__main__":
    unittest.main()
