# Engineering contract: Action 6 autonomous daily Timelapse (Mimo research)

**Priority:** an Osmo Action 6 that autonomously repeats a real Timelapse daily for user-selected start/stop local times and enters a low-power state, WITHOUT runtime external hardware. **Current code is offline RESEARCH ONLY.**

## Definition of done
- Once configured, an Action 6 starts 08:00, stops 18:00, finalizes native MP4, and starts again next morning.
- Works for 8h, 10h and 12h windows, day-of-week restrictions optional, persists across system startup/reboot.
- Prove power-state behavior by measurement, not an unlit screen. Power and storage/temperature safety are necessary.
- No reliance on ESP32/Bluetooth/mobile/Wi-Fi after initial provisioning.
- At least seven successful days of real-device operation and a validated recovery method for any firmware changes.

## First read
1. `README.md`
2. `docs/MIMO_REVERSE_ENGINEERING_2026-10-29.md`
3. `docs/MIMO_CAPTURE_PROCEDURE.md`

## Evidence rigor
- **Documented on a REAL Action 6**: V01.02.0521 / DJI Mimo iOS 2.12.0, DUML 02/6C, 16-byte body, 32-bit duration in seconds and 00/99 `cam_lapse_param` state feedback. Allowed finite values captured <=18000 seconds.
- **NOT demonstrated**: 28800 accepted; value persisted across restart; built-in daily repeating alarm; firmware patch accepted; safe boot restore.
- Any new observations must include **actual camera firmware**, **Mimo version**, **transport**, **command**, **reply**, **readback**, **clip or setting persistence evidence**.
- A valid bytestring is not a valid *camera setting*. ACK00 alone is not proof of 8h capture. Readback alone is not proof of daily recurrence.
- Distinguish Mimo DUML `02/6C` and `02/01` from the remote-controller R SDK `1D03`, `1D04`.
- Avoid brute force command IDs. Prefer read-only analysis, then one controlled reversible settings write of 28800s after baseline capture.
- Preserve user-chosen interval/save/output and all unknown reserved fields; restore original configuration after experiments.
- DO NOT flash edited DJI firmware without a device-specific, tested recovery path and explicit permission.
- DO NOT publish raw HCI/BTSnoop/PCAP, Wi-Fi credentials, pairing PINs, camera identifiers, third-party copyrighted APKs or firmware images.
- The standalone 8h payload encoder is intentionally offline-only. Don't add a network sender without safeguards, user-controlled target identity, dry-run and status checks.

## Development process
Use separate branches, open a draft PR per material stage, run offline unit tests. Where no hardware is available, say so. For any claimed supported Action 6 firmware version, attach sanitized evidence and test results. Compare older v01.02.0521 data to actual current camera firmware before generalizing.

## Current related branches
- `research/mimo-action6-protocol`: preferred camera-only effort.
- `feat/esp32-daily-timelapse`: earlier external controller fallback (not yet hardware verified).
