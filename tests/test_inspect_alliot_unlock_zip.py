import importlib.util
import pathlib
import tempfile
import unittest
import zipfile


SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "tools" / "inspect_alliot_unlock_zip.py"
spec = importlib.util.spec_from_file_location("inspect_alliot_unlock_zip", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StaticZipInspectorTests(unittest.TestCase):
    def test_manifest_and_text_without_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = pathlib.Path(tmp) / "dummy.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("notes/readme.txt", "sample text")
                archive.writestr("bin/loader.bin", b"\x7fELF\x02\x01test")
            report = module.analyze(archive_path, expected_sha256=None, preview=True)
            self.assertEqual(report["entry_count"], 2)
            self.assertEqual(report["entries"][0]["preview"], "sample text")
            self.assertEqual(report["entries"][1]["magic_hex"].split()[:4], ["7f", "45", "4c", "46"])
            self.assertIsNone(report["sha256_matches"])
            self.assertFalse((pathlib.Path(tmp) / "notes").exists())

    def test_unsafe_path_is_flagged_not_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "dummy.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../../bad.sh", "echo bad")
            report = module.analyze(path, expected_sha256=None)
            self.assertTrue(report["entries"][0]["unsafe_path"])
            self.assertTrue(report["warnings"])

    def test_wrong_pinned_hash_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "dummy.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("ok.txt", "OK")
            report = module.analyze(path)
            self.assertFalse(report["sha256_matches"])
            self.assertTrue(any("MISMATCH" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
