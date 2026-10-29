#!/usr/bin/env python3
"""Offline-only regression tests for Action 6 Mimo evidence decoding."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mimo_action6 as mimo


class MimoAction6Tests(unittest.TestCase):
    def test_external_crc_golden_frame(self):
        # OpenPocketCine open-source selftest: valid 02/0C DUML frame.
        gold = bytes.fromhex("55 11 04 92 02 01 00 a0 40 02 0c 01 01 00 01 b6 3b")
        messages = list(mimo.scan_duml_frames(b"XXXX" + gold + b"YY"))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["offset"], 4)
        self.assertEqual((messages[0]["cmd_set"], messages[0]["cmd_id"]), (2, 12))
        self.assertEqual(messages[0]["body"], b"\x01\x01\x00\x01")
        self.assertEqual(mimo.crc8(gold[:3]), 0x92)
        self.assertEqual(mimo.crc16(gold[:-2]), 0x3BB6)

    def test_proposal_eight_hours(self):
        body = mimo.make_timelapse_payload("10", 8 * 3600)
        self.assertEqual(body.hex(" "), "04 00 00 64 00 80 70 00 00 00 00 00 00 00 00 00")
        parsed = mimo.decode_timelapse_payload(body)
        self.assertEqual(parsed["duration_hours"], 8)
        self.assertFalse(parsed["advertised_in_2026_09_capture"])
        self.assertEqual(parsed["supported_on_camera"], "NOT VERIFIED by encoding")

    def test_observed_exact_lapse_example(self):
        # Action 6 OpenPocketCine observed request in T13 for Video 2s / 600s.
        body = bytes.fromhex("04 00 00 14 00 58 02 00 00 00 00 00 00 00 00 00")
        parsed = mimo.decode_timelapse_payload(body)
        self.assertEqual(parsed["interval_seconds"], 2)
        self.assertEqual(parsed["duration_seconds"], 600)
        self.assertTrue(parsed["advertised_in_2026_09_capture"])

    def test_cam_lapse_state_21_bytes(self):
        state = bytes.fromhex("00 64 00 05 00 80 70 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
        self.assertEqual(mimo.decode_cam_lapse_param(state)["duration_seconds"], 28800)
        self.assertEqual(mimo.decode_cam_lapse_param(state)["minimum_interval_seconds"], 0.5)

    def test_capabilities_observed_list(self):
        import struct
        cap = bytes([9]) + struct.pack("<9I", *mimo.ADVERTISED_DURATIONS_S)
        self.assertEqual(tuple(mimo.decode_count_prefixed_durations(cap)),
                         mimo.ADVERTISED_DURATIONS_S)

    def test_unknown_reserved_rejected(self):
        bad = bytearray(mimo.make_timelapse_payload("2", 300))
        bad[-1] = 1
        with self.assertRaises(ValueError):
            mimo.decode_timelapse_payload(bytes(bad))

    def test_scan_rejects_invalid_crc(self):
        good = bytearray.fromhex("55 11 04 92 02 01 00 a0 40 02 0c 01 01 00 01 b6 3b")
        good[11] ^= 1
        self.assertEqual(list(mimo.scan_duml_frames(bytes(good))), [])

    def test_rejects_unsupported_or_fractional_fields(self):
        for interval in ("0", "0.15", "6553.6", "-1"):
            with self.assertRaises(ValueError):
                mimo.make_timelapse_payload(interval, 300)
        with self.assertRaises(ValueError):
            mimo.make_timelapse_payload("10", -1)
        with self.assertRaises(ValueError):
            mimo.make_timelapse_payload("10", 100, save=1)

    def test_encode_frame_roundtrip_offline(self):
        body = mimo.make_timelapse_payload("10", 28800)
        frame = mimo.encode_duml_frame(2, 0x6C, body)
        self.assertEqual(len(frame), 29)
        self.assertEqual(frame[:3], bytes([0x55, 0x1D, 0x04]))
        got = list(mimo.scan_duml_frames(frame))
        self.assertEqual(len(got), 1)
        self.assertEqual((got[0]["cmd_set"], got[0]["cmd_id"]), (2, 0x6C))
        self.assertEqual(got[0]["body"], body)
        matching = mimo.summarize_lapse_frames(frame)
        self.assertEqual(matching[0]["timelapse"]["duration_seconds"], 28800)

    def test_unlimited_is_zero_duration(self):
        payload = mimo.make_timelapse_payload("0.5", 0, save=2)
        parsed = mimo.decode_timelapse_payload(payload)
        self.assertEqual(parsed["duration_seconds"], 0)
        self.assertEqual(parsed["save_format"], "JPEG+Video")
        self.assertTrue(parsed["advertised_in_2026_09_capture"])


if __name__ == "__main__":
    unittest.main()
