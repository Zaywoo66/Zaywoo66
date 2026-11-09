"""Check the public stack artwork and README data boundary."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "Backend": ["Python", "FastAPI", "PostgreSQL", "Go"],
    "Frontend": ["React", "TypeScript", "Vite", "Tailwind CSS"],
    "Tools": ["Docker", "GitHub Actions"],
}
ALT = ("Stack: Backend: Python, FastAPI, PostgreSQL, Go. "
       "Frontend: React, TypeScript, Vite, Tailwind CSS. "
       "Tools: Docker, GitHub Actions.")
SVG = "{http://www.w3.org/2000/svg}"


class StackSvgTests(unittest.TestCase):
    def test_themes_have_exact_stack_and_local_icons(self):
        expected = [item for group in GROUPS.items() for item in (group[0], *group[1])]
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                path = ROOT / "assets" / f"stack-{theme}.svg"
                payload = path.read_bytes()
                self.assertLess(len(payload), 150_000)
                text = payload.decode("utf-8")
                root = ET.fromstring(payload)
                self.assertEqual(root.attrib["viewBox"], "0 0 1200 260")
                labels = [element.text for element in root.iter(f"{SVG}text")]
                self.assertEqual(labels, expected)
                self.assertEqual(len(list(root.iter(f"{SVG}svg"))), 11)
                self.assertIn("@media (prefers-reduced-motion:reduce)", text)
                self.assertIn(".chip{opacity:1!important", text)
                self.assertIn("13s ease-in-out infinite", text)
                self.assertIn("@keyframes sweep", text)
                self.assertNotIn("<script", text)
                self.assertNotRegex(text, r"https?://(?!www\.w3\.org/2000/svg)")
                self.assertNotRegex(text, r"(?:href|src)\s*=")

    def test_readme_has_matching_accessible_sections(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertLess(readme.index("## Projects"), readme.index("## Stack"))
        self.assertLess(readme.index("## Stack"), readme.index("## Activity"))
        russian = readme.split("<summary>Русская версия</summary>", 1)[1].split("</details>", 1)[0]
        english = readme.split("## Stack", 1)[1].split("## Activity", 1)[0]
        for section in (russian, english):
            self.assertIn("Технологии" if section is russian else "<picture>", section)
            self.assertIn(f'alt="{ALT}"', section)
            self.assertIn('srcset="assets/stack-dark.svg"', section)
            self.assertIn('src="assets/stack-light.svg"', section)
            for label, names in GROUPS.items():
                self.assertIn(f"**{label}:** {' · '.join(names)}", section)
        self.assertEqual(readme.count(f'alt="{ALT}"'), 2)
        for forbidden in ("Rust", "Java", "Node", "Linux"):
            self.assertNotIn(forbidden, english)
            self.assertNotIn(forbidden, russian)


if __name__ == "__main__":
    unittest.main()
