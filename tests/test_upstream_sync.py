"""Test three-way synchronization with local repositories, without network writes."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location("sync_upstream", Path(__file__).resolve().parents[1] / "ci_tooling/sync_upstream.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Sync test")
        self.git("config", "user.email", "sync@example.test")
        self.commit("shared.txt", "original")
        self.git("branch", "official")

    def git(self, *args):
        return sync.checked(self.root, *args)

    def commit(self, name, text):
        (self.root / name).write_text(text)
        self.git("add", name)
        self.git("commit", "-m", name)

    def prepare(self, candidate="missing-candidate"):
        return sync.prepare(self.root, "main", "official", candidate)

    def test_no_official_changes_creates_no_candidate(self):
        self.assertIsNone(self.prepare())
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_official_payload_and_version_arrive_together_preserving_custom_ui(self):
        self.commit("ui.txt", "fork UI")
        main = self.git("rev-parse", "main")
        self.git("switch", "official")
        self.commit("kext.zip", "new payload")
        self.commit("constants.py", "new version")
        self.git("switch", "main")
        result = self.prepare()
        self.assertTrue(result["changed"])
        self.assertEqual((self.root / "ui.txt").read_text(), "fork UI")
        self.assertEqual((self.root / "constants.py").read_text(), "new version")
        self.assertEqual((self.root / "kext.zip").read_text(), "new payload")
        self.assertEqual(self.git("rev-parse", "main"), main)

    def test_conflict_aborts_without_changing_main(self):
        self.commit("shared.txt", "fork implementation")
        main = self.git("rev-parse", "main")
        self.git("switch", "official")
        self.commit("shared.txt", "official implementation")
        self.git("switch", "main")
        with self.assertRaisesRegex(RuntimeError, "Merge blocked"):
            self.prepare()
        self.assertEqual(self.git("rev-parse", "main"), main)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual((self.root / "shared.txt").read_text(), "fork implementation")

    def test_existing_candidate_keeps_manual_review_changes_without_new_merge(self):
        self.git("switch", "official")
        self.commit("kext.zip", "new payload")
        self.git("switch", "main")
        self.prepare()
        self.commit("review.txt", "reviewed correction")
        self.git("branch", "saved-candidate")
        self.git("switch", "main")
        self.git("branch", "-D", sync.BRANCH)
        result = self.prepare("saved-candidate")
        self.assertFalse(result["changed"])
        self.assertEqual((self.root / "review.txt").read_text(), "reviewed correction")

    def test_dirty_checkout_is_rejected(self):
        (self.root / "shared.txt").write_text("unsaved change")
        with self.assertRaisesRegex(RuntimeError, "dirty working tree"):
            self.prepare()

    def test_previously_merged_candidate_does_not_open_an_empty_pr(self):
        self.git("switch", "official")
        self.commit("kext.zip", "new payload")
        self.git("switch", "main")
        self.prepare()
        self.git("branch", "saved-candidate")
        self.git("switch", "main")
        self.git("merge", "--ff-only", "saved-candidate")
        self.git("branch", "-D", sync.BRANCH)
        self.assertIsNone(self.prepare("saved-candidate"))
        self.assertEqual(self.git("branch", "--show-current"), "main")
