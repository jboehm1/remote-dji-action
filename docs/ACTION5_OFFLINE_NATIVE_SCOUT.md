# Action 5 Pro: offline native-binary scout (read-only)

**Objective:** find plausible locations of the **camera's own Timer Shooting/Repeat implementation** and its 5-hour restriction, without mistaking ordinary Timelapse (`02/6C`) for the scheduled task.

**Code:** [`tools/scan_osmo_native.py`](../tools/scan_osmo_native.py); regression tests in [`tests/test_scan_osmo_native.py`](../tests/test_scan_osmo_native.py).

## Why this tool, and what it does not achieve

[AlliotTech/action-control](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md) demonstrates local Binder start/stop on a previously rooted Action 5 Pro, not access to DJI's C/C++ source. Its tested status API has mode-profile mappings **1=Video** and **5=Photo**; **Timelapse mode has not been mapped or proven as locally controlled**. The firmware SHA-256 for its client/server libraries is part of its compatibility lock, so reusing another firmware's offsets would be unsafe.

The scanner reads **owner-supplied, already extracted, offline** files. It detects ASCII and UTF-16LE timer/lapse/scheduler-related strings, hashes inputs, and counts potential 3/5/8/10-hour 32-bit little-endian literals. It emits JSON to stdout only and does not touch a camera, modify bytes, transmit DUML, connect to ADB or write firmware files.

**A hit is only a lead, not proof.** Arbitrary numeric constants can coincide with 18,000/28,800/36,000 seconds; true durations may be data tables, enums, encoded structs, UI resources or computed dynamically. Distance between a literal and a string in an ELF file is not a validated call graph. No 10-hour firmware implementation has been demonstrated.

## Usage on a development computer

```bash
python3 -m unittest discover -s tests -p 'test_scan_osmo_native.py' -v

# Later, only after lawful access and a separately approved recovery procedure:
python3 tools/scan_osmo_native.py /path/to/your/offline/extracted/camera-libraries
```

The input can be one file or a directory. Symlinks are skipped. Per-file size is limited to 128 MiB; scans stop above 300 files. The report includes SHA-256, per-keyword byte offsets, bounded examples and candidate literal counts. Keyword excerpts are intentionally **not** emitted to avoid accidentally reproducing credentials or proprietary strings. Keep proprietary firmware copies and full reports **outside Git**.

## Next research order

1. **No root needed:** compare camera/Mimo settings changes when changing *only* native Timer Shooting from **3h to 5h**, then changing only ordinary Timelapse from **∞ to 5h**; record a repeat toggle and one-hour start-time delta separately. Determine if the property named `gui_autorecord_param` actually belongs to Timer Shooting (it could be the diving Auto Record feature). Existing [A/B matrix](ACTION5_NATIVE_TIMER_INVESTIGATION_2026-11-03.md) specifies the controls.
2. **Read-only firmware study, if authorized later:** obtain an official firmware identity and maintain original hashes. On an **already unlocked** compatible device after a proven recovery review, save approved native libraries on the operator's own machine. Use this scout to prioritize Ghidra/radare2 xrefs and distinguish the GUI list, task persistence, validation layer and RTC/PMIC alarm owner. Do not publish the binaries.
3. **If the scheduler service already accepts 36,000s:** evaluate the narrowest reversible UI/configuration change. Confirm camera task readback, persistence after reboot, actual on-card 10h capture and next-day repeat. A mere ordinary `02/6C` ACK is insufficient.
4. **If the setter clamps to 5h:** only then investigate a native companion scheduled by the camera itself using Alliot's existing start/stop path. This still needs a proven native *Timelapse* mode and RTC wake behavior; a Linux cron job does not wake an unpowered camera.

**Do not** unlock, root, flash, replace ELF files, alter firmware signatures or run any unfamiliar ADB installer as part of this offline scan. Unattended outdoor deployment requires thermal/power/storage safeguards and at least seven days' real repeat/wake validation.
