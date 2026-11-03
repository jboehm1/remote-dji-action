#!/usr/bin/env python3
"""Offline, read-only triage of user-supplied Osmo native binaries.

This tool does not connect to a camera, modify firmware, or require root.
Its hints are deliberately weak evidence: a constant/string occurrence does
not establish which UI, scheduler, or validation path uses it.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")
UTF16LE_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")
HINTS = re.compile(
    r"time[ _-]?lapse|timer[ _-]?shoot(?:ing)?|time[ _-]?shoot(?:ing)?|"
    r"auto[ _-]?record|schedule|schedul|repeat|wake[ _-]?alarm|"
    r"rtc[ _-]?wake|gui_autorecord_param|camcap_timelapse_duration|"
    r"cam_lapse_param|duration",
    re.IGNORECASE,
)
SECONDS = {"3h": 10800, "5h": 18000, "8h": 28800, "10h": 36000}
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_FILES = 300
MAX_DISPLAY_HINTS = 100
MAX_DISPLAY_NEAR_CONSTANTS = 40
NEAR_WINDOW = 8192


def scan_string_hints(data: bytes) -> list[dict[str, object]]:
    """Report only matching keywords/offsets, not surrounding private text."""
    found: list[dict[str, object]] = []
    for regex, encoding in ((ASCII_RUN, "ascii"), (UTF16LE_RUN, "utf-16le")):
        for run in regex.finditer(data):
            raw = run.group()
            decoded = raw.decode("ascii" if encoding == "ascii" else "utf-16le")
            for match in HINTS.finditer(decoded):
                offset = run.start() + match.start() * (2 if encoding == "utf-16le" else 1)
                found.append({"offset": offset, "encoding": encoding, "keyword": match.group().lower()})
    return sorted(found, key=lambda item: (int(item["offset"]), str(item["keyword"])))


def scan_constants(data: bytes, hints: list[dict[str, object]]) -> dict[str, object]:
    """Look for LE32 duration literals near keyword strings; never infer use."""
    positions = [int(h["offset"]) for h in hints]
    results: dict[str, object] = {}
    for label, seconds in SECONDS.items():
        needle = struct.pack("<I", seconds)
        cursor, count, near = 0, 0, []
        while True:
            offset = data.find(needle, cursor)
            if offset == -1:
                break
            count += 1
            cursor = offset + 1
            idx = bisect.bisect_left(positions, offset)
            neighbors = []
            if idx < len(positions):
                neighbors.append(idx)
            if idx:
                neighbors.append(idx - 1)
            if neighbors:
                closest = min(neighbors, key=lambda i: abs(positions[i] - offset))
                distance = abs(positions[closest] - offset)
                if distance <= NEAR_WINDOW:
                    near.append({
                        "offset": offset,
                        "distance_to_hint": distance,
                        "hint": hints[closest]["keyword"],
                    })
        near.sort(key=lambda match: (int(match["distance_to_hint"]), int(match["offset"])))
        results[label] = {
            "seconds": seconds,
            "little_endian_hex": needle.hex(" "),
            "total_raw_occurrences": count,
            "occurrences_within_8k_of_hint": len(near),
            "nearest_examples": near[:MAX_DISPLAY_NEAR_CONSTANTS],
        }
    return results


def scan_file(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    hints = scan_string_hints(data)
    return {
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format": "ELF" if data.startswith(b"\x7fELF") else "other",
        "hint_count": len(hints),
        "hints": hints[:MAX_DISPLAY_HINTS],
        "hints_truncated": len(hints) > MAX_DISPLAY_HINTS,
        "duration_literals": scan_constants(data, hints),
    }


def collect_paths(root: Path) -> tuple[list[Path], list[dict[str, str]]]:
    if not root.exists():
        raise ValueError("input path does not exist")
    if root.is_symlink():
        raise ValueError("symlink input is not accepted")
    if not (root.is_file() or root.is_dir()):
        raise ValueError("input must be a regular file or directory")
    files = [root] if root.is_file() else sorted(root.rglob("*"))
    selected, skipped = [], []
    for path in files:
        if path.is_symlink() or not path.is_file():
            continue
        if len(selected) >= MAX_FILES:
            raise ValueError(f"more than {MAX_FILES} candidate files; narrow input")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            skipped.append({"file": str(path), "reason": "larger than 128 MiB"})
        else:
            selected.append(path)
    return selected, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="offline firmware file or extracted directory")
    args = parser.parse_args(argv)
    try:
        paths, skipped = collect_paths(args.path)
        root = args.path
        reports = []
        for path in paths:
            report = scan_file(path)
            report["file"] = str(path.relative_to(root)) if root.is_dir() else path.name
            reports.append(report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "warning": "Heuristic only; a match is NOT evidence of firmware acceptance or Timer Shooting ownership.",
        "mode": "offline-read-only",
        "files": reports,
        "skipped": skipped,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
