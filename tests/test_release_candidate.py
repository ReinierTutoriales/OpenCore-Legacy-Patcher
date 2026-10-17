"""Release checks must reject wrong provenance, altered bytes and incomplete uploads."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("publish_candidate", Path(__file__).resolve().parents[1] / "ci_tooling/publish_candidate.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in publish.PACKAGES:
            (self.root / name).write_bytes(name.encode())
        (self.root / "build-provenance.json").write_text(json.dumps({"commit": "a" * 40, "versions": {"patcher_version": "3.0.0-rc.3"}}))
        (self.root / "resolved-dependencies.txt").write_text("dependencies")
        self.sums = self.root / "SHA256SUMS.txt"
        self.sums.write_text("".join(publish.digest(self.root / name).split(":")[1] + "  dist/" + name + "\n" for name in publish.PACKAGES))

    def validate(self):
        return publish.validate_files(self.root, "a" * 40, "3.0.0-rc.3")

    def test_verified_packages_and_metadata_are_all_included(self):
        self.assertEqual(set(self.validate()), set(publish.PACKAGES + publish.INFO))

    def test_wrong_source_commit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            publish.validate_files(self.root, "b" * 40, "3.0.0-rc.3")

    def test_modified_package_is_rejected(self):
        (self.root / publish.PACKAGES[0]).write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.validate()

    def test_missing_package_checksum_is_rejected(self):
        self.sums.write_text("\n".join(self.sums.read_text().splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError, "three package"):
            self.validate()

    def test_duplicate_checksum_is_rejected(self):
        self.sums.write_text(self.sums.read_text() + self.sums.read_text().splitlines()[0] + "\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.validate()

    def test_server_asset_bytes_must_match_before_publication(self):
        expected = self.validate()
        assets = [{"name": name, **identity} for name, identity in expected.items()]
        publish.verify_assets({"assets": assets}, expected)
        assets[0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "Uploaded asset"):
            publish.verify_assets({"assets": assets}, expected)

    def test_created_draft_is_used_without_a_second_list_query(self):
        created = {"id": 123, "draft": True, "assets": []}
        with patch.object(publish, "command", return_value=json.dumps(created)) as command, patch.object(publish, "find_release", side_effect=AssertionError("must not relist")), patch.object(publish.Path, "read_text", return_value="release notes"):
            self.assertEqual(publish.create_release("owner/repo", "3.0.0-rc.3", "a" * 40), created)
        self.assertIn("POST", command.call_args.args)
