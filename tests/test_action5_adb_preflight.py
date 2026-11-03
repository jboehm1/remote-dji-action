"""Fully simulated host tests; never invoke ADB or a connected camera."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from action5_adb_preflight import KNOWN_HASHES, SERVICES, check


def simulation(root=True, mismatch=False, missing=False):
    calls = []

    def run(args):
        calls.append(tuple(args))
        if args == ["get-state"]:
            return (1, "") if missing else (0, "device")
        if args == ["shell", "id", "-u"]:
            return 0, "0" if root else "2000"
        if args == ["shell", "uname", "-m"]:
            return 0, "aarch64"
        if args == ["shell", "cat", "/build.prop"]:
            return 0, "ro.product.name=qcs8550_ac204\nsecret.another=value\n"
        if args[:3] == ["shell", "sha256sum", args[-1]] and args[-1] in KNOWN_HASHES:
            sha = KNOWN_HASHES[args[-1]]
            if mismatch and args[-1].endswith("client.so"):
                sha = "0" * 64
            return 0, sha + "  " + args[-1]
        if args[:3] == ["shell", "systemctl", "is-active"] and args[-1] in SERVICES:
            return 0, "active"
        raise AssertionError("unexpected command " + repr(args))

    return run, calls


class PreflightTests(unittest.TestCase):
    def test_exact_fingerprint_matching(self):
        run, calls = simulation()
        result = check("FAKE_SERIAL_01", run)
        self.assertEqual(result["result"], "fingerprints_match_only")
        self.assertEqual(len(result["files"]), len(KNOWN_HASHES))
        self.assertNotIn("secret", str(result))
        self.assertFalse(any("push" in x or "reboot" in x for args in calls for x in args))

    def test_mismatch_is_blocked(self):
        run, _ = simulation(mismatch=True)
        self.assertEqual(check("FAKE_SERIAL_01", run)["result"], "blocked")

    def test_no_root_ends_before_hashes(self):
        run, calls = simulation(root=False)
        self.assertIn("root ADB", check("FAKE_SERIAL_01", run)["reason"])
        self.assertFalse(any("sha256sum" in args for args in calls))

    def test_device_missing(self):
        run, calls = simulation(missing=True)
        self.assertEqual(check("FAKE_SERIAL_01", run)["result"], "blocked")
        self.assertEqual(calls, [("get-state",)])

    def test_serial_validation(self):
        run, _ = simulation()
        with self.assertRaises(ValueError):
            check("../../;reboot", run)


if __name__ == "__main__":
    unittest.main()
