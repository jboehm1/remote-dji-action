# Hardware test plan: Osmo Action 6 + ESP32-C6

This plan is **NOT yet executed**. Preserve logs and real output file metadata.

## Initial verification
1. Record camera firmware version, ESP-IDF version/target, timezone, hardware revision, and power scheme.
2. Use Action 6 to set **Timelapse → Duration ∞**, interval (example 10s), native video save format. Disable any competing in-camera schedule.
3. Build ESP32 firmware; configure exact Wi-Fi NTP and schedule using `idf.py menuconfig`.
4. Enable Wireless Connection on camera, confirm Bluetooth pairing; first connection may ask for approval.
5. Check 1D02 and 1D06 have fresh mode/status; camera model must be Action 6. Keep other DJI cameras out of pairing range for this prototype.
6. Schedule an opening a few minutes ahead and ending 15–30 minutes later. Observe 1D03 START/STOP and matching camera status plus saved media. Do not infer success from command ACK alone.
7. Repeat a 6h and a 10h capture on continuous safe external power, with a fixed location; inspect actual start/stop and generated MP4.

## Recovery and safety matrix
| Case | Expected behaviour |
|---|---|
| ESP32 restarts before window | Load persisted ownership/attempts; no premature start |
| ESP32 restarts during recording | Reconnect, verify status; do not toggle shutter; stop at deadline |
| BLE disappears mid-window | No speculative commands; reconnect with backoff |
| BLE disappears at close | Stop when connection/status restored; log missed deadline |
| Wi-Fi outage after NTP sync | RTC remains valid while device runs; log drift expectations |
| Cold boot without valid time | Do not start/stop; request time sync |
| Camera manually starts normal video | Do not stop or switch mode |
| Camera manually changes away from Timelapse | Do not stop a different mode |
| SD reports < 1024 MiB free | Do not start new capture |
| Camera temperature status nonzero | Do not start new capture |
| Timelapse auto stops at 5h because ∞ not set | Detect, bounded restart attempts; test must fail until ∞ configured |
| Daylight-saving transition | Wall clock times remain correct, no duplicate session |
| Thursday 23:00 – Friday 02:00 | Treat as one Thursday start-day session |
| Long shutdown/power cycle | Require known-good clock and BLE status before any action |

## Remaining blockers before unattended service
- We have **not** built this ESP-IDF project with a local toolchain or checked the connected Action 6 BLE handshake. Compile/link or product-specific protocol changes may be needed.
- ESP32 currently has only SNTP (no battery-backed RTC). After complete power loss, a Wi-Fi-free boot remains inert.
- BLE wake from sleeping/off state not yet implemented in automated loop. The camera must remain remotely accessible across the night.
- No UI/web control or health alert transport yet. Menuconfig requires reflashing to change daily hours.
- No verification of free capacity beyond camera status report and no MP4-integrity check. Firmware does not download/correlate media.
- No automatic camera model whitelist. Tested setup must contain only the intended Action 6.
- No seven-day continuous-run logs; do not call it production-ready.

## Unit test
`cc -std=c11 -Wall -Wextra -Werror -Icore core/scheduler.c tests/test_scheduler.c -o /tmp/daily-scheduler-test && /tmp/daily-scheduler-test`

## Firmware build
```sh
git clone --recursive https://github.com/jboehm1/remote-dji-action.git
cd remote-dji-action
git checkout feat/esp32-daily-timelapse
git submodule update --init --recursive
# Source ESP-IDF v5.x environment first.
idf.py set-target esp32c6
idf.py menuconfig
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

IMPORTANT: Build must be performed on a real host with ESP-IDF installed. Don't enter real credentials into any tracked file. `sdkconfig` is ignored by Git.
