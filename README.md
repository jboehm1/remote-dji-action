# Osmo Action 6 — Daily Timelapse Scheduler

**Goal:** True Action 6 **Timelapse**, every day on a freely chosen schedule, e.g. **08:00–18:00 (10 hours)**, without the **5-hour finite duration** option restricting the recording. Work toward weeks of unattended operation.

> ⚠️ **Prototype; not tested on physical Action 6 or built with ESP-IDF yet. Do not leave unattended.**

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
| **A. ESP32 daily BLE scheduler + ∞** | Most promising, avoids modifying camera | **Code prototype** + unit tests, camera not tested |
| **B. Push 8h over BLE** | Encoding possible, **acceptance unknown**; Mimo protocol vs GPS remote | Offline packet payload experiment |
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
