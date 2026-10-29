#!/usr/bin/env python3
"""OFFLINE inspect of a legitimately obtained DJI Mimo Android APK, no JADX needed.

Reads ZIP entries without installing the APK, extracting or publishing proprietary
DEX/APK files. Detects DEX string-table entries, ZIP asset filenames, and
resources.arsc string-pool entries. Reports ONLY keyword strings, field
provenance, and counts; no pairing data or phone secrets.

Example:
  python3 tools/inspect_mimo_apk.py /path/to/dji.mimo.apk --output local-private/mimo-audit.json

A match in the APK is evidence of an APP string, NOT a mapped DUML command
or evidence the CAMERA supports 8h Timer Shooting.
"""
from __future__ import annotations
import argparse
import json
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path

TARGETS = {
    "camcap_timelapse_duration", "cam_lapse_param", "gui_autorecord_param",
    "timer shooting", "scheduled shooting", "timelapse", "autorecord",
    "time lapse", "auto record", "timed recording", "repeat", "daily",
    "timer_shooting", "schedule_recording", "time_shoot",
}
# Numeric values may be DEX bytecode constants, not stored as strings; string
# search is not enough to demonstrate 18000 or 28800 validation semantics.
NUMERIC_AS_STRINGS = {"18000", "21600", "28800", "36000", "43200"}
MAX_UNCOMPRESSED = 160 * 1024 * 1024
MAX_STRINGS = 3_000_000
MAX_SHOW_PER_KEY = 40


def uleb128(b: bytes, pos: int) -> tuple[int, int]:
    number = 0
    for i in range(5):
        if pos >= len(b):
            raise ValueError("truncated ULEB")
        x = b[pos]
        pos += 1
        number |= (x & 127) << (7 * i)
        if not (x & 128):
            return number, pos
    raise ValueError("invalid ULEB")


def dex_strings(data: bytes):
    """Extract strings by DEX string_ids offsets; no bytecode execution."""
    if len(data) < 112 or not data.startswith(b"dex\n"):
        return
    if data[7] != 0:
        return
    count, offset = struct.unpack_from("<II", data, 56)
    if count > MAX_STRINGS or offset + 4 * count > len(data):
        return
    for index in range(count):
        (s_off,) = struct.unpack_from("<I", data, offset + 4 * index)
        if s_off >= len(data):
            continue
        try:
            _, pos = uleb128(data, s_off)
            end = data.find(b"\x00", pos, min(pos + 4097, len(data)))
            if end < 0:
                continue
            # Java modified UTF-8 differs slightly; text replacement is enough
            # to identify the ASCII protocol identifiers / English UI labels.
            yield index, data[pos:end].decode("utf-8", "replace")
        except ValueError:
            continue


def arsc_strings(data: bytes):
    """Find TYPE_STRING_POOL chunks, including nested RES_TABLE_PACKAGE pools.

    String pool header has 28 bytes, offsets array after header. Malformed
    chunk bounds are ignored rather than parsed past the section.
    """
    def walk(start: int, limit: int, level: int = 0):
        if level > 5:
            return
        off = start
        while off + 8 <= limit:
            typ, header_size, chunk_size = struct.unpack_from("<HHI", data, off)
            end = off + chunk_size
            if header_size < 8 or chunk_size < header_size or end > limit:
                break
            if typ == 0x0001 and header_size >= 28:
                num, _, flags, offset_strings = struct.unpack_from("<IIII", data, off + 8)
                is_utf8 = bool(flags & 0x100)
                if num <= MAX_STRINGS and off + header_size + num * 4 <= end:
                    for i in range(num):
                        rel = struct.unpack_from("<I", data, off + header_size + i*4)[0]
                        pos = off + offset_strings + rel
                        if not off <= pos < end:
                            continue
                        try:
                            if is_utf8:
                                # utf16 and UTF8 lengths each use 1 or 2 byte field
                                pos += 2 if data[pos] & 0x80 else 1
                                n = data[pos] & 0x7f
                                if data[pos] & 0x80:
                                    if pos + 1 >= end:
                                        continue
                                    n = (n << 8) | data[pos + 1]
                                    pos += 2
                                else:
                                    pos += 1
                                if n > 4096 or pos + n > end:
                                    continue
                                yield i, data[pos:pos+n].decode("utf-8", "replace")
                            else:
                                n = struct.unpack_from("<H", data, pos)[0]
                                pos += 2
                                if n & 0x8000:
                                    n = ((n & 0x7fff) << 16) | struct.unpack_from("<H", data, pos)[0]
                                    pos += 2
                                if n > 4096 or pos + 2 * n > end:
                                    continue
                                yield i, data[pos:pos+2*n].decode("utf-16-le", "replace")
                        except (IndexError, ValueError, struct.error):
                            continue
            if typ in (0x0002, 0x0200) and off + header_size < end:
                yield from walk(off + header_size, end, level + 1)
            off = end
    yield from walk(0, len(data))


def hits_for(value: str) -> list[str]:
    lower = value.lower()
    return sorted([term for term in TARGETS | NUMERIC_AS_STRINGS if term in lower])


def native_strings_scan(archive: zipfile.ZipFile, ent: zipfile.ZipInfo):
    """Match targeted ASCII tokens in ELF without extracting the binary.

    Limit to controlled string names and labels, not numeric byte patterns.
    This scans uncompressed ZIP entry chunks and handles boundary overlap.
    """
    needles = sorted(TARGETS - {"timelapse", "repeat", "daily"} |
                     {"camcap_timelapse_duration", "cam_lapse_param",
                      "gui_autorecord_param", "timer_shooting"}, key=len,
                     reverse=True)
    needles_b = [(name, name.encode("ascii")) for name in needles]
    tail = b""
    read_total = 0
    chunk_size = 1024 * 1024
    with archive.open(ent) as src:
        while read_total < MAX_UNCOMPRESSED:
            block = src.read(min(chunk_size, MAX_UNCOMPRESSED - read_total))
            if not block:
                break
            read_total += len(block)
            combined = (tail + block).lower()
            for name, pattern in needles_b:
                at = combined.find(pattern)
                if at >= 0:
                    yield (name, at + read_total - len(combined))
            tail = combined[-256:]


def inspect(apk: Path) -> dict:
    if not apk.is_file() or not zipfile.is_zipfile(apk):
        raise ValueError("Input must be a valid local APK/ZIP file")
    result = {
        "file_name": apk.name, "bytes": apk.stat().st_size,
        "observed": {}, "entries_checked": 0, "dex_files": 0,
        "remarks": [
            "A string match proves only inclusion in APK code or resources.",
            "18000 and 28800 may be bytecode numeric constants, absent from string tables.",
            "Mimo app controls may be separate from on-camera Timer Shooting UI.",
            "A scheduled-control command needs on-camera SET/ACK/GET validation.",
        ],
    }
    counters = Counter()
    out = {}
    with zipfile.ZipFile(apk) as archive:
        for ent in archive.infolist():
            if ent.is_dir():
                continue
            result["entries_checked"] += 1
            for target in hits_for(ent.filename):
                key = target
                counters[key] += 1
                if counters[key] <= MAX_SHOW_PER_KEY:
                    out.setdefault(key, []).append({"location": "apk-entry", "part": ent.filename})
            if ent.file_size > MAX_UNCOMPRESSED or ent.compress_size == 0:
                continue
            if re.fullmatch(r"classes\d*\.dex", Path(ent.filename).name):
                result["dex_files"] += 1
                parsed = dex_strings(archive.read(ent))
                label = "dex-string"
            elif ent.filename == "resources.arsc":
                parsed = arsc_strings(archive.read(ent))
                label = "resource-string"
            elif ent.filename.endswith(".so"):
                for term, off in native_strings_scan(archive, ent):
                    counters[term] += 1
                    if counters[term] <= MAX_SHOW_PER_KEY:
                        out.setdefault(term, []).append({
                            "location": "native-elf-string",
                            "part": ent.filename, "byte_offset": off,
                        })
                continue
            else:
                continue
            for idx, value in parsed:
                for target in hits_for(value):
                    counters[target] += 1
                    if counters[target] <= MAX_SHOW_PER_KEY:
                        out.setdefault(target, []).append({
                            "location": label, "part": ent.filename,
                            "string_index": idx,
                            "value": value[:180],
                        })
    result["match_counts"] = dict(counters)
    result["observed"] = out
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("apk", type=Path)
    ap.add_argument("--output", type=Path, help="write report locally, not to repository")
    args = ap.parse_args()
    data = json.dumps(inspect(args.apk), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data + "\n", encoding="utf-8")
        print(f"Report: {args.output}")
    else:
        print(data)


if __name__ == "__main__":
    main()
