#!/usr/bin/env python3
"""Offline code/strings investigator for a locally owned DJI Mimo APK.

This NEVER downloads an APK, transmits anything to a camera, patches an APK,
copies source code into this repo, or uploads proprietary assets. It indexes
only matching file paths and line numbers, never the matched content.

First use JADX locally:
  jadx --no-res -d local-private/mimo-jadx <YOUR_LOCAL_DJI_MIMO_APK>
Then:
  python3 tools/inspect_mimo_jadx.py local-private/mimo-jadx --json-out local-private/index.json

Counts and file/line references in JADX output can help identify the UI code
that enumerates durations and writes DUML 02/6C. A "Daily" resource may simply
be a DJI color mode, not a recurring scheduler.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

SEARCHES = {
    "lapse_capability": ["camcap_timelapse_duration", "cam_lapse_param"],
    "lapse_settings": ["timelapse_duration", "timelapseDuration", "lapseInterval"],
    "autorecord": ["gui_autorecord_param", "auto_record", "autoRecord"],
    "daily_schedule": ["repeat_daily", "repeatDaily", "scheduled_shooting",
                       "scheduledShooting", "RTC_ALARM", "RTC_WAKEUP",
                       "AlarmManager", "setExactAndAllowWhileIdle"],
    "duration_constants": ["18000", "28800", "21600", "36000", "43200"],
}
EXTENSIONS = {".java", ".kt", ".smali", ".xml", ".json", ".txt"}
MAX_FILE_BYTES = 12_000_000
MAX_HITS_PER_TERM = 1000


def inspect(root: Path) -> dict:
    if not root.is_dir():
        raise ValueError("Please supply an existing local JADX output directory")
    results = defaultdict(list)
    files = 0
    inspected = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        files += 1
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        rel = str(path.relative_to(root))
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                inspected += 1
                # Report file path and line, NOT proprietary matched source text.
                for group, terms in SEARCHES.items():
                    matches = [term for term in terms if term in line]
                    for term in matches:
                        key = group + "/" + term
                        if len(results[key]) < MAX_HITS_PER_TERM:
                            results[key].append({"file": rel, "line": lineno})
    return {"files_seen": files, "lines_checked": inspected, "matches": dict(results),
            "warning": "Matches are leads, not proof of camera-side scheduling."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--json-out", type=Path, help="write local index; do not commit raw APK")
    args = parser.parse_args()
    result = inspect(args.root)
    out = json.dumps(result, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(out + "\n", encoding="utf-8")
        print(f"Wrote {args.json_out} ({sum(map(len, result['matches'].values()))} hits)")
    else:
        print(out)


if __name__ == "__main__":
    main()
