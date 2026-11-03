"""Offline end-to-end policy tests. No DJI camera or BLE device is used."""

from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.osmo_pi import (ControlError, atomic_save, hhmm, load_state, parse_days,
                           record_state, session_for, tick, verify_status)


def status(*, recording=False, mode=2, duration=0, fresh=True,
           model="Osmo Action 5 Pro", free=3000, connected=True):
    return {
        "connected": connected, "fresh": fresh, "link": "on", "active": {"model": model},
        "capture_mode": mode, "record": {"state": "recording" if recording else "idle"},
        "lapse": {"duration": duration}, "storage": {"free_mb": free},
    }


class FakeClient:
    def __init__(self, state):
        self.current = state
        self.requests = []

    def status(self):
        return self.current

    def command(self, path):
        self.requests.append(path)
        self.current["record"]["state"] = "recording" if path.endswith("start") else "idle"
        return {"ok": True}


class RaspberrySchedulerTests(unittest.TestCase):
    def setUp(self):
        self.days = set(range(7))
        self.zone = ZoneInfo("Europe/Berlin")
        self.state = {"session": None, "attempts": 0, "maybe_ours": False}

    def when(self, day, hour, minute=0):
        return dt.datetime(2026, 11, day, hour, minute, tzinfo=self.zone)

    def decide(self, client, day, hour, minute=0, *, dry_run=False):
        return tick(client, self.state, now=self.when(day, hour, minute),
                    start=8 * 60, end=18 * 60, days=self.days,
                    model="Osmo Action 5 Pro", assume_infinite=False,
                    dry_run=dry_run)

    def test_start_and_stop_only_when_owned(self):
        client = FakeClient(status())
        self.assertEqual(self.decide(client, 3, 7), "hold: outside schedule")
        self.assertEqual(self.decide(client, 3, 8), "START")
        self.assertTrue(self.state["maybe_ours"])
        self.assertEqual(self.state["attempts"], 1)
        client.command("/api/record/start")
        self.assertEqual(self.decide(client, 3, 9), "hold: already recording")
        self.assertEqual(self.decide(client, 3, 18), "STOP")
        client.command("/api/record/stop")
        self.assertEqual(self.decide(client, 3, 18), "clear: owned recording already idle")

    def test_manual_recording_never_stopped(self):
        client = FakeClient(status(recording=True))
        self.assertEqual(self.decide(client, 3, 18), "hold: outside schedule")
        self.assertEqual(self.decide(client, 3, 9), "hold: already recording")
        self.assertFalse(self.state["maybe_ours"])

    def test_missing_camera_or_stale_status_fails_closed(self):
        for kwargs in ({"connected": False}, {"fresh": False},
                       {"mode": 1}, {"model": "Osmo Action 4"}):
            with self.subTest(kwargs=kwargs):
                client = FakeClient(status(**kwargs))
                self.assertTrue(self.decide(client, 3, 8).startswith("hold:"))
                self.assertFalse(self.state["maybe_ours"])

    def test_finite_duration_blocks_recording(self):
        client = FakeClient(status(duration=18000))
        self.assertIn("not confirmed at infinity", self.decide(client, 3, 8))

    def test_low_storage_blocks_recording(self):
        client = FakeClient(status(free=500))
        self.assertIn("insufficient", self.decide(client, 3, 8))

    def test_no_retries_after_budget(self):
        client = FakeClient(status())
        self.decide(client, 3, 8)
        self.decide(client, 3, 8, 1)
        self.assertIn("retry budget", self.decide(client, 3, 8, 2))

    def test_dry_run_never_takes_ownership(self):
        client = FakeClient(status())
        self.assertEqual(self.decide(client, 3, 8, dry_run=True), "dry-run: would START")
        self.assertFalse(self.state["maybe_ours"])

    def test_overnight_and_weekdays(self):
        mon_only = {0}
        self.assertIsNone(session_for(self.when(3, 22), 23 * 60, 2 * 60, mon_only))
        monday = dt.datetime(2026, 11, 2, 23, 0, tzinfo=self.zone)
        tuesday = dt.datetime(2026, 11, 3, 1, 59, tzinfo=self.zone)
        self.assertEqual(session_for(monday, 23 * 60, 2 * 60, mon_only), "2026-11-02")
        self.assertEqual(session_for(tuesday, 23 * 60, 2 * 60, mon_only), "2026-11-02")
        self.assertIsNone(session_for(tuesday.replace(hour=2), 23 * 60, 2 * 60, mon_only))

    def test_fall_dst_repeated_hour_same_session(self):
        before = dt.datetime(2026, 10, 25, 2, 30, fold=0, tzinfo=self.zone)
        after = before.replace(fold=1)
        self.assertEqual(session_for(before, 60, 4 * 60, self.days), "2026-10-25")
        self.assertEqual(session_for(after, 60, 4 * 60, self.days), "2026-10-25")

    def test_state_persists_and_malformed_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state.json"
            atomic_save(path, {"session": "2026-11-03", "attempts": 1, "maybe_ours": True})
            self.assertTrue(load_state(path)["maybe_ours"])
            path.write_text("truncated", encoding="utf-8")
            with self.assertRaises(ControlError):
                load_state(path)

    def test_manual_status_safety(self):
        with self.assertRaises(ControlError):
            verify_status(status(mode=1))
        with self.assertRaises(ControlError):
            verify_status(status(duration=5), must_be_infinite=True)
        self.assertEqual(record_state(status(recording=True)), "recording")

    def test_validators(self):
        self.assertEqual(hhmm("08:30"), 510)
        self.assertEqual(parse_days("mon,tue"), {0, 1})
        with self.assertRaises(Exception):
            hhmm("28:99")
        with self.assertRaises(Exception):
            parse_days("turtle")


if __name__ == "__main__":
    unittest.main()
