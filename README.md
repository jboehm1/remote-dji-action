# DJI Osmo Action 5 Pro — Remote Daily Timelapse Controller

## Current test target (2026-11-03): **Osmo Action 5 Pro**

**[Start here: Action 5 Pro Pi 4 / ESP32 / Pico test matrix, commands and
8-hour protocol probe](docs/ACTION5_TEST_NOW.md).**

**[Important: Action 5 low-energy moon, Bluetooth/Wi-Fi, overnight wake,
measured-vs-hypothetical watt budgets and four control profiles](docs/ACTION5_LOW_ENERGY.md).**

**Field observation update (Nov. 3):** user's 14-minute final Timelapse video
drained a 10,000 mAh bank from 90% and the Action 5 battery from 14%. Depending
on **1 s vs 2 s** capture interval and **25 vs 30 fps** exported video, this
represents **5 h 50 min to 14 h actual capture**, not 14 minutes. The exact
settings are still unconfirmed; see the calculation and reproducible
`tools/action5_calibrate.py` in the power research document.

This branch adds:

- **Raspberry Pi 4**: `tools/osmo_pi.py` controls an Action 5 Pro through the
  local [Osmo Client](https://github.com/luisreysan/osmo-client) API. Includes
  status, camera-safe START/STOP, daily schedule, persistent ownership, DST
  handling and tests. Requires BLE **and** Wi-Fi to run Osmo Client itself.
- **Reversible 6/8/10/12-hour experiment**: apply
  `patches/osmo-client-action5-probe.patch` to Osmo Client, then run
  `python3 tools/osmo_pi.py probe-hours --hours 8`. This targets ordinary
  `02/6C` Timelapse; **it may not control the separate Timer Shooting duration**.
- **ESP32-C6**: existing official DJI BLE controller prototype with daily
  schedule, now guarded by an exact configured camera BLE MAC to prevent
  operating the nearest unknown device. No camera firmware modification.
- **Pico/Pico W**: hardware-dependent feasibility and porting checklist in
  the guide. **No standalone Pico firmware** has been built or verified.
- **Future Android / remote monitoring**: documented authenticated Pi portal,
  recording/battery status, MJPEG preview caveats, and phone hotspot option.
- **Investigate before rewriting**: existing Android BLE remote
  [osmoControl](https://github.com/AlliotTech/osmoControl) and the Action 5
  Pro **root-only** internal Web console
  [Action Control](https://github.com/AlliotTech/action-control). Neither is
  a verified safe daily scheduler for a stock Action 5 Pro.

**Validation status:** Python scheduler tests and portable C scheduler tests
run offline. No ESP-IDF toolchain or physical Action 5 Pro is available in this
environment. **This is NOT certified for unattended paid-production filming.**

The older sections below describe Action 6 research and the original ESP32
proof of concept. They remain available for historical context.

---

## Earlier Action 6 research (2026-10-29)

**Goal:** True Action 6 **Timelapse**, every day on a freely chosen schedule, e.g. **08:00–18:00 (10 hours)**, without the **5-hour finite duration** menu restriction. **The primary target is camera-only: no phone, ESP32 or other runtime hardware.** Work toward weeks of unattended operation.

> ⚠️ **Prototype; not tested on physical Action 6 or built with ESP-IDF yet. Do not leave unattended.**

## Research update: important camera wake limitation (2026-10-29)

**New primary direction: internal camera-only scheduling and custom 8h+ setting, IF a safe reversible path is feasible.** The ESP32 branch is a fallback experiment and its firmware has not been built or run on a camera.

- DJI's official remote protocol says broadcast BLE wake requires the camera to have slept **no more than 30 minutes**, illustrated with older Action 4/5 models. We have **not confirmed** whether Action 6 has the same limit. Do not assume it can wake after 14 hours.
- DJI says Timelapse moon low-power mode **disables Bluetooth and Wi-Fi during capture**, potentially blocking external STOP.
- A custom `28800`-second duration setting would not by itself make the camera restart automatically tomorrow. Native recurring schedule and internal RTC alarms also need investigation.
- **Current ESP32 firmware has no deep-sleep code**. The ~0.01Wh/day target is for a **future optimized board**, not the current always-on implementation.

Read [camera-only feasibility study](docs/NATIVE_FIRMWARE_FEASIBILITY_2026-10-29.md), [camera power states](docs/POWER_STATES_AND_NATIVE_PLAN.md), and [calculated ESP32 energy budgets](docs/ENERGY_BUDGET.md). Reproduce estimates with `python3 tools/esp32_power_budget.py`.

## Quick answer: how we go beyond five hours

The official DJI Action 6 Timelapse menu lists 5h as its **longest finite option**, **but it also offers ∞ (unlimited)**. Set **Timelapse → Duration ∞** on the camera; let an **external ESP32 BLE remote** start and stop the capture at 08:00 and 18:00. This avoids a firmware hack and does not require a direct custom 8h parameter to be accepted.

```text
ESP32-C6 (NTP time, DST, persistent schedule)
  ├─ 07:59  wait (no record)
  ├─ 08:00  check camera mode / temperature / SD / BLE status → START
  ├─ ...    verify recording, reconnect on loss
  ├─ 18:00  if controller owns this Timelapse → STOP, verify
  └─ Night  no recording; automated camera sleep/wake still TODO
                       │
                       └─ Bluetooth DJI R SDK ──→ Osmo Action 6
                                  Timelapse mode; Duration = ∞
```

## Alternatives

| Route | Feasibility | Our status |
|---|---|---|
| **A. ESP32 daily BLE scheduler + ∞** | Conditional: overnight wake and low-power STOP may fail | **Code prototype**, camera not tested |
| **B. Push 8h over BLE + native scheduler** | **Preferred if** a native recurring schedule exists; 8h acceptance unknown | Offline packet experiment |
| **C. Hack camera firmware** | High risk, requires compatible firmware + full recovery | Not started |

See [research and evidence](docs/RESEARCH.md). DJI Mimo's observed duration parameter uses LE32 seconds, but the Action 6's published capability list ends at 18,000 seconds (5h) plus 0=unlimited. Sending 28,800 as bytes is *not proof* the camera accepts it.

## Code layout

- [AGENTS.md](AGENTS.md): **central mandatory requirements / handoff and quality gates**.
- [core/](core/): portable C daily schedule decisions (day/night/overnight/weekday/DST).
- [main/](main/): ESP-IDF NTP + BLE DJI R SDK + NVS + fail-closed policy.
- [tests/](tests/): host tests for time windows, ownership and safety gates.
- [experiments/](experiments/): **offline** 8h Mimo timelapse payload builder (no BLE transmission).
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md): setup, build, manual testing, soak-test and open gaps.
- `vendor/dji-sdk`: pinned git submodule from [DJI official remote demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo).

## Reproduce on a development computer

```bash
git clone --recursive https://github.com/jboehm1/remote-dji-action.git
cd remote-dji-action
git checkout feat/esp32-daily-timelapse
git submodule update --init --recursive

# Run pure portable tests without ESP-IDF / camera:
cc -std=c11 -Wall -Wextra -Werror -Icore core/scheduler.c tests/test_scheduler.c -o /tmp/daily-scheduler-test
/tmp/daily-scheduler-test

# Experiment: construct a *payload*, DOES NOT send to camera:
python3 experiments/timelapse_payload.py --interval 10 --hours 8

# ESP32-C6 requires an installed Espressif ESP-IDF v5.x toolchain:
idf.py set-target esp32c6
idf.py menuconfig  # Daily DJI Timelapse Settings: Wi-Fi, TZ, start/end
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

**Critical:** first set **Timelapse** with **∞** and chosen interval on the camera. The prototype does not yet automatically select the capture mode, prove the correct camera is connected, wake a deeply sleeping camera, or guarantee a 10-hour video. The ESP32 must get valid time from NTP at least once. Use stable external camera power, storage, thermal protection and waterproofing for multi-day footage.

## Sources and rights

- [DJI Action 6 specifications](https://www.dji.com/support/product/osmo-action-6)
- [rhoenschrat/DJI-Remote](https://github.com/rhoenschrat/DJI-Remote) (ESP32 remote with stated Action 6 support)
- [DJI official GPS controller demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo) (SDK/API; consult MIT/EULA notices)
- [OpenPocketCine Action 6 timelapse protocol survey](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) (observations, not guaranteed remote feature)

This project is not affiliated with DJI.
