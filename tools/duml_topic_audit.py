#!/usr/bin/env python3
"""Offline DJI named-property inspection for 00/99 traffic captures.

Investigate gui_autorecord_param WITHOUT asserting it means Timer Shooting.
Accepts an opaque file with embedded contiguous CRC-valid DUML frames.
No BLE/UDP transmission, no firmware changes. Logs only selected topic names
and 64-byte-or-smaller values. Raw capture must remain local/private.

Examples:
  python3 tools/duml_topic_audit.py topics capture-schedule-3h.bin
  python3 tools/duml_topic_audit.py diff 3hours.pcapng 5hours.pcapng
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from mimo_action6 import scan_duml_frames

KEY_TOPICS = {
    "gui_autorecord_param", "cam_lapse_param", "camcap_timelapse_duration",
    "cam_status", "cam_record_time", "cam_custom_mode_params",
}
MAX_CAPTURE_BYTES = 1024 * 1024 * 1024
MAX_EXAMPLES = 12


def decode_property(body: bytes) -> dict | None:
    """Best-effort decode two published 00/99 variants (subscriptions/pushes).

    For 02/06 pushes, name length is at body offset 13 and name at 15.
    Some 02/02 subscriptions use extra 2-byte prefix before name length.
    Return None for unknown structure, not a fabricated interpretation.
    """
    if len(body) < 19 or body[0] != 2 or body[1] not in (2, 6):
        return None
    kind = "push" if body[1] == 6 else "subscribe"
    for pos in (13, 15):
        if pos + 2 > len(body):
            continue
        n = int.from_bytes(body[pos:pos+2], "little")
        if not 3 <= n <= 80 or pos+2+n > len(body):
            continue
        name_bytes = body[pos+2:pos+2+n]
        if not all(32 <= x <= 126 for x in name_bytes):
            continue
        try:
            name = name_bytes.decode("ascii")
        except UnicodeDecodeError:
            continue
        if not (name.startswith(("cam", "gui_", "v_"))):
            continue
        tail = body[pos+2+n:]
        data = None
        if len(tail) >= 8 and tail[:6] == bytes(6):
            dlen = int.from_bytes(tail[6:8], "little")
            if 0 < dlen <= len(tail) - 8:
                data = tail[8:8+dlen]
        return {"name": name, "kind": kind, "data": data,
                "name_length_pos": pos}
    return None


def summarize_capture(blob: bytes) -> dict:
    result: dict = {"all_named_topic_names": {}, "target_observations": {},
                    "frames_checked": 0, "property_frames": 0}
    grouped: dict = {}
    for msg in scan_duml_frames(blob):
        result["frames_checked"] += 1
        if msg["cmd_set"] != 0 or msg["cmd_id"] != 0x99:
            continue
        prop = decode_property(msg["body"])
        if prop is None:
            continue
        result["property_frames"] += 1
        name = prop["name"]
        counts = result["all_named_topic_names"]
        counts[name] = counts.get(name, 0) + 1
        if name not in KEY_TOPICS:
            continue
        record = {
            "offset": msg["offset"], "kind": prop["kind"],
            "flags": msg["flags"],
            "data_bytes": len(prop["data"]) if prop["data"] is not None else None
        }
        if prop["data"] is not None and len(prop["data"]) <= 64:
            record["data_hex"] = prop["data"].hex(" ")
        group = grouped.setdefault(name, [])
        if len(group) < MAX_EXAMPLES:
            group.append(record)
    result["target_observations"] = grouped
    result["disclaimer"] = (
        "Names from traffic are not semantic proof. "
        "A GUI parameter can be about diving Auto Record rather than scheduling. "
        "Opaque scan omits DUML split across packet/capture boundaries.")
    return result


def byte_diffs(before: bytes, after: bytes) -> list[dict]:
    """Find changed offsets and four-byte little-endian candidate widths."""
    result = []
    for i in range(max(len(before), len(after))):
        x = before[i] if i < len(before) else None
        y = after[i] if i < len(after) else None
        if x != y:
            result.append({"offset": i, "old": x, "new": y})
    return result[:100]


def changed_topic_values(first: dict, second: dict) -> dict:
    changes = {}
    for key in KEY_TOPICS:
        a = {x["data_hex"] for x in first["target_observations"].get(key, [])
             if "data_hex" in x}
        b = {x["data_hex"] for x in second["target_observations"].get(key, [])
             if "data_hex" in x}
        if a or b:
            only_a, only_b = sorted(a - b), sorted(b - a)
            item = {"old_only": only_a, "new_only": only_b}
            if len(a) == len(b) == 1:
                ba = bytes.fromhex(next(iter(a)))
                bb = bytes.fromhex(next(iter(b)))
                item["changed_byte_offsets"] = byte_diffs(ba, bb)
            changes[key] = item
    return changes


def read_and_summarize(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_CAPTURE_BYTES:
        raise ValueError("file missing or larger than 1 GiB limit")
    return summarize_capture(path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("topics", help="extract public topic names and selected values")
    one.add_argument("capture", type=Path)
    both = sub.add_parser("diff", help="compare two isolated camera setting captures")
    both.add_argument("before", type=Path)
    both.add_argument("after", type=Path)
    args = parser.parse_args()
    if args.cmd == "topics":
        result = read_and_summarize(args.capture)
    else:
        before = read_and_summarize(args.before)
        after = read_and_summarize(args.after)
        result = {
            "before": args.before.name,
            "after": args.after.name,
            "new_topics": sorted(set(after["all_named_topic_names"]) -
                                 set(before["all_named_topic_names"])),
            "selected_value_changes": changed_topic_values(before, after),
            "caveat": "No matching transaction/clock semantics inferred from diffs alone.",
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
