"""W-03 pure link planning fixtures; not evidence of atomic move integration."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from links_v1 import heading_slug, heading_fragments, repair_relative_links
from validate_v1 import IntegrityError


class LinkPlanningFixtures(unittest.TestCase):
    def test_unicode_and_duplicate_headings(self):
        self.assertEqual(heading_slug("Привет мир!"), "привет-мир")
        self.assertEqual(
            heading_fragments("# Intro\n## Intro\n# Привет мир!\n" +
                              "~~~md\n# Hidden\n~~~\n## Intro\n"),
            {"intro", "intro-2", "intro-3", "привет-мир"}
        )

    def test_inbound_relative_link_repair(self):
        source = "# Reference\n\n[Go](../notes/old.md#part)\n"
        changed, targets = repair_relative_links(
            source,
            before_path="openwiki/ideas/ref.md",
            after_path="openwiki/ideas/ref.md",
            moved_paths={"openwiki/notes/old.md": "openwiki/projects/new.md"},
            current_sources={
                "openwiki/ideas/ref.md": source,
                "openwiki/projects/new.md": "# Part\n\nBody\n",
            }
        )
        self.assertIn("[Go](../projects/new.md#part)", changed)
        self.assertEqual(targets, {"openwiki/projects/new.md"})

    def test_outbound_links_rebase_when_source_moves(self):
        source = "# Source\n\n[Go](../../concepts/target.md#intro)\n"
        destination = "openwiki/ideas/new.md"
        changed, targets = repair_relative_links(
            source,
            before_path="openwiki/projects/component/old.md",
            after_path=destination,
            moved_paths={"openwiki/projects/component/old.md": destination},
            current_sources={
                destination: source,
                "openwiki/concepts/target.md": "# Intro\n\nBody\n",
            }
        )
        self.assertIn("[Go](../concepts/target.md#intro)", changed)
        self.assertEqual(targets, {"openwiki/concepts/target.md"})

    def test_stable_record_links_unchanged(self):
        source = ("# Intro\n\n"
                  "[Other](record:123e4567-e89b-42d3-a456-426614174000#part)\n"
                  "[Site](https://example.org/page)\n"
                  "[Here](#intro)\n")
        changed, targets = repair_relative_links(
            source,
            before_path="openwiki/notes/old.md",
            after_path="openwiki/ideas/new.md",
            moved_paths={"openwiki/notes/old.md": "openwiki/ideas/new.md"},
            current_sources={"openwiki/ideas/new.md": source}
        )
        self.assertEqual(changed, source)
        self.assertEqual(targets, set())

    def test_fenced_code_not_rewritten(self):
        source = ("# Text\n\n" +
                  chr(96)*3 + "md\n" +
                  "[Do not touch](../notes/old.md)\n" +
                  chr(96)*3 + "\n\n" +
                  "[Real](../notes/old.md)\n")
        rewritten, linked = repair_relative_links(
            source,
            before_path="openwiki/ideas/ref.md",
            after_path="openwiki/ideas/ref.md",
            moved_paths={"openwiki/notes/old.md": "openwiki/projects/new.md"},
            current_sources={
                "openwiki/ideas/ref.md": source,
                "openwiki/projects/new.md": "# New\n",
            }
        )
        self.assertIn("[Do not touch](../notes/old.md)", rewritten)
        self.assertIn("[Real](../projects/new.md)", rewritten)
        self.assertEqual(linked, {"openwiki/projects/new.md"})

    def test_unsafe_uri_and_dangling_stable_id_fail_closed(self):
        for link in (
            "javascript:alert",
            "record:123e4567-e89b-42d3-a456-426614174000#missing",
            "record:invalid-uuid",
        ):
            with self.subTest(link=link), self.assertRaises(IntegrityError):
                source = "# Intro\n\n[Other](" + link + ")\n"
                repair_relative_links(
                    source, before_path="openwiki/notes/a.md",
                    after_path="openwiki/notes/a.md", moved_paths={},
                    current_sources={"openwiki/notes/a.md": source},
                    record_ids={"123e4567-e89b-42d3-a456-426614174000":
                                "openwiki/notes/a.md"}
                )

    def test_unsafe_and_missing_links_fail_closed(self):
        source_path = "openwiki/notes/old.md"
        for source in (
            "# A\n\n[Missing](../ideas/missing.md)\n",
            "# A\n\n[Escape](../../../outside.md)\n",
            "# A\n\n[Bad](//untrusted/path.md)\n",
            "# A\n\n[Heading](../ideas/target.md#missing)\n",
            "# A\n\n[Here](#not-present)\n",
        ):
            with self.subTest(source=source), self.assertRaises(IntegrityError):
                repair_relative_links(
                    source,
                    before_path=source_path,
                    after_path=source_path,
                    moved_paths={},
                    current_sources={
                        source_path: source,
                        "openwiki/ideas/target.md": "# Present\n",
                    }
                )


if __name__ == "__main__":
    unittest.main()
