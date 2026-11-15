import importlib.util
import hashlib
import json
import pathlib
import unittest
from unittest.mock import patch

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "audit_legacy_evidence.py"
spec = importlib.util.spec_from_file_location("audit_legacy_evidence", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class AuditEvidenceTests(unittest.TestCase):
    def test_exact_bytes_and_event_provenance(self):
        source = b"---\ntype: note\nvisibility: private\n---\n\n[child](child.md)\n"
        event = {"id": "legacy-1", "timestamp": "unknown", "after": source.decode(), "before": None}
        log = ("# history\n\n```json\n" + json.dumps(event) + "\n```\n").encode()
        paths = ["openwiki/index.md", "openwiki/a.md", "openwiki/a.log.md"]
        data = {"openwiki/a.md": source, "openwiki/a.log.md": log}
        def fake_git(*args):
            if args[0] == "ls-tree":
                return ("\0".join(paths) + "\0").encode()
            self.assertEqual(args[0], "show")
            return data[args[1].split(":", 1)[1]]
        with patch.object(audit, "git_bytes", side_effect=fake_git):
            report = audit.audit("a" * 40)
        self.assertFalse(report["publication_approved"])
        self.assertEqual(len(report["items"]), 2)
        record, history = report["items"]
        self.assertEqual(record["sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(record["frontmatter"]["visibility"], "private")
        self.assertEqual(record["relative_links"], ["child.md"])
        self.assertEqual(history["native_events"][0]["timestamp"], "unknown")
        self.assertEqual(history["native_events"][0]["after_sha256"], record["sha256"])
        self.assertEqual(history["review_status"], "pending")

if __name__ == "__main__":
    unittest.main()
