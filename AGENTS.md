# Engineering contract — DJI Action 6 daily timelapse

This is the **central development handoff**, binding for every contribution. Read it before editing code.

## Mission and operating boundaries
Create a daily, scheduled **genuine camera Timelapse** (not normal video), with editable start and stop **wall-clock times**, weekday selection, DST awareness and no five-hour total-time restriction. Example: every day 08:00–18:00 (10h). Other windows, including overnight windows, must work. Camera must not record at night unless the chosen window includes night. Multi-day unattended operation is the quality target, but it is **not yet achieved or demonstrated**.

## Strict priorities
1. Do not damage, flash, downgrade, overwrite, or patch DJI camera firmware in this project without a separate recovery/rollback design and explicit authorization. No proprietary binary distribution.
2. Implement and hardware-test **external ESP32 BLE scheduler** before attempting firmware hacks.
3. Before scheduling, user must set Osmo Action 6 to **Timelapse / infinite (∞) duration**, preferred interval and save format. Configure it on camera first. No claim that the R SDK currently changes these settings.
4. Use the DJI R SDK status reporting (1D02/1D06) for observation and explicit record commands (1D03) for attempts. Camera must confirm its state; a command ACK is **not** proof that media is being created.
5. Never send a scheduled START with invalid system clock, stale/unverified camera status, wrong mode, overtemperature warning, or <1 GiB reported free storage.
6. Never stop a recording unless there is evidence of ownership by scheduler and camera is in Timelapse mode. Manual activity must not be interrupted.
7. Persist ownership and per-session start attempts before any start command; limit retries; avoid tight loops. Maintain safe behaviour on reboot, disconnect, lost Wi-Fi, SD full, camera shutdown and DST.
8. Do not silently fall back to ordinary video, a fake interval, or continuous overnight capture.
9. Nothing is production-ready until Action 6 hardware testing and a >=7-day endurance run prove actual clip creation and daily start/stop.

## Approaches, ordered
**A — ESP32 external scheduler (primary):** ESP32-C6 (ESP-IDF, Wi-Fi NTP, Bluetooth R SDK) sends START at local schedule opening and STOP at close, with Timelapse configured to ∞. This avoids the 5h menu ceiling. Full power-off/wake/sleep still unverified; v0 keeps camera in a remotely accessible state.

**B — Extended-duration BLE setting (experiment):** DJI Mimo protocol observations show a 16-byte 02/6C timelapse settings body containing a LE32 duration. The camera's advertised legal list ends at 18,000 seconds (5h) plus 0=unlimited. Test whether 28,800 seconds can be accepted and read back **only on hardware**; byte-field width alone does not imply support. This is a *different protocol* from the official GPS remote R SDK. No blind injection of 02/6C through 1D03.

**C — DJI camera firmware patch (last resort):** Not implemented; investigate only after A/B fail and recovery and licensing analysis exist.

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
