#!/usr/bin/env python3
"""Read-only Action 5 Pro root-ADB and Alliot ABI compatibility preflight.

No unlock, EDL, reboot, shell modification, pull, flash, install or writes.
The caller explicitly chooses a serial; no nearby/first device is guessed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Callable

PRODUCT = "qcs8550_ac204"
KNOWN_HASHES = {
    "/usr/lib/libdcam_camera_service_client.so": "98731a8252ee1d1e557af05e3369d33192b9c25142e97513c774f47c16bf27fa",
    "/usr/lib/libdcam_camera_service_server.so": "da7713234f19353054fd9faede2fa9feb211a99564ba4352d796d538cf9c859f",
    "/usr/bin/dji_gui_on_disp0": "30eb933b1c2315984e150885124d277c13c1cef3194ba6c08cb3d4d1f6656db1",
    "/usr/bin/dji_gui_on_disp1": "e965fbc8588445f5fa922fd1df38ed7051198fe28a50c33e51c94246c00fdb27",
    "/usr/lib/libgui_image_loader.so": "4774cc379c3cdbcc11242b7bde1b7490f3061c11c09ed79f05e2f0afd7c53c82",
}
SERVICES = ("dji_camera3.service", "dji_media.service", "gui.service",
            "sub_gui.service", "dji_sw_uav.service")
SERIAL = re.compile(r"[a-zA-Z0-9_.:-]{1,100}\Z")
SHA_LINE = re.compile(r"([a-fA-F0-9]{64})\s+\S+")


def adb_runner(serial: str) -> Callable[[list[str]], tuple[int, str]]:
    def call(arguments: list[str]) -> tuple[int, str]:
        try:
            p = subprocess.run(["adb", "-s", serial, *arguments],
                               capture_output=True, text=True, timeout=8, check=False)
            return p.returncode, p.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return 127, ""
    return call


def check(serial: str, run: Callable[[list[str]], tuple[int, str]]) -> dict[str, object]:
    """Use a fixed whitelist of nonmutating ADB shell commands only."""
    if not SERIAL.fullmatch(serial):
        raise ValueError("invalid device serial")
    report: dict[str, object] = {
        "mode": "read-only", "model": None, "root_adb": False,
        "architecture": None, "files": {}, "services": {}, "result": "blocked",
        "notice": "Does not unlock, install, flash, reboot, or change any camera files.",
    }
    rc, state = run(["get-state"])
    if rc != 0 or state != "device":
        report["reason"] = "ADB device unavailable or unauthorized"
        return report
    rc, uid = run(["shell", "id", "-u"])
    if rc != 0 or uid.strip() != "0":
        report["reason"] = "root ADB not available; Alliot installer would refuse this camera"
        return report
    report["root_adb"] = True
    rc, arch = run(["shell", "uname", "-m"])
    report["architecture"] = arch if rc == 0 else None
    rc, properties = run(["shell", "cat", "/build.prop"])
    match = re.search(r"^ro\.product\.name=(.+)$", properties, re.MULTILINE) if rc == 0 else None
    report["model"] = match.group(1).strip() if match else None
    if report["model"] != PRODUCT or report["architecture"] != "aarch64":
        report["reason"] = "product or architecture is not the verified AC204/AArch64"
        return report
    files = {}
    for path, known in KNOWN_HASHES.items():
        rc, output = run(["shell", "sha256sum", path])
        matched = SHA_LINE.match(output) if rc == 0 else None
        digest = matched.group(1).lower() if matched else None
        files[path] = {
            "sha256": digest, "matches_alliot_2026_09_27": digest == known,
            "known_reference": known,
        }
    report["files"] = files
    services = {}
    for service in SERVICES:
        rc, status = run(["shell", "systemctl", "is-active", service])
        services[service] = status if rc == 0 and status in {"active", "inactive"} else "not confirmed active"
    report["services"] = services
    if not all(d["matches_alliot_2026_09_27"] for d in files.values()):
        report["reason"] = "ABI/GUI SHA mismatch or unavailable file: NEVER reuse upstream offsets blindly"
        return report
    report["result"] = "fingerprints_match_only"
    report["reason"] = "Reference hashes match; NOT proof of safe root, timer API, recovery, or 10h acceptance"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="exact camera serial from adb devices")
    args = parser.parse_args(argv)
    try:
        report = check(args.serial, adb_runner(args.serial))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "fingerprints_match_only" else 2


if __name__ == "__main__":
    sys.exit(main())
