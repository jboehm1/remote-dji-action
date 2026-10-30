#!/usr/bin/env python3
"""Offline synthetic regression fixtures; never contain real camera logs."""
from __future__ import annotations
import sys
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from inspect_mimo_apk import inspect, dex_strings
from duml_topic_audit import (
    byte_diffs, changed_topic_values, decode_property, summarize_capture
)
from mimo_action6 import encode_duml_frame


def make_dex_string_fixture() -> bytes:
    texts = [b"cam_lapse_param", b"gui_autorecord_param",
             b"camcap_timelapse_duration", b"18000"]
    dex = bytearray(112)
    dex[:8] = b"dex\n035\x00"
    struct.pack_into("<II", dex, 56, len(texts), 112)
    dex.extend(bytes(4 * len(texts)))
    for i, item in enumerate(texts):
        pos = len(dex)
        struct.pack_into("<I", dex, 112 + 4 * i, pos)
        # <=127 UTF-16 characters; ASCII fixture only
        dex.extend(bytes([len(item)]) + item + b"\x00")
    return bytes(dex)


def push_topic(name: str, value: bytes) -> bytes:
    nb = name.encode("ascii")
    payload = (
        b"\x02\x06\x00\x00" + bytes(9) + len(nb).to_bytes(2, "little")
        + nb + bytes(6) + len(value).to_bytes(2, "little") + value
    )
    return encode_duml_frame(0, 0x99, payload, sender=0x28, receiver=2,
                             flags=0x40)


class MimoNativeSettingsTests(unittest.TestCase):
    def test_direct_dex_string_index(self):
        extracted = list(dex_strings(make_dex_string_fixture()))
        self.assertEqual([item for _, item in extracted], [
            "cam_lapse_param", "gui_autorecord_param",
            "camcap_timelapse_duration", "18000"
        ])

    def test_apk_reads_dex_without_decompiler(self):
        with tempfile.TemporaryDirectory() as root:
            apk = Path(root) / "dji.mimo.test.apk"
            with zipfile.ZipFile(apk, "w") as z:
                z.writestr("classes.dex", make_dex_string_fixture())
            results = inspect(apk)
            self.assertEqual(results["dex_files"], 1)
            self.assertEqual(results["match_counts"]["gui_autorecord_param"], 1)
            self.assertEqual(results["match_counts"]["camcap_timelapse_duration"], 1)

    def test_native_elf_strings_are_included(self):
        with tempfile.TemporaryDirectory() as root:
            apk = Path(root) / "mimo.with.native.apk"
            with zipfile.ZipFile(apk, "w") as z:
                z.writestr("lib/arm64-v8a/libcontrol.so",
                           b"ELF" + bytes(130) +
                           b"gui_autorecord_param\x00" +
                           b"camcap_timelapse_duration\x00")
            found = inspect(apk)
            self.assertIn("gui_autorecord_param", found["match_counts"])
            self.assertIn("camcap_timelapse_duration", found["match_counts"])

    def test_named_push_21_byte_setting(self):
        frame = push_topic("gui_autorecord_param", bytes.fromhex("00 10 0e 00 00"))
        summary = summarize_capture(frame)
        self.assertIn("gui_autorecord_param", summary["all_named_topic_names"])
        self.assertEqual(summary["target_observations"]["gui_autorecord_param"][0]["data_hex"],
                         "00 10 0e 00 00")

    def test_subscribe_variant_namelen_at_15(self):
        sample = bytes.fromhex(
            "02 02 00 00 df 69 00 00 00 00 00 00 1a 00 00 0a 00"
        ) + b"cam_status" + bytes(12)
        self.assertEqual(decode_property(sample)["name"], "cam_status")

    def test_3h_to_5h_synthetic_diff_does_not_assume_semantics(self):
        def bundle(seconds: int) -> dict:
            # Synthetic made-up value format, NOT an observed DJI command.
            return summarize_capture(push_topic(
                "gui_autorecord_param", struct.pack("<I", seconds)))
        delta = changed_topic_values(bundle(10800), bundle(18000))
        item = delta["gui_autorecord_param"]
        self.assertEqual(item["old_only"], ["30 2a 00 00"])
        self.assertEqual(item["new_only"], ["50 46 00 00"])
        self.assertTrue(item["changed_byte_offsets"])

    def test_byte_diffs(self):
        self.assertEqual([x["offset"] for x in byte_diffs(b"abc", b"aXd")], [1, 2])

    def test_wrong_00_99_payload_is_not_fabricated(self):
        self.assertIsNone(decode_property(b"\x02\x06" + bytes(6)))
        self.assertEqual(summarize_capture(bytes(100))["frames_checked"], 0)


if __name__ == "__main__":
    unittest.main()
