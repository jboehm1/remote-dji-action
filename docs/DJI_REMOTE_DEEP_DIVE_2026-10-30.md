# Deep dive — `dimadesu/dji-remote` (Android), Moblin upstream, and the other ESP32 DJI-Remote
Date: 2026-10-30. Scope: investigate **the earlier "C. DJI Remote" example** as evidence that DJI cameras accept numerical settings outside Mimo's menu, and as a potential codebase for the Action 6 8–10h recurring Timer Shooting goal.

## TL;DR

**Good real source of control and out-of-menu configuration; NOT an Action 6 daily timelapse hack.** `dimadesu/dji-remote` is an Android/Kotlin BLE app that configures **RTMP livestreams**, not native microSD Timelapse or the in-camera repeating Timer Shooting schedule. It encodes a caller-provided bitrate as **LE16 kbps** and offers **2–20 Mbps** in a dropdown even though official DJI Mimo's RTMP UI offers **3/6 Mbps at 1080p**. The project's author says values >6 Mbps can be used and recommends <=10 Mbps unless tested, but provides no independent measured 10/20Mbps Action 6 trace. Camera-side persistence and 8h schedule acceptance remain unverified.

New finding: **The Android repo's Action 6 handling is behind Moblin upstream.** It treats Action 6 like Action 5 Pro for stabilization configuration and sends the older binary RTMP start body. Moblin's main branch has explicit Action 6 fixes, qualified by a DJI Mimo **BTSnoop** capture: configure byte **0x08 (Action 4)** rather than **0x1A (Action 5 Pro)**, and a **new JSON-wrapped RTMP start variant with middle bytes `FE 00`**. These differences matter when considering reuse of the Android app with Action 6.

## Sources read directly

- Android project: https://github.com/dimadesu/dji-remote (read source files on `main`)
- Android app [README](https://github.com/dimadesu/dji-remote/blob/main/README.md) & [releases](https://github.com/dimadesu/dji-remote/releases) (latest tagged `v0.0.4` as of the research, APK offered)
- Android [UI bitrate list](https://github.com/dimadesu/dji-remote/blob/main/app/src/main/java/com/dimadesu/djiremote/ui/dji/DjiDeviceSettingsScreen.kt), [bitrate encoder](https://github.com/dimadesu/dji-remote/blob/main/app/src/main/java/com/dimadesu/djiremote/dji/DjiPayloads.kt), [model classification](https://github.com/dimadesu/dji-remote/blob/main/app/src/main/java/com/dimadesu/djiremote/dji/SettingsDjiDevice.kt), [BLE/state machine](https://github.com/dimadesu/dji-remote/blob/main/app/src/main/java/com/dimadesu/djiremote/dji/DjiDevice.kt)
- Moblin Swift upstream: [DjiDevice.swift](https://github.com/eerimoq/Moblin/blob/main/Moblin/Integrations/Dji/DjiDevice/DjiDevice.swift), [DjiDeviceMessage.swift](https://github.com/eerimoq/Moblin/blob/main/Moblin/Integrations/Dji/DjiDevice/DjiDeviceMessage.swift). The upstream code explicitly says Action 6 configure byte is known from a DJI BTSnoop trace.
- Official [DJI Mimo RTMP options](https://repair.dji.com/help/content?customId=01700006728&lang=fr&paperDocType=ARTICLE&re=FR&spaceId=17), including Action 6: 1080p -> 3 or **6 Mbps**; 720p -> 2 or 4 Mbps; 480p -> 1 or 2 Mbps.
- Independent field write-up: https://irl4you.de/en/irl-tools/dji-remote.html (uses app, no 10/20Mbit independent media verification claimed).
- **Different, similarly named ESP32 project**: https://github.com/rhoenschrat/DJI-Remote (ESP-IDF C/NimBLE, Action 4/5/6, BLE remote recording, sleep/wake and snapshot; not the Kotlin RTMP tool).
- Official accessory protocol: https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/protocol_data_segment.md .

## Android: specific implementation of the out-of-menu bitrate

`DjiDeviceSettingsScreen.kt` UI list:
```text
20_000_000, 16_000_000, 12_000_000, 10_000_000,
8_000_000, 6_000_000, 4_000_000, 2_000_000
```
Values are kept as **bit/s** in the settings data class (`bitrate=6_000_000` default), passed in **kb/s** via `settings.bitrate / 1000`, then serialized in `DjiStartStreamingMessagePayload.encode()`:
```kotlin
writer.writeUInt16Le(bitrateKbps and 0xFFFF)
```
Example wire bytes for the **RTMP bitrate field** (little endian, *not* the native Timelapse field):
```text
  6,000 kbps -> 0x1770 -> 70 17
 10,000 kbps -> 0x2710 -> 10 27
 20,000 kbps -> 0x4e20 -> 20 4e
```
The RTMP command is `target=0x0802`, `type=0x780840`, i.e. **DUML set 0x08 / id 0x78**. BLE GATT service `FFF0` uses `FFF5` for writes, with fragment queue and pairing. Video RTMP START/STOP are NOT the camera's native `02/01` Timelapse trigger nor the Timer Shooting duration.

**Crucial distinction:** 20Mbps appearing in a drop-down and 20Mbps being serialized DO NOT demonstrate that an Action 6 produces an actual 20Mbps RTMP stream. The developer says >6 Mbps can work and cautions >10 Mbps may be unstable; the README says the developer personally tested **Action 4** and received reports Action 6 works, **without latest upstream Action 6 changes**.

## Exact Action 6 compatibility risk: Android vs newer Moblin

| Feature | Android `dimadesu/dji-remote` | Newer Moblin Swift upstream | Action |
|---|---|---|---|
| Camera model | `OSMO_ACTION_6` present | `.osmoAction6` present | Both recognize model |
| Stabilization config flag | `OSMO_ACTION_6` grouped with Action 5 Pro: `oa5=true` -> byte **0x1A** | `.osmoAction4, .osmoAction6` grouped: byte **0x08**; comments cite **DJI BTSnoop capture** | **Port newer Action 6 branch before trusting Kotlin app** |
| RTMP start payload | Ordinary `DjiStartStreamingMessagePayload` binary; `oa5` toggles prefix `0x2A` vs `0x2E` | Explicit Action 6 case `DjiStartStreamingMessagePayload2`: **JSON-wrapped** body, middle **`FE 00`**; includes codec/EnhancedRTMP fields | Port Action 6-specific RTMP payload if working on its streaming |
| START confirmation | Sends 02/8E confirm for `hasNewProtocol()` | Also sends confirm for `hasNewProtocol()` | Similar |
| Timelapse 02/6C | No implementation found in Android app | Not in Moblin DJI RTMP classes examined | Need different camera-control module |
| Native Timer Shooting duration | Not implemented | Not implemented in inspected Moblin module | **Still unknown** |
| On-device recurrence | Not controlled | Not controlled | No camera-only hack from RTMP code |

Protocol migration is tangible evidence that model/firmware distinction matters. Do not blindly send the Action 5 Pro profile to Action 6 based only on its presence in supported camera enum.

## Safety/operational issues in Android source

- `DjiModel.kt` explicitly logs the complete **Wi-Fi password** and **RTMP URL**, which may include a private stream key. `DjiDevice.kt` also traces TX/RX frames. Remove/redact secrets before using this app with production credentials or sharing debug logs.
- BLE messages use 20-byte write chunks on `FFF5`; a 16-byte 02/6C command body plus 13-byte DUML envelope is 29 bytes, but mere ability to fragment/encode it does NOT prove Action 6's camera accepts a Timelapse SET on the BLE connection, as opposed to the richer Mimo Wi-Fi/UDP **9004** session.
- ACK of a setting is not sufficient: read back current state, reboot, make actual media, and verify recurring autonomous schedule.

## Other `DJI-Remote` — C/ESP32 fallback, distinct from Android tool

`rhoenschrat/DJI-Remote` is **actual C code with ESP-IDF 5.5.1**, NimBLE and LVGL, supports Action 6 and provides local recording START/STOP, **sleep/wake**, snapshot while sleeping, multi-camera, reconnect, 1D02/1D06 power/status. It uses the official DJI **R-SDK remote-controller protocol**, not the Mimo `02/6C` Timelapse settings protocol or `08/78` RTMP bitrate. Relevant [README](https://github.com/rhoenschrat/DJI-Remote) and [implementation doc](https://github.com/rhoenschrat/DJI-Remote/blob/main/docs/implementation.md).

A particularly useful implementation is **manufacturer BLE wake advertising `WKP` plus reversed camera MAC**, 3-second broadcast and wake queue. This might improve our earlier `feat/esp32-daily-timelapse` fallback. However it does **NOT** verify wake after **14 hours** of Action 6 sleep. DJI reference describes a **30-minute** restriction for related Action models; explicit long-night testing is mandatory. The project uses **ESP32/ESP32-S3**, not the exact ESP32-C6 hardware in our prototype; a port will require validation.

## Best route to our requested 08:00–18:00 native daily Timelapse

1. **Do not fork Android DJI Remote blindly**: confirm upstream Moblin Action 6 model-specific protocol first. Reuse its small, well-contained DUML BLE/GATT/CRC infrastructure only if useful for initial commissioning and diagnostics.
2. If a phone is available as one-time provisioner, prioritize `Osmosis` (BLE+Wi-Fi/UDP 9004) and/or Action 6-specific Mimo captures to observe **native Timer Shooting scheduled-job** readback when changing **3h->5h**.
3. Decoding `camcap_timelapse_duration` and `cam_lapse_param` is useful for **ordinary** Timelapse but may not affect the scheduled-job duration. `gui_autorecord_param` remains unqualified.
4. Only then send **one reversible 8h scheduled-job duration** candidate, require ACK + state readback + power-cycle persistence + actual daily automatic recurrence. No firmware flashing until a verified restore route.
5. For fallback ESP32, prefer proven R-SDK sleep/wake/status code from `rhoenschrat`, but do not assume overnight wake, or command STOP during Timelapse moon low-power mode.

**Status of work:** Source code read and compared; no physical Action 6, no RTMP bitrate measured, no live duration write, no camera firmware changes performed.
