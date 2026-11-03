"""Host-only regression tests with generated synthetic binaries, no DJI IP."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from scan_osmo_native import collect_paths, scan_constants, scan_file, scan_string_hints


class NativeScanTests(unittest.TestCase):
    def test_ascii_and_utf16_offset(self):
        blob = b"\x00foo cam_lapse_param\x00" + b"timer shooting".decode().encode("utf-16le")
        hints = scan_string_hints(blob)
        self.assertEqual([(h["keyword"], h["encoding"]) for h in hints],
                         [("cam_lapse_param", "ascii"), ("timer shooting", "utf-16le")])
        self.assertEqual(hints[0]["offset"], 5)
        self.assertEqual(hints[1]["offset"], 21)

    def test_duration_matches_do_not_claim_validation(self):
        blob = b"native_timer_shoot\x00" + b"z" * 70 + (18000).to_bytes(4, "little")
        blob += b"z" * 20 + (36000).to_bytes(4, "little")
        literal = scan_constants(blob, scan_string_hints(blob))
        self.assertEqual(literal["5h"]["total_raw_occurrences"], 1)
        self.assertEqual(literal["10h"]["occurrences_within_8k_of_hint"], 1)
        self.assertEqual(literal["8h"]["total_raw_occurrences"], 0)

    def test_distant_unrelated_int_not_ranked_near(self):
        blob = b"timelapse" + b"z" * 10000 + (28800).to_bytes(4, "little")
        literal = scan_constants(blob, scan_string_hints(blob))
        self.assertEqual(literal["8h"]["total_raw_occurrences"], 1)
        self.assertEqual(literal["8h"]["occurrences_within_8k_of_hint"], 0)

    def test_symlinks_not_followed_and_hash_emitted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            file = folder / "module.so"
            file.write_bytes(b"\x7fELF" + b"schedule")
            (folder / "external.so").symlink_to(file)
            paths, skipped = collect_paths(folder)
            self.assertEqual(paths, [file])
            self.assertEqual(skipped, [])
            self.assertEqual(scan_file(file)["format"], "ELF")
            self.assertEqual(len(scan_file(file)["sha256"]), 64)

    def test_cli_valid_json_and_no_output_files(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "sample.bin"
            file.write_bytes(b"timer shooting\x00" + (36000).to_bytes(4, "little"))
            script = Path(__file__).resolve().parents[1] / "tools" / "scan_osmo_native.py"
            result = subprocess.run([sys.executable, str(script), str(file)],
                                    check=True, capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertEqual(report["mode"], "offline-read-only")
            self.assertEqual(report["files"][0]["duration_literals"]["10h"]["total_raw_occurrences"], 1)
            self.assertEqual([p.name for p in Path(temp).iterdir()], ["sample.bin"])


if __name__ == "__main__":
    unittest.main()
