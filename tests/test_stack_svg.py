"""Check the public stack artwork and README data boundary."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "Backend": ["Python", "FastAPI", "Go", "Rust", "Java", "PostgreSQL"],
    "Frontend": ["React", "TypeScript", "Vite", "Tailwind CSS"],
    "Data / ML": ["scikit-learn", "XGBoost"],
    "Tools": ["Git", "GitHub Actions", "Docker", "Docker Compose", "Linux"],
}
ALT = ("Stack: Backend: Python, FastAPI, Go, Rust, Java, PostgreSQL. "
       "Frontend: React, TypeScript, Vite, Tailwind CSS. "
       "Data / ML: scikit-learn, XGBoost. "
       "Tools: Git, GitHub Actions, Docker, Docker Compose, Linux.")
SVG = "{http://www.w3.org/2000/svg}"


class StackSvgTests(unittest.TestCase):
    def test_themes_have_exact_stack_and_local_icons(self):
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                path = ROOT / "assets" / f"stack-{theme}.svg"
                payload = path.read_bytes()
                self.assertLess(len(payload), 150_000)
                text = payload.decode("utf-8")
                root = ET.fromstring(payload)
                self.assertEqual(root.attrib["viewBox"], "0 0 760 300")
                rows = [element for element in root.iter(f"{SVG}g") if "data-group" in element.attrib]
                self.assertEqual([row.attrib["data-group"] for row in rows], list(GROUPS))
                self.assertEqual(sum(len(names) for names in GROUPS.values()), 17)
                self.assertLessEqual(sum(len(names) for names in GROUPS.values()), 24)
                self.assertEqual(root.find(f"{SVG}desc").text,
                                 " ".join(f"{label}: {', '.join(names)}."
                                          for label, names in GROUPS.items()))
                for row in rows:
                    names = [element.text for element in row.iter(f"{SVG}text")
                             if element.attrib.get("class") == "chip-name"]
                    self.assertEqual(names, GROUPS[row.attrib["data-group"]])
                    self.assertTrue(all(element.attrib.get("font-size") == "15"
                                        for element in row.iter(f"{SVG}text")
                                        if element.attrib.get("class") == "chip-name"))
                    self.assertEqual(len([element for element in row.iter(f"{SVG}text")
                                          if element.attrib.get("class") == "group-label"]), 1)
                self.assertEqual(len(list(root.iter(f"{SVG}svg"))), 15)
                self.assertEqual([element.text for element in root.iter(f"{SVG}text")
                                  if element.attrib.get("class") == "monogram"], ["Ja", "XG", "DC"])
                self.assertIn("@media (prefers-reduced-motion:reduce)", text)
                self.assertIn("@media (max-width:500px){.chip-name{font-size:19px}", text)
                self.assertIn(".card,.chip{opacity:1!important", text)
                self.assertIn("13s ease-in-out infinite", text)
                self.assertIn("@keyframes sweep", text)
                self.assertIn("@keyframes glow", text)
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
            lines = [line.removesuffix("<br>") for line in section.splitlines()
                     if line.startswith(tuple(f"{label}:" for label in GROUPS))]
            self.assertEqual(lines, [f"{label}: {', '.join(names)}"
                                     for label, names in GROUPS.items()])
        self.assertEqual(readme.count(f'alt="{ALT}"'), 2)
        for forbidden in ("Also:", "Kafka", "Redis", "Kubernetes"):
            self.assertNotIn(forbidden, english)
            self.assertNotIn(forbidden, russian)


if __name__ == "__main__":
    unittest.main()
