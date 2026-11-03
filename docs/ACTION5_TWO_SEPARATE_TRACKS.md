# Two independent Osmo Action 5 Pro workstreams (2026-11-03)

**User priority:** 10-hour **camera-only native Timer Shooting** with daily Repeat and native wake. No phone, ESP32, Raspberry Pi, physical actuator or external BLE connection needed during shooting. The camera's own power-management sequence must remain intact. Timelapse interval target: 1 second (optionally 0.5–2 seconds).

## Track N — camera-native modification (PRIMARY)

Entry points: [Alliot exact bootloader/root Linux and addon A-to-Z](ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md), [Alliot root/ABI/GUI audit](ALLIOT_ACTION5_ROOT_ABI_AUDIT_2026-11-03.md), [unlock ZIP static review](ALLIOT_UNLOCK_ZIP_STATIC_REVIEW.md), [10-hour firmware target and gates](ACTION5_TIMER10H_FIRMWARE_TARGET.md), [offline binary scout](ACTION5_OFFLINE_NATIVE_SCOUT.md), [`tools/action5_adb_preflight.py`](../tools/action5_adb_preflight.py).

1. Identify the exact Action 5 Pro firmware, native scheduler and UI ownership. Distinguish **Timer Shooting** from ordinary **Timelapse** duration.
2. Establish a reliable, documented, model-matched root/ADB **and full recovery route** before any modification. Read-only on a pre-rooted device is not a proof of safe unlocking.
3. Examine the stock GUI option table, native task setter, persistence and the camera's existing RTC/PMIC wake mechanism.
4. Best case: insert `36000` seconds (10 h) through a reversible vendor settings/configuration path, retaining the stock wake. If GUI validation is separate, expose the option **only after** actual scheduled-task readback and media acceptance are proved.
5. More invasive ELF/GUI patching or on-camera companion code requires an independent review. Nothing from this track is installed on a real camera yet.

**Do not** call a standard `02/6C` Timelapse duration write a Timer Shooting patch. **Do not** call a root Web console DJI source code or a bootloader unlock. **Do not** show a 10h label without 10h recording acceptance.

## Track B — external BLE/Wi-Fi control (FALLBACK, kept separate)

Existing assets: [ESP32-C6 remote PR #1](https://github.com/jboehm1/remote-dji-action/pull/1), [Action 5 Pi/ESP32 PR #4](https://github.com/jboehm1/remote-dji-action/pull/4), `tools/osmo_pi.py`, `core/` and DJI R SDK integration. This track can use ordinary Timelapse `∞` and remote START/STOP, **but requires an external controller during operation**. Overnight BLE wake and STOP in moon low-power mode remain unvalidated. It is **not a camera-only solution**.

## Protocol and subsystem boundaries

| Item | Domain | Verified meaning | Never infer |
|---|---|---|---|
| DJI R SDK `1D03` | BLE accessory control | Start/stop trigger in official demo | Modify internal Timer Shooting task |
| Mimo/DUML `02/6C` | Ordinary Timelapse | Interval/save/duration on Action 6 survey | Scheduled task duration on Action 5 |
| `camcap_timelapse_duration`, `cam_lapse_param` | Mimo capability/state topic | Ordinary Timelapse duration entries | Native GUI C variables or a Timer wake alarm |
| `gui_autorecord_param` | Mimo topic name | String subscribed by an external project | Timer Shooting; may concern diving Auto Record |
| Alliot native Binder recorder | Rooted Action 5 Pro | Local record START/STOP/status on matched firmware | Timelapse profile or scheduled wake proven |
| Stock Timer Shooting | Action 5 Pro firmware | Manufacturer states camera can wake and start preset capture on schedule | Firmware accepts a 10h task |

## Evidence and completion policy

`SOURCE` = documented by upstream/official source; `DEVICE` = reported physical behavior by upstream with model/version; `OUR_TEST` = reproduced on our exact camera with evidence; `HYPOTHESIS` = untested mechanism. Keep these labels separate in all issues, docs and summaries. No firmware patch is production-ready without readback, actual >5h native capture, reboot persistence, next-day autonomous wake and a >=7-day endurance run.
