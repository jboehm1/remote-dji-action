#!/usr/bin/env python3
"""Offline DJI Mimo 02/6C Timelapse *payload* encoder, NOT a transmitter.

Based on observed Action 6 Mimo protocol from OpenPocketCine's Sept 2026
device survey. This is not the official DJI GPS-remote command path.
The ability to encode an 8h value does NOT prove camera firmware accepts it.
"""
import argparse
import struct


def build_payload(interval_seconds: float, duration_seconds: int, save: int = 0) -> bytes:
    """16-byte mode-specific settings body: 04 00 SAVE INTERVAL_LE16 DURATION_LE32 +7 zeros."""
    if save not in (0, 2, 3):
        raise ValueError("save must be 0 (video), 2 (JPEG+video), or 3 (RAW+video)")
    ticks = round(interval_seconds * 10)
    if ticks <= 0 or ticks > 65535 or abs(ticks / 10 - interval_seconds) > 1e-8:
        raise ValueError("interval must be 0.1 second units within uint16")
    if duration_seconds < 0 or duration_seconds > 0xFFFFFFFF:
        raise ValueError("duration_seconds out of uint32 range")
    return struct.pack("<BBBHI7x", 4, 0, save, ticks, duration_seconds)


def test_vectors() -> None:
    eight_hours = build_payload(10, 8 * 3600)
    assert len(eight_hours) == 16
    assert eight_hours.hex(" ") == "04 00 00 64 00 80 70 00 00 00 00 00 00 00 00 00"
    assert build_payload(2, 0).hex(" ").startswith("04 00 00 14 00 00 00 00 00")
    try:
        build_payload(1, -1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative duration accepted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=10.0, help="interval in seconds")
    parser.add_argument("--hours", type=float, default=8.0, help="duration in hours (0 means infinity)")
    args = parser.parse_args()
    seconds = args.hours * 3600
    if not seconds.is_integer():
        parser.error("hours must resolve to integer seconds")
    test_vectors()
    b = build_payload(args.interval, int(seconds))
    print(b.hex(" "))
    print("Payload only, not a complete DUML frame. Camera acceptance is unverified.")
