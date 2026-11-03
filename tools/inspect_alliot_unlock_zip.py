#!/usr/bin/env python3
"""Read-only, static manifest for Alliot's Action 5 Pro unlock release ZIP.

Does NOT extract, run, decrypt, or modify any file. Intended for a downloaded
copy of the upstream release, never as an EDL/flash/unlock implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import sys
import zipfile


EXPECTED_SHA256 = "995315621279cbff1a37690ddc98b0ea6732125403b001f4c9e59828b7fe81cd"
MAX_ENTRY = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".sh", ".bat", ".cmd", ".ps1", ".xml", ".json", ".ini", ".cfg", ".conf", ".py"}


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(path: pathlib.Path, *, expected_sha256: str | None = EXPECTED_SHA256,
            preview: bool = False) -> dict:
    result = {"archive": str(path), "archive_size": path.stat().st_size,
              "sha256": file_sha256(path), "expected_sha256": expected_sha256,
              "sha256_matches": None, "entries": [], "warnings": []}
    if expected_sha256:
        result["sha256_matches"] = result["sha256"].lower() == expected_sha256.lower()
        if not result["sha256_matches"]:
            result["warnings"].append("ARCHIVE HASH MISMATCH: do not trust as pinned upstream asset")

    total_uncompressed = 0
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            name = info.filename
            posix = pathlib.PurePosixPath(name.replace("\\", "/"))
            is_symlink = stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)
            path_unsafe = posix.is_absolute() or ".." in posix.parts or "\x00" in name
            encrypted = bool(info.flag_bits & 1)
            total_uncompressed += info.file_size
            record = {
                "name": name, "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size, "crc32": f"{info.CRC:08x}",
                "is_directory": info.is_dir(), "is_symlink": is_symlink,
                "unsafe_path": path_unsafe, "encrypted": encrypted,
                "entry_sha256": None, "magic_hex": None, "preview": None,
            }
            if path_unsafe or is_symlink:
                result["warnings"].append(f"Dangerous archive path/type: {name!r}")
            if encrypted:
                result["warnings"].append(f"Encrypted archive entry (not decrypted): {name!r}")
            if info.file_size > MAX_ENTRY or total_uncompressed > MAX_TOTAL:
                result["warnings"].append(f"Size limit exceeded; not reading entry: {name!r}")
            elif not (info.is_dir() or encrypted):
                digest = hashlib.sha256()
                prefix = bytearray()
                with archive.open(info, "r") as stream:
                    for chunk in iter(lambda: stream.read(64 * 1024), b""):
                        digest.update(chunk)
                        if len(prefix) < 4096:
                            prefix.extend(chunk[:4096 - len(prefix)])
                record["entry_sha256"] = digest.hexdigest()
                record["magic_hex"] = prefix[:16].hex(" ")
                if preview and pathlib.PurePosixPath(name).suffix.lower() in TEXT_SUFFIXES:
                    record["preview"] = bytes(prefix).decode("utf-8", errors="replace")
            result["entries"].append(record)
    result["total_uncompressed_bytes"] = total_uncompressed
    result["entry_count"] = len(result["entries"])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=pathlib.Path, help="Local ZIP file (read-only)")
    parser.add_argument("--preview-text", action="store_true", help="Include first 4096 bytes of text files in JSON")
    parser.add_argument("--no-pinned-hash", action="store_true", help="Allow inspecting a test/different ZIP")
    args = parser.parse_args(argv)
    try:
        report = analyze(args.archive, expected_sha256=None if args.no_pinned_hash else EXPECTED_SHA256,
                         preview=args.preview_text)
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        print(f"Cannot inspect ZIP: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["sha256_matches"] is not False and not report["warnings"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
