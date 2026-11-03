# Action 5 Pro — test now, 2026-11-03

**Target hardware is the DJI Osmo Action 5 Pro (model 0x0015), not Action 6.**
These instructions are a field-test procedure, NOT certification. The camera,
Pi, Pico and ESP32 are not attached to this development environment.

## Reality check: two unrelated clocks

1. **Ordinary Timelapse duration** is the Mimo `02/6C` parameter. The
   documented finite menu ends at 5 h, but `duration=0` means **until stopped**.
2. **Timer Shooting / scheduled daily capture duration** is the *camera's*
   built-in scheduled task. The Action 5 Pro gained Timer Shooting / Repeat in
   firmware v01.01.05.20 (2024). Its setter is **not yet identified**; sending
   `02/6C` might have NO effect on that 5 h scheduled-task ceiling.

The scheduler in this repo bypasses the finite-duration question by using
native Timelapse with duration infinity, external START at 08:00 and external
STOP at 18:00. It requires a responsive BLE connection at both times.

**DJI's moon-icon Timelapse Low Power Consumption disables Wi-Fi and Bluetooth
during shooting. Turn it OFF for external scheduled STOP.** This changes the
camera's power consumption and must be tested with external power and adequate
ventilation. DJI source:
https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE

For the exact **moon/AOD/screen-off distinction**, unknown watts at **1–2 s**,
unverified **14–16 h wake-up**, and battery versus mains operating profiles,
read [ACTION5_LOW_ENERGY.md](ACTION5_LOW_ENERGY.md) before a 7-day test.

## A. Raspberry Pi 4: easiest live end-to-end test

Requirements: Raspberry Pi OS/Linux with BlueZ, Bluetooth LE and Wi-Fi,
NetworkManager, Python 3.10–3.14. The Pi 4 has both radios. **The Wi-Fi must
connect to the camera** for this Osmo Client protocol; Ethernet, another Wi-Fi
adapter or experimental camera station mode is needed for concurrent Internet.
DJI Mimo should be disconnected from the camera during initial pairing.

On the Pi, in a directory where you keep source repositories:

```bash
git clone https://github.com/jboehm1/remote-dji-action.git
git clone https://github.com/luisreysan/osmo-client.git
cd osmo-client
# Probe patch was prepared against osmo-client commit 96cff35.
# If newer source rejects it, inspect the upstream diff; do NOT force-apply.
# Optional ONLY for testing a non-menu 6h/8h finite duration:
git apply --check ../remote-dji-action/patches/osmo-client-action5-probe.patch
git apply ../remote-dji-action/patches/osmo-client-action5-probe.patch

# Launch the camera connection, pairing and status service:
sh osmo-client.sh --no-browser --no-delete
```

On first pairing, open the Pi's local `http://127.0.0.1:8091` page (or tunnel
it via SSH), select the **Action 5 Pro**, approve the connection on the camera,
and wait until live status says connected. Future launches normally reconnect
to the last paired camera. In a **second terminal**:

```bash
cd remote-dji-action
python3 tools/osmo_pi.py status

# Manually set on the Action 5: Timelapse, interval 2 seconds,
# duration ∞, low-power moon OFF. Then test single commands:
python3 tools/osmo_pi.py start --dry-run
python3 tools/osmo_pi.py start
python3 tools/osmo_pi.py status
python3 tools/osmo_pi.py stop

# Schedule dry run first. Then real unattended process, kept in foreground:
python3 tools/osmo_pi.py daily --start 08:00 --end 18:00 \
  --days all --tz Europe/Berlin --dry-run
python3 tools/osmo_pi.py daily --start 08:00 --end 18:00 \
  --days mon,tue,wed,thu,fri --tz Europe/Berlin
```

For a fast test, select a schedule opening **2–3 minutes into the future** and
closing **5–10 minutes after that**. Observe camera's red recording indicator,
the `record.state` field from `/api/status`, and inspect the final playable
media file. Only then try 6–8 hours, and finally a 7-day test.

Safety decisions in `tools/osmo_pi.py`:

- Fails closed unless connected status is fresh, the target is exactly
  `Osmo Action 5 Pro`, capture mode is native Timelapse `2`, and free memory
  exceeds 1 GiB. START requires a confirmed infinity duration (`0`).
- If Action 5 does not publish the current duration in its status, you can
  *explicitly* add `--assume-infinite` after checking the camera's own screen.
  This is an operator override, not proof; leave it off for initial testing.
- Never automatically STOP a recording that was already running when the
  scheduler began. START ownership and retry counts are written to an atomic
  local JSON file before a command is issued. Commands are idempotent at the
  scheduler level, but the external camera response is not yet qualified.
- The schedule is evaluated in local wall time; overnight windows and weekends
  work. If the Pi is powered off at START, nothing can run; use a reliable
  power supply and a systemd service for real deployments. Never run two
  scheduler processes against the same state file.

### Probe 8 h directly: the reversible custom command

Keep the camera **idle**, in native Timelapse, with a known interval and
save format. The patch above adds a dedicated `POST /api/lapse/probe` route
**only for model 0x0015**. It uses the Osmo Client live Bluetooth+Wi-Fi session,
preserves the existing save-format/interval bytes, sends `02/6C` and waits
for camera readback. It rejects values <=5 h or >24 h.

```bash
# 8h = 28800 s; the script prints ACK, payload, before and readback:
python3 tools/osmo_pi.py probe-hours --hours 8
# or the raw local API call:
curl -X POST http://127.0.0.1:8091/api/lapse/probe \
  -H 'Content-Type: application/json' \
  -d '{"duration":28800}'

# Test another value (do not brute-force dozens of writes):
python3 tools/osmo_pi.py probe-hours --hours 6
```

An **ACK** means only that a protocol request was answered.
`"verified":true` means `cam_lapse_param` reported the requested finite
duration. Neither proves a real recording runs that long, persists after
reboot, or extends **Timer Shooting's** separate duration. Inspect the UI,
reboot, inspect media after a real run. **Restore** Duration to the normal
`∞` or another published choice on the camera afterward.

`02/6C` payload example, 1 s interval, video-only, 8 h:

```text
04 00 00 0A 00 80 70 00 00 00 00 00 00 00 00 00
                    ^^ ^^ ^^ ^^ = 28800 seconds, little endian
```

This is the **16-byte body**, not a complete BLE packet. Sending these bytes
directly to a Bluetooth characteristic or a raw socket is invalid.

### Pi 4 media backup after the shoot

Osmo Client already provides gallery listing, Wi-Fi downloads and resume; it
can save directly into a folder on a USB disk mounted on the **Pi** using
`sh osmo-client.sh --downloads /path/to/mounted/drive/...`. A fully unattended
nightly download job (enumerate → compare known files → queue → checksum →
never erase the SD until verified) remains a **future milestone**.

## B. ESP32: DJI BLE, standalone scheduler prototype

The official DJI [Osmo GPS Controller Demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo)
explicitly supports the **Action 5 Pro**, Action 4 and Action 6. The pinned
source here is the vendor submodule; the real firmware glue is `main/app_main.c`.

Requirements: **ESP32-C6 development board** (the only current build target),
ESP-IDF 5.x on a PC, Wi-Fi access to an NTP server (a mobile phone hotspot
works for time sync), BLE nearby (typical remote range ~25 m), powered camera.
ESP32-C3, classic ESP32 and ESP32-S3 have BLE but need **separate build and
hardware qualification**. No Wi-Fi connection *to the camera* is required for
R SDK START/STOP/record/battery status, unlike the Pi/Mimo path.

```bash
git clone --recurse-submodules https://github.com/jboehm1/remote-dji-action.git
cd remote-dji-action
git switch feat/action5-multi-hardware
idf.py set-target esp32c6
idf.py menuconfig
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

Configure Wi-Fi SSID/password, `Europe/Berlin` POSIX TZ (default), START,
STOP, weekdays and the **exact camera BLE MAC** in menuconfig. On a first
boot with MAC unset the DJI demo's BLE scan prints nearby devices and their
addresses, **but this project refuses recording commands**. Copy and verify
the intended Action 5 MAC from the serial log, configure it and flash again.
The identity lock is essential: the upstream DJI demo defaults to whichever
camera has the strongest BLE signal.

Camera setup: Timelapse → ∞ → moon OFF. Observe command and status telemetry
in serial monitor, run a short schedule test; then 6 h, 8 h and 7 days.
The firmware currently does not provide a local web dashboard, auto media
backup or verified waking from deep sleep. It does not enter ESP32 deep sleep
either. `idf.py build` **has not been run in our environment** (no toolchain).

## C. Raspberry Pi Pico vs Pico W — important hardware difference

| Board | Wireless hardware | Can it run this standalone today? |
|---|---|---|
| Raspberry Pi Pico (original RP2040) | **None** (neither BLE nor Wi-Fi) | **No.** Needs an additional BLE controller such as ESP32, or a wired USB/UART bridge. |
| Raspberry Pi Pico W (RP2040) | **Wi-Fi + BLE** via CYW43439 | **Technically plausible** using C SDK + BTstack BLE central; DJI R SDK must be ported from ESP-IDF, not done yet. |
| Raspberry Pi 4 | Built-in Bluetooth + Wi-Fi | Python/Osmo Client implementation ready to test now. |

Existing `core/scheduler.c` is portable C suitable for reusing in a Pico W
build. A true Pico W implementation additionally requires: BTstack discovery,
FFF0 service / FFF4 notify / appropriate write characteristic, DJI pairing,
R SDK framing/CRC, camera identity persistence, Wi-Fi NTP or RTC, and status
feedback. No working Pico W DJI radio driver or verified binary exists yet;
do not mistake portability of the clock code for complete Pico support.

Reference: https://github.com/raspberrypi/pico-examples (BLE client examples).

## D. Remote status, battery and live view

**Raspberry Pi 4** has the most useful existing portal: Osmo Client provides
`GET /api/status` (including battery and record status), its own web page,
`GET /stream` (MJPEG preview), gallery and downloads. The HTTP server
intentionally binds **127.0.0.1 only**. Keep it that way.

- When on the same trusted LAN, `ssh -L 8091:127.0.0.1:8091 pi@pi-address`
  then open `http://127.0.0.1:8091` locally.
- From outside the site, join the Pi through an **authenticated VPN** such
  as Tailscale or use an authenticated SSH gateway, then use the SSH tunnel.
  **Never** expose Osmo Client's unauthenticated recording API on a public IP.
- If the camera's Wi-Fi takes over the Pi's only network interface, Internet
  access and VPN are lost. Prefer Pi Ethernet/USB LTE/second Wi-Fi or
  experiment carefully with Osmo Client shared Wi-Fi station mode.
- `GET /stream` may provide live preview while recording **if** the Action 5
  actually sends frames in Timelapse; this is **not verified**. DJI's USB UVC
  webcam mode is a different mode and should not be assumed concurrent with
  native Timelapse. Test `video_age` and the actual MJPEG image during a
  2-minute recording. With moon low-power enabled, Wi-Fi is disabled.

**ESP32** DJI R SDK reports recording/battery over BLE, so a small status
page is feasible. [ShutterLink](https://github.com/rover1312/shutterlink)
already provides an ESP32-C3 BLE bridge with Wi-Fi AP, record controls and
camera/battery dashboard; it is a strong reference, **not yet integrated**
with this scheduler. Native DJI video live preview over ESP32 is a much larger
Wi-Fi/video transport project and is **not implemented**.

**Future Android**: a phone may offer its Wi-Fi hotspot to the Pi/ESP32,
work as a BLE controller itself, provide a password-protected status UI,
or trigger recordings. Phone hotspot is NOT required for BLE START/STOP
(only potentially for NTP or remote Internet). No APK is implemented here.
Existing reference: [AlliotTech/osmoControl](https://github.com/AlliotTech/osmoControl)
is a public Android Kotlin DJI BLE remote demo with mode switching,
recording, sleeping/waking, GPS and a diagnostic panel. A **recurring daily
alarm has not been verified** in that app; prefer reuse before creating a new
Android stack.

### E. Action 5 Pro Linux-native alternative (research, NOT for deployment)

[AlliotTech/action-control](https://github.com/AlliotTech/action-control)
specifically targets Action 5 Pro AC204 and runs a root-owned Web console
**inside the camera's Linux system**. It documents native recording control,
readback, media manager, Wi-Fi and browser preview (preview can depend on
DJI Mimo already running). This is potentially the most direct future route
to **camera-only internal scheduling**, without an ESP32 or Pi.

**Hard prerequisite:** camera already unlocked with `root ADB`. The project
explicitly does **not** unlock a bootloader, enable root ADB, or remove
factory mode. Installation modifies camera filesystem/services and requires
firmware fingerprint matches. Its default HTTP service has **no login and
no encryption**. Do **not** install, flash, root or expose it for this
project without a separately verified recovery/rollback and explicit user
authorization. No supported Action 5 Pro root method or safe multi-day
scheduled Timelapse is demonstrated by this project's README.

## Hardware acceptance evidence required

- [ ] Action 5 exact firmware number, initial pairing screenshot, BLE MAC
  redacted from public Git history, time zone and chosen Timelapse interval.
- [ ] 1-minute start/stop via Pi; `GET /api/status` during and after; playable MP4.
- [ ] 1-minute start/stop via ESP32; 1D03 ACK plus 1D02 state and playable MP4.
- [ ] Test ordinary `02/6C` 28800 probe, record ACK + before/after readback.
- [ ] A/B capture **Timer Shooting** 3h vs 5h, discover its actual setter.
- [ ] One 6h and one 8h session; actual file duration and playback checked.
- [ ] Evening STOP with moon low-power disabled; overnight power-on/wake test.
- [ ] Loss of BLE/Wi-Fi, power cut, SD full and manual recording safety tests.
- [ ] Seven consecutive daily runs with logs and final media verification.

**No box above is checked yet.** Unit tests and upstream hardware reports are
valuable, but are not certification on **your** Action 5 Pro.
