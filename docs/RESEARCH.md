# Research / design decision record (2026-10-29)

## Confirmed information
- DJI's public Action 6 specification lists Timelapse durations 5/10/20/30m, 1/2/3/5h and **infinity (∞)**. The 5h menu item is **not a hard recording-length limit** when ∞ is selected. [DJI support](https://www.dji.com/support/product/osmo-action-6).
- [rhoenschrat/DJI-Remote](https://github.com/rhoenschrat/DJI-Remote) explicitly lists Action 6 and implements recording, sleep/wake, status and mode switching with ESP32 + BLE. The implementation says background reconnect is user-triggered; it is **not** a ready-made scheduling solution.
- [DJI official GPS remote demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo) implements BLE communication and status subscriptions; command set 1D02 includes mode/status, while the demo has 1D03 START/STOP and 1D04 mode switching APIs. Action 6 device_id is 0xFF55. The demo's mode-switch implementation hardcodes an Action 4 constant; don't rely on it for Action 6 without tests.
- [OpenPocketCine Action 6 protocol survey](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) observed that DJI **Mimo** `02/6C` carries a 16-byte timelapse settings body: `04 00 SAVE INTERVAL_LE16 DURATION_LE32 00*7`, tenths-of-second interval, duration in seconds, 0=∞. Its enumerated durations ended at 18,000s, plus 0. A theoretical 28,800s LE32 representation exists, but it is **not demonstrated accepted by camera firmware**.
- The same survey observed Mimo `02/01` for timelapse START/STOP; this is distinct from the official GPS remote `1D03` command. Cross-protocol equivalence is **not assumed**.

## Options / engineering assessment
| Approach | Chance of achieving 8h daily | Risk | Status |
|---|---|---|---|
| Set camera Timelapse ∞ + external ESP32 BLE daily START/STOP | High in principle; depends on confirming R SDK command | Low for camera firmware; medium for connection reliability | Firmware prototype in this branch, untested on camera |
| DJI Mimo app protocol send duration 28800s via 02/6C | Unknown: current capability list ends at 18000s | Medium protocol risk, no flash risk | Packet encoder only |
| BLE remote *only* sends 8h value without external schedule | Unknown feasibility, still does **not** solve daily recurrence unless scheduled within camera | Medium | Research only |
| Camera firmware patch to remove 5h UI restriction / add recurrent scheduler | Unknown, firmware access and rollback needed | High risk of soft/hard brick, warranty | Not started |
| Timelapse ∞ recorded continuously, cut night in post | Works only for *video* editing but wastes night power and storage | Low hardware risk, poor requirements fit | Rejected as default |

## Important distinctions
- A duration selection of 5h in Timelapse settings is not necessarily the limit of any separate **scheduled/daily capture** feature. Verify the exact Action 6 UI flow and firmware version. Never equate a menu parameter with a tested hard limit.
- BLE GATT 0xFFF0/FFF4/FFF5 in the GPS remote is not interchangeable with every Mimo command path.
- BLE wake is not guaranteed to recover a fully powered-off camera. Sleep/wake behaviour and one camera identity must be hardware-tested.
- Long recordings require external power, thermal protection and storage planning. Do not deploy outdoors without waterproof USB power and enclosure/condensation assessment.

## Why we start with ESP32 instead of a firmware hack
The remote-controlled scheduler can choose start and stop clock times while camera Timelapse uses its publicly documented **∞** duration. That avoids altering the camera firmware and works with native video production. The hard part is robust pairing, wake/reconnect, time and health feedback—not representing a number greater than 18000.
