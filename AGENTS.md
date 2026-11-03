# Engineering contract — DJI Action 5 Pro daily timelapse (Action 6 legacy)

## Current user request — 2026-11-03 (takes precedence over older Action 6 goals)

**Primary target: Osmo Action 5 Pro with camera-only, repeating native Timer Shooting of 10 hours (e.g. 08:00–18:00). NO runtime external controller.**
Preserve the original DJI scheduled wake/low-power path. First distinguish Timer
Shooting's own duration setter from ordinary Timelapse `02/6C` using a
non-root 3h→5h capture comparison. Next investigate settings-only 36000s
acceptance. Bootloader/root/native ELF modifications are prohibited without a
separate owner-approved recovery gate. Raspberry Pi 4, ESP32-C6 and Pico W
controller prototypes remain *fallback* experiments, not the camera-only goal.
The original Pico (without W) has no built-in Bluetooth or Wi-Fi and cannot
remotely control DJI by itself. An ESP32 BLE bridge is a distinct two-board
option, not equivalent to native Pico support.

**New ordering:** before any root/EDL work, follow **`docs/ACTION5_MINIMUM_NO_CABLE_FIRST_2026-11-03.md`**: stock UI and rootless Mimo/task discovery, verified scheduled-setter readback, one-time 36,000 s attempt only if qualified; camera-only autonomous >5 h wake/end validation. No cable-free root method is currently proven on locked AC204; do not confuse vendor ordinary Timelapse `02/6C` with daily Timer Shooting. EDL cable is only a fallback, estimated ~€8–15, and backups do **not** erase boot/partition brick risk.\n\nRead **`docs/ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md`** before any device/root work: the original author's blog and ZIP have now been verified and explain exact AC204 firmware 10.00.16.13 / EDL → devinfo → factory ABL → root Linux process stages. **Never copy sector addresses, slot assumptions or execute writes on the owner's camera without a separate recovery gate.**\n\nSee **`docs/ACTION5_TWO_SEPARATE_TRACKS.md`** for the strict split between primary camera-native research and independent external BLE fallback; **`docs/ALLIOT_ACTION5_ROOT_ABI_AUDIT_2026-11-03.md`** for pinned source/ABI/GUI root details; **`docs/ALLIOT_UNLOCK_ZIP_STATIC_REVIEW.md`** for the **authenticated original ZIP's complete two-binary manifest and ELF/certificate audit**; and **`docs/ACTION5_TIMER10H_FIRMWARE_TARGET.md`** for the 10 h validation chain. The owner-supplied ZIP was SHA-256 verified and inspected offline; this **does not validate** the root procedure, programmer-device compatibility, bootloader key acceptance or recovery. Archive inspection is read-only via `tools/inspect_alliot_unlock_zip.py`.

See `docs/ACTION5_TEST_NOW.md` for real-hardware acceptance and all limitations.
The `02/6C` setter changes *ordinary Timelapse duration*, whereas the
Action 5's **Timer Shooting / Repeat** scheduled duration may use an entirely
different unconfirmed command. Never advertise a direct 8h probe as a hack of
that separate scheduler.

Run Python/C host tests, keep ESP-IDF builds distinct from tests. Hardware
validation of START/STOP, overnight BLE wake and prolonged recordings is still
mandatory. Existing clauses below about safety, no DJI firmware flashing,
ownership, storage, status freshness and no simulated certification still apply.

## Product direction update — 2026-10-29

**Primary user requirement: NO external device.** The camera itself must run a daily repeating Timelapse schedule with a freely configurable 8h+ window, then enter low-power/off state as appropriate and wake automatically next day. Prefer a reversible, on-camera settings/protocol modification; firmware patching is a research-only fallback until update/signature/recovery paths are demonstrated. The existing ESP32 PR is a fallback feasibility prototype, not the preferred final product.

**Critical correction:** Do NOT assume an ordinary BLE STOP (DJI R SDK 1D03) puts the camera into deep sleep. DJI's Action 6 manual guarantees automatic off after 3s specifically for **SnapShot launched while powered off**, not for arbitrary STOP commands. DJI's remote-demo Q&A describes a different **sleep → remote wake → snapshot → return to sleep** flow. These are three distinct state transitions. Furthermore, DJI says **Timelapse Low Power Consumption (moon icon) disables Bluetooth and Wi-Fi during shooting**, potentially preventing an ESP32 BLE STOP at the desired end time. The fallback controller is therefore blocked on a proven end-of-session path when this feature is on. See `docs/POWER_STATES_AND_NATIVE_PLAN.md`.


This is the **central development handoff**, binding for every contribution. Read it before editing code.

## Mission and operating boundaries
Create a daily, scheduled **genuine camera Timelapse** (not normal video), with editable start and stop **wall-clock times**, weekday selection, DST awareness and no five-hour total-time restriction. Example: every day 08:00–18:00 (10h). Other windows, including overnight windows, must work. Camera must not record at night unless the chosen window includes night. Multi-day unattended operation is the quality target, but it is **not yet achieved or demonstrated**.

**HARD NIGHT-WAKE BLOCKER:** Official DJI GPS controller protocol documentation `001A` states BLE broadcast waking needs prior recent connection and camera sleep duration **no more than 30 minutes** (examples from Action 4/5). Do not treat this as an established Action 6 limit, but **do not design a 14-hour camera sleep + one morning BLE wake** without explicitly measuring Action 6 behaviour after 40min, 2h and 14h. If wake fails, any energy budget relying on only two daily active windows does not imply a working system. See `docs/NATIVE_FIRMWARE_FEASIBILITY_2026-10-29.md`, `docs/ENERGY_BUDGET.md`, and issue #2.

**CURRENT CODE ENERGY WARNING:** `main/app_main.c` currently leaves Wi-Fi/BLE active and does not enter ESP32 deep sleep. 7uA is the Espressif silicon specification, **not the measured draw of this prototype**. Before promising 0.01Wh/day, add low-leakage regulator/RTC, deep-sleep firmware, BLE wake verification and bench measurements.

## Strict priorities
1. Do not damage, flash, downgrade, overwrite, or patch DJI camera firmware in this project without a separate recovery/rollback design and explicit authorization. No proprietary binary distribution.
2. Prioritize **native Action 5 Timer Shooting**: non-destructive protocol A/B, firmware-identity confirmation and read-only offline triage before any privileged firmware intervention. A rooted on-camera companion is a high-risk fallback; a separate external ESP32 remains another fallback.
3. Before scheduling, user must set Osmo Action 6 to **Timelapse / infinite (∞) duration**, preferred interval and save format. Configure it on camera first. No claim that the R SDK currently changes these settings.
4. Use the DJI R SDK status reporting (1D02/1D06) for observation and explicit record commands (1D03) for attempts. Camera must confirm its state; a command ACK is **not** proof that media is being created.
5. Never send a scheduled START with invalid system clock, stale/unverified camera status, wrong mode, overtemperature warning, or <1 GiB reported free storage.
6. Never stop a recording unless there is evidence of ownership by scheduler and camera is in Timelapse mode. Manual activity must not be interrupted.
7. Persist ownership and per-session start attempts before any start command; limit retries; avoid tight loops. Maintain safe behaviour on reboot, disconnect, lost Wi-Fi, SD full, camera shutdown and DST.
8. Do not silently fall back to ordinary video, a fake interval, or continuous overnight capture.
9. Nothing is production-ready until Action 6 hardware testing and a >=7-day endurance run prove actual clip creation and daily start/stop.

## Approaches, ordered
**A — Native Action 5 Timer Shooting (primary):** identify the *scheduled task* duration setter, prove DJI's native automatic wake remains intact and test 36000s only through reversible, owner-authorized steps with full readback and real recording. The ordinary `02/6C` setting is not the scheduled-task setter. No working camera-only 10h modification is claimed.

**B — On-camera companion (research-only fallback):** AlliotTech/action-control proves certain native Binder recording calls on an already unlocked/rooted Action 5 Pro, but Timelapse mode, timer task ownership and overnight RTC wake are unverified. Do not deploy root code until a model-matched restore path and separate permission exist.

**C — External ESP32/Pi scheduler (fallback), then firmware patch only as last resort:** External code exists but moon mode disables radio and overnight BLE wake is uncertain. DJI firmware patching is not implemented; require separate risk/recovery/license review. See [Action 5 offline scout](docs/ACTION5_OFFLINE_NATIVE_SCOUT.md).

## Reference revisions and rights
- DJI official GPS remote demo, pinned git submodule at `vendor/dji-sdk`, commit `92fe23e5a749f189593f980a26a105c3bb66aa1c`. Its own source license mentions MIT and DJI EULA for the protocol. Read upstream LICENSE. Do not strip headers.
- https://github.com/rhoenschrat/DJI-Remote (Action 6 supported, ESP32 reference; no scheduling included).
- https://www.dji.com/support/product/osmo-action-6 (official ∞ timelapse duration).
- https://opencapture.org/openpocketcine/docs/devices/action-6/modes/ (observed DJI Mimo 02/6C semantics).

## Repository architecture
- `core/`: pure C deterministic schedule/state decisions (no hardware calls).
- `main/`: ESP-IDF Wi-Fi time sync, NVS persistence, BLE R SDK adapter, policy checks.
- `vendor/dji-sdk`: pinned Git submodule; never edit vendored files.
- `tests/`: host-gcc unit tests; expand with simulated BLE disconnect/restart.
- `experiments/`: packet construction and reverse-engineering tools; **no live unsafe packet transmit**.
- `docs/`: evidence matrix, field procedures, results and remaining gaps.

## Must-pass acceptance gates
- [x] Pure schedule logic for daytime / overnight / weekday / DST-local calendar.
- [x] Experimental ESP-IDF glue built against upstream SDK source paths; compiles **not yet verified**.
- [x] Status freshness gate, time gate, overheat and capacity gate, bounded attempts, NVS ownership.
- [ ] Build with pinned ESP-IDF toolchain (capture version and exact build logs).
- [ ] Pair and connect physical Action 6; reject other nearby camera identities.
- [ ] Verify that 1D03 starts and stops **Timelapse** on Action 6.
- [ ] Prove 08:00–18:00 actual 10h recording on SD and camera remains cooler than thermal limits.
- [ ] Confirm deterministic camera wake/sleep/reconnect across overnight and power-cycling.
- [ ] Hard reboot + loss of NTP + power interruption + storage full + high temperature + BLE outages.
- [ ] Prove no accidental stop of manual video/timelapse.
- [ ] >=7 consecutive days of correct morning starts and afternoon stops with evidence/media/logs.

## Development protocol
1. Read `AGENTS.md`, `README.md`, `docs/RESEARCH.md`, `docs/TEST_PLAN.md`.
2. Inspect current HEAD and PRs before edits. Work in feature branches and maintain evidence in docs.
3. Prefer measured behaviour over assumptions. Mark every Action 6 feature **observed**, **documented**, or **not verified**.
4. Run host unit tests locally; avoid using GitHub Actions minutes when quota is exhausted.
5. When hardware is available record firmware version, ESP32 model, radio scan, BLE handshake and raw/parsed command/status responses (redact credentials/MACs).
6. A regression test is mandatory for each bug fixed. Never fake test results, builds or a working camera recording.
