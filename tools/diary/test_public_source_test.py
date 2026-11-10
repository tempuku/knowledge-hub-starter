import tempfile
import unittest
from pathlib import Path

from test_public_source import violations


def put(root: Path, name: str, *, type_name="diary-entry", visibility="private"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + "type: " + type_name + "\n" +
        ("visibility: " + visibility + "\n" if visibility is not None else "") +
        "title: Example\n---\n\n# Example\n", encoding="utf-8",
    )


class PublicSourcePrivacyTests(unittest.TestCase):
    def test_reject_new_private_diary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            put(root, "openwiki/journal/2026/11/10/personal.md")
            self.assertTrue(violations(root))

    def test_reject_implicit_private_diary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            put(root, "openwiki/journal/2026/11/10/unspecified.md", visibility=None)
            self.assertTrue(violations(root))

    def test_reject_new_private_project(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            put(root, "openwiki/projects/new-secret.md", type_name="project")
            self.assertTrue(violations(root))

    def test_allow_explicit_public_entry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            put(root, "openwiki/journal/2026/11/10/public-note.md", visibility="public")
            self.assertFalse(violations(root))

    def test_legacy_exemptions_do_not_cover_new_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            put(root, "openwiki/projects/knowledge-hub.md", type_name="project")
            put(root, "openwiki/projects/ivanovo-models.md", type_name="project")
            self.assertFalse(violations(root))
            put(root, "openwiki/projects/another-private.md", type_name="project")
            self.assertEqual(len(violations(root)), 1)


if __name__ == "__main__":
    unittest.main()
