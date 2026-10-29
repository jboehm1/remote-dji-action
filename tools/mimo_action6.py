#!/usr/bin/env python3
"""Offline DJI Mimo/Action 6 DUML investigator (no camera connections).

Built from independently documented Action 6 captures: OpenPocketCine
physical survey 2026-09-21, and Osmo Client protocol notes.
This NEVER transmits a command, edits firmware, or changes a camera.

Examples:
  python tools/mimo_action6.py proposal --interval 10 --hours 8
  python tools/mimo_action6.py readback --hex "00 64 00 05 00 80 70 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
  python tools/mimo_action6.py capabilities --hex "09 00 00 00 00 2c 01 00 00 ..."
  python tools/mimo_action6.py scan trace.bin

DUML parser intentionally prints only (02,6C) Timelapse settings; other
frames may contain private device IDs or Wi-Fi credentials.
"""
from __future__ import annotations

import argparse
import json
import struct
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

ADVERTISED_DURATIONS_S = (0, 300, 600, 1200, 1800, 3600, 7200, 10800, 18000)
SAVE_FORMATS = {0: "Video", 2: "JPEG+Video", 3: "RAW+Video"}
HEADER_LENGTH = 11
FRAME_OVERHEAD = 13


def crc8(data: bytes, start: int = 0x77) -> int:
    value = start
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value >> 1) ^ (0x8C if value & 1 else 0)) & 0xFF
    return value


def crc16(data: bytes, start: int = 0x3692) -> int:
    value = start
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = ((value >> 1) ^ (0x8408 if value & 1 else 0)) & 0xFFFF
    return value


def parse_hex(value: str) -> bytes:
    """Strictly accept plain hex with spaces, colons or 0x prefixes."""
    s = value.replace("0x", "").replace("0X", "").replace(":", "").replace(" ", "")
    if len(s) % 2:
        raise ValueError("hex must contain whole bytes")
    try:
        return bytes.fromhex(s)
    except ValueError as exc:
        raise ValueError("invalid hex") from exc


def make_timelapse_payload(interval_seconds: str, duration_seconds: int,
                           save: int = 0) -> bytes:
    if save not in SAVE_FORMATS:
        raise ValueError("unsupported save format")
    try:
        ten_ticks = Decimal(interval_seconds) * 10
    except InvalidOperation as exc:
        raise ValueError("interval must be numeric") from exc
    if ten_ticks != ten_ticks.to_integral_value() or not 1 <= ten_ticks <= 65535:
        raise ValueError("interval must fit unsigned 16-bit tenths of second")
    if not 0 <= duration_seconds <= 0xFFFFFFFF:
        raise ValueError("duration must fit unsigned 32-bit seconds")
    return struct.pack("<BBBHI7x", 4, 0, save, int(ten_ticks), duration_seconds)


def decode_timelapse_payload(data: bytes) -> dict:
    if len(data) != 16 or data[:2] != b"\x04\x00":
        raise ValueError("not a 16-byte Timelapse 02/6C settings body")
    if data[9:] != bytes(7):
        raise ValueError("unexpected nonzero reserved trailer; new format?")
    save = data[2]
    interval_ticks = int.from_bytes(data[3:5], "little")
    seconds = int.from_bytes(data[5:9], "little")
    return {
        "save_code": save,
        "save_format": SAVE_FORMATS.get(save, "UNKNOWN"),
        "interval_seconds": interval_ticks / 10,
        "duration_seconds": seconds,
        "duration_hours": seconds / 3600,
        "advertised_in_2026_09_capture": seconds in ADVERTISED_DURATIONS_S,
        "supported_on_camera": "NOT VERIFIED by encoding",
    }


def decode_cam_lapse_param(body: bytes) -> dict:
    """Parse 21-byte *topic data* (not full 00/99 topic wrapper)."""
    if len(body) != 21:
        raise ValueError("cam_lapse_param state data must be exactly 21 bytes")
    return {
        "save_code": body[0],
        "interval_seconds": int.from_bytes(body[1:3], "little") / 10,
        "minimum_interval_seconds": int.from_bytes(body[3:5], "little") / 10,
        "duration_seconds": int.from_bytes(body[5:9], "little"),
        "hyperlapse_ratio": int.from_bytes(body[9:11], "little"),
        "secondary_ratio": int.from_bytes(body[11:13], "little"),
        "running_seconds_correlated_counter": int.from_bytes(body[13:17], "little"),
        "output_correlated_counter": int.from_bytes(body[17:21], "little"),
        "notice": "Counters' units not independently verified; readback alone not proof of full recording.",
    }


def decode_count_prefixed_durations(data: bytes) -> list[int]:
    """Parse NORMALIZED count:u8 + N x u32-LE seconds (not complete 00/99 wrapper)."""
    if not data or len(data) != 1 + data[0] * 4:
        raise ValueError("expect count byte followed by exactly count*4 bytes")
    return list(struct.unpack("<" + "I" * data[0], data[1:]))


def scan_duml_frames(blob: bytes) -> Iterator[dict]:
    """Validate 0x55 DUML frames embedded in opaque bytes (UDP wrapper, HCI, etc.).

    This scanner cannot reassemble frames split across packets, and should NOT
    be used to infer absence of commands from an incomplete capture.
    """
    i = 0
    end = len(blob)
    while i + FRAME_OVERHEAD <= end:
        if blob[i] != 0x55 or (blob[i + 2] >> 2) != 1:
            i += 1
            continue
        length = blob[i + 1] | ((blob[i + 2] & 0x03) << 8)
        if length < FRAME_OVERHEAD or i + length > end:
            i += 1
            continue
        frame = blob[i:i + length]
        if (crc8(frame[:3]) != frame[3] or
                crc16(frame[:-2]) != int.from_bytes(frame[-2:], "little")):
            i += 1
            continue
        yield {
            "offset": i, "sender": frame[4], "receiver": frame[5],
            "sequence_raw_le": int.from_bytes(frame[6:8], "little"),
            "flags": frame[8], "cmd_set": frame[9], "cmd_id": frame[10],
            "body": frame[11:-2],
        }
        i += length


def summarize_lapse_frames(blob: bytes) -> list[dict]:
    results = []
    for frame in scan_duml_frames(blob):
        # Ignore all other commands: some include names, credentials or token data.
        if (frame["cmd_set"], frame["cmd_id"]) != (0x02, 0x6C):
            continue
        result = {"offset": frame["offset"], "flags": frame["flags"],
                  "sender": frame["sender"], "receiver": frame["receiver"],
                  "body_length": len(frame["body"])}
        if frame["flags"] == 0x40 and len(frame["body"]) == 16:
            try:
                result["timelapse"] = decode_timelapse_payload(frame["body"])
            except ValueError:
                result["kind"] = "non-Timelapse variant or unqualified 02/6C"
        elif frame["flags"] in (0x80, 0xC0):
            # A response '00' alone is not enough: verify 00/99 state readback.
            result["ack_result"] = frame["body"][0] if frame["body"] else None
        results.append(result)
    return results


def cli() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    prop = sub.add_parser("proposal", help="encode settings *body*, never send")
    prop.add_argument("--interval", default="10", help="seconds, 0.1s steps")
    prop.add_argument("--hours", type=Decimal, default=Decimal(8))
    prop.add_argument("--save", choices=sorted(SAVE_FORMATS), type=int, default=0)
    read = sub.add_parser("readback", help="decode 21-byte cam_lapse_param *body*")
    read.add_argument("--hex", required=True)
    cap = sub.add_parser("capabilities", help="decode normalized count+u32 duration list")
    cap.add_argument("--hex", required=True)
    scan = sub.add_parser("scan", help="find CRC-verified 02/6C in opaque binary capture")
    scan.add_argument("file", type=Path)
    args = ap.parse_args()
    if args.command == "proposal":
        seconds = args.hours * 3600
        if not seconds.is_finite() or seconds != seconds.to_integral_value():
            ap.error("hours must resolve to a finite whole number of seconds")
        body = make_timelapse_payload(args.interval, int(seconds), args.save)
        print(json.dumps({"payload_hex": body.hex(" "),
                          "interpretation": decode_timelapse_payload(body),
                          "transmitted": False}, indent=2))
    elif args.command == "readback":
        print(json.dumps(decode_cam_lapse_param(parse_hex(args.hex)), indent=2))
    elif args.command == "capabilities":
        values = decode_count_prefixed_durations(parse_hex(args.hex))
        print(json.dumps({"seconds": values, "match_action6_survey":
                          tuple(values) == ADVERTISED_DURATIONS_S}, indent=2))
    else:
        data = args.file.read_bytes()
        print(json.dumps({"bytes_scanned": len(data),
                          "matching_02_6c": summarize_lapse_frames(data),
                          "warning": "Opaque scan does not reassemble split DUML frames."}, indent=2))


if __name__ == "__main__":
    cli()
