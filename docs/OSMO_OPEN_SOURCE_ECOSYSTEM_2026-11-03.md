# DJI Osmo Action ecosystem: firmware, protocols, control and historical generations

**Research snapshot:** 2026-11-03  
**Primary camera:** DJI Osmo Action 5 Pro (AC204)  
**Goal:** native, camera-only, recurring construction Timelapse of ~08:00–18:00 (8–12 h) at 1 s / optionally 2 s, without night recording; external controller only if the internal route fails.  
**Status:** source research; no physical Action 5 Pro access, bootloader unlock, firmware dump, patch or 7-day endurance validation in this work.

## Executive finding

An **on-camera** open-source project really exists: [AlliotTech/action-control](https://github.com/AlliotTech/action-control), for the **Action 5 Pro**, runs alongside DJI's original Linux services after the owner has **already unlocked the bootloader and enabled root ADB**. It is *not* the DJI firmware source, nor a complete firmware replacement. Its author reverse-engineered the existing `libdcam_camera_service_client.so` / Binder client and reports a real-device recording start/stop/status cycle with an actual saved video. The project also installs a guarded extension to the rear-screen GUI. This creates a plausible path to studying, then extending, **native Timer Shooting** or implementing an on-camera scheduler, subject to much stronger access, recovery, wake and power validation.

There is **no demonstrated Action 5 Pro patch to make Timer Shooting accept 8 h** in the sources inspected. Specifically, the well-known DJI Mimo `02/6C` 32-bit Timelapse duration parameter describes **ordinary Timelapse duration**, not necessarily the camera's **Timer Shooting / Repeat task duration**. A successfully encoded `28800` seconds or ordinary `02/6C` readback is not proof that the scheduled 5 h menu limit changed.

### Evidence grades used in this document

- **H — Hardware observed**: maintainer explicitly describes a tested camera and observed effect; not independently reproduced here.
- **D — Direct source/documented**: vendor repository, API or manufacturer documentation; may be untested with our exact Action 5 firmware.
- **P — Proposed/inferred**: could help but is not a demonstrated camera-specific solution.
- **N — Not established**: absent from inspected sources, not proof of impossibility.

## 1. Priority map — which projects can actually help?

| Rank | Project / primary source | Category | Model evidence | Transferable capability | Limit for **our** goal | Evidence |
|---|---|---|---|---|---|---|
| **1** | [AlliotTech/action-control](https://github.com/AlliotTech/action-control) — [native reuse notes](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md) | **Runs inside the camera**, Go + Python native adapter + Web GUI | **Action 5 Pro**, real-device tests | Existing root on-camera process, camera Binder client, record start/stop/status, mode switching, GUI plugin; starting point for read-only firmware/service analysis | Requires unlocked/rooted device **in advance**; no Timer Shooting 8 h patch or RTC-wake validation; firmware-specific fingerprints | **H/D** |
| **2** | [KonradIT/osmosis](https://github.com/KonradIT/osmosis) — [MEDIA_PROTOCOL](https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md) | Mimo BLE/Wi-Fi/DUML reverse engineering; media offload | **Action 5 Pro** hardware (also Action 4 and 6 media tests) | Captured named properties including `gui_autorecord_param`, readback/capability workflows, BLE/Wi-Fi model IDs; nightly media verification path | `gui_autorecord_param` **name only**, not decoded as scheduled task; not an internal scheduler | **H/D** |
| **3** | [OpenPocketCine](https://github.com/erik-sutton95/OpenPocketCine) — [Action 6 protocol captures](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) | Mimo protocol reverse engineering | **Action 6** on firmware V01.02.0521, Mimo 2.12.0; **not Action 5** | `02/6C` ordinary Timelapse setting, encoded interval/duration and capability list | No demonstrated 8 h write; no native Timer Shooting task format | **H** on Action 6 only |
| **4** | [dji-sdk/Osmo-GPS-Controller-Demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo) — [command spec](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/protocol_data_segment.md), [Q&A](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/Q%26A.md) | Official ESP32-C6 BLE *remote* R SDK | Explicit Action **4 / 5 Pro / 6** documentation | Command `1D03` record control, `0011` shutter key, `1D02/1D06` status, `1D04` mode, `001A` power-state | No stock-camera 8 h Timer Shooting setter; BLE wake after long overnight off **not guaranteed** | **D** |
| **5** | [brianmerchant/Kaze-for-DJI](https://github.com/brianmerchant/Kaze-for-DJI) — [settings protocol](https://github.com/brianmerchant/Kaze-for-DJI/blob/main/docs/CAMERA_SETTINGS_PROTOCOL.md) | iOS/Android Mimo protocol implementation | **Pocket 3** hardware-tested; Action 5 not certified | Useful controlled `02/6C` settings readback and menu tables, interval in 0.1 s units | Not proof that Pocket 3 settings IDs apply to Action 5 Timer Shooting | **H** Pocket 3, **P** Action 5 |
| **6** | [luisreysan/osmo-client](https://github.com/luisreysan/osmo-client) | Linux/Pi/PC Mimo BLE+Wi-Fi control | Nano validated, other Action models require camera reports | Our [`feat/action5-multi-hardware`](../README.md) branch uses it for a **reversible ordinary** Timelapse 8 h probe and daily external start/stop | Action 5 not certified by upstream; not camera-only; does not change scheduled-task field | **P** Action 5 |
| **7** | [rhoenschrat/DJI-Remote](https://github.com/rhoenschrat/DJI-Remote) | ESP32 screen remote, multi-cam | Declares Action **4 / 5 Pro / 6** | Ready BLE status/control/wake implementation, reusable ESP-IDF practices | No 24-hour auto scheduled camera-only routine; sleep restrictions persist | **D** |
| **8** | [AlliotTech/osmoControl](https://github.com/AlliotTech/osmoControl) | Android BLE remote, same author as camera-native work | DJI Osmo family | Potential protocol code cross-check, pairing/command models | Runs on Android, not inside Action 5; not a firmware mod | **D** |
| 9 | [datagutt/node-osmo](https://github.com/datagutt/node-osmo) | TypeScript BLE/Mimo reverse engineering | Claims Action **3 / 4 / 5**, Pocket 3 | Older protocol lineage; configuration/video mode and pairing | Author reports noble BLE instability; no device-only schedule | **D/P** |
| 10 | [Spillmaker/DJILib.swift](https://github.com/Spillmaker/DJILib.swift) | Early Swift DJI BLE protocol library | Action 4 documented | Historic protocol lineage used by Moblin/node-osmo | No Action 5 native root, scheduled duration, or RTC control proven | **D/P** |
| 11 | [dimadesu/dji-remote](https://github.com/dimadesu/dji-remote) | Android BLE remote for RTMP and camera control | **Action 4** developer-tested; Action 5 reported supported | **Precedent of out-of-menu numeric override:** developer reports RTMP bitrate above Mimo 6 Mbps UI choice | Higher RTMP bitrate ≠ Timer Shooting 8 h acceptance; developer indicates Action 2 unsupported | **H** Action 4 RTMP report |
| 12 | [dstrat28/action-multicam-remote](https://github.com/dstrat28/action-multicam-remote) | iOS multicamera BLE R SDK | **Action 5 Pro / Action 6** hardware-tested; Action 4 listed but not tested | Independently tested Action 5 remote control | External remote only; not internal timer modification | **H** |
| 13 | [KevinCowleys/osmo-live](https://github.com/KevinCowleys/osmo-live) | Go BLE/RTMP | **Action 4** tested; 3/5/6 proposed | Older-generation 3/4/5 command integration | RTMP streaming, not Timer Shooting | **H** Action 4 |
| 14 | [WingerATB/theslate](https://github.com/WingerATB/theslate) | ESP32-C3 SuperMini and other chip variants, camera BLE bridge | Osmo Nano/360 stable; Action beta | Very small cheap controller; reference C3 SuperMini; chip-specific build cases | **Not** a validated Action 5 daily scheduler; camera BLE limitations remain | **D** |
| 15 | [rover1312/shutterlink](https://github.com/rover1312/shutterlink) | ESP32-C3 BLE DJI/GoPro trigger bridge | DJI Osmo Action protocol implementation | ESP32-C3-specific implementation and BLE pairing details | Trigger bridge ≠ overnight autonomous camera restart | **D** |
| 16 | [theserialhobbyist/M5StickCPlus2_Remote_For_DJI_Osmo](https://github.com/theserialhobbyist/M5StickCPlus2_Remote_For_DJI_Osmo) | Older ESP32/M5Stick remote | DJI Action remote | Historical basis for `DJI-Remote` | No camera-native patch | **D** |
| 17 | [PANDAJSR/OSMO-Remote](https://github.com/PANDAJSR/OSMO-Remote) | Android Kotlin remote + protocol experimentation | Osmo Action (model coverage unclear) | Cross-check R SDK framing, live-view investigations | Model-specific test coverage unclear | **P** |
| 18 | [smithplus/Osmotic](https://github.com/smithplus/Osmotic) / [intermittech/OsmoOffload](https://github.com/intermittech/OsmoOffload) | macOS / Windows media backup | Action family | Potential external automatic nightly offload/media integrity workflow | External media clients; no native timer modification | **D** |
| 19 | [CoffeeMan1ac/osmo-offload](https://github.com/CoffeeMan1ac/osmo-offload) | Linux USB import | **Action 4** | Filesystem import and confirmed-first backup pattern | USB-connected host, not internal scheduler | **D** |
| 20 | [HackMan3D-LayerShot](https://github.com/HackMan3D/Hackman3D-LayerShot) | Layered still images via BLE | Action **4 / 5 / 6** listed | Camera control/mode pairing on microcontrollers | Still-photo stacking, not native 8 h Timelapse | **D** |

All project claims above are scoped to the **models and functions each maintainer actually reports**. Do not infer support merely from shared BLE identifiers or a generic product list. Consult each upstream license before reusing any code; link to source instead of copying proprietary DJI assets or raw camera firmware.

## 2. Generational evolution (why older work still matters)

| Generation | Useful source evidence | Inheritance relevance | What is **not** proved |
|---|---|---|---|
| **Osmo Action (1), 2019** | [DJI firmware download center](https://www.dji.com/downloads/products/osmo-action) lists manufacturer update package; [Osmosis roadmap](https://github.com/KonradIT/osmosis/blob/main/ROADMAP.md) calls out the older index-based media protocol | Historical firmware containers and older Wi-Fi/media transfer scheme | No publicly **verified** Action 1 bootloader/root/8 h scheduler hack found here; modern R SDK commands are not established |
| **DJI Action 2, 2021** | [Osmosis](https://github.com/KonradIT/osmosis) classifies media support as in progress; [dimadesu/dji-remote](https://github.com/dimadesu/dji-remote) explicitly reports remote protocol support as **not working** | Older Mimo protocol fields/packet framing may provide clues | Do not promise modern BLE start/stop or Action 5-compatible firmware image |
| **Osmo Action 3, 2022** | [node-osmo](https://github.com/datagutt/node-osmo) claims Action 3 BLE coverage; [osmo-live](https://github.com/KevinCowleys/osmo-live) lists Action 3 as expected | Better BLE protocol lineage; use only verified commands as clues | No verified Action 3 camera-root jailbreak, native scheduler mod, or independent hardware evidence for every claimed command |
| **Osmo Action 4, 2023** | DJI [R SDK reference](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo); [Osmosis](https://github.com/KonradIT/osmosis) now hardware-validates media; [dimadesu](https://github.com/dimadesu/dji-remote) and [osmo-live](https://github.com/KevinCowleys/osmo-live) tested control/RTMP | Strongest older **external control** reference; compare packet formats and mode IDs with Action 5 | Remote success does not imply an on-camera root method or accepted 8 h native task duration |
| **Osmo Action 5 Pro, 2024** | [DJI Action 5 firmware release notes](https://dl.djicdn.com/downloads/DJI_Osmo_Action_5_Pro/RN/20241126/DJI_Osmo_Action_5_Pro_Release_Notes_en.pdf) explicitly introduce **Timer Shooting** in firmware `01.01.05.20` on 2024-10-16; [Action Control](https://github.com/AlliotTech/action-control) runs locally with root ADB | **First priority**: native GUI task, internal service and writable scheduler interface; media verification possible | Repeat behaviour and 8 h scheduled duration require exact camera firmware/UI and real hardware checks; root method has risks |
| **Osmo Action 6, 2025/26** | [OpenPocketCine real protocol capture](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) and [DJI specs](https://www.dji.com/osmo-action-6/specs) | More recent Timelapse capability enumeration and wire format | Do not transplant Action 6 offsets/firmware/command assumptions blindly to Action 5 |
| **Pocket 3 / Nano / Osmo 360** | [Kaze](https://github.com/brianmerchant/Kaze-for-DJI), [Osmosis](https://github.com/KonradIT/osmosis), [lib-osmo-ble](https://github.com/yigitkonur/lib-osmo-ble), [osmo-client](https://github.com/luisreysan/osmo-client) | Valuable DUML transport/capabilities/CRC/readback patterns and examples | Different firmware/app architecture; no direct Action 5 Timer Shooting evidence |

**Takeaway:** Action 1–4 work is useful mainly for *protocol chronology*. The **Action 5 Pro on-device** `action-control` research is much more promising for avoiding an ESP32 than assuming an older camera's firmware hack is portable.

## 3. Three unrelated interfaces which must never be conflated

| Surface | Who runs it? | Observed API/example | What it controls | Unproven gap |
|---|---|---|---|---|
| **R SDK / accessory BLE** | ESP32, Pi, phone, official accessory | `1D03`, `0011`, `1D02/1D06`, `001A` | External recording commands / telemetry / some power requests | Native Timer Shooting schedule duration; hours-long wake from off |
| **DJI Mimo DUML** | Mimo or third-party host over BLE and Wi-Fi | `02/6C` `duration:uint32_le`, named `cam_lapse_param`, `gui_autorecord_param` | **Ordinary** Timelapse capture duration; some GUI state properties | `gui_autorecord_param` has no decoded task layout or proven setter for repeated schedule |
| **On-camera native client/Binder** | Root-authorized local program on Action 5 Pro | `libdcam_camera_service_client.so` camera getters, `camera_start_recording`, `camera_stop_recording`, GUI extension | Invokes original capture, encoder and file-save services from inside Linux | Dedicated Timer Shooting API, RTC wake, deep sleep policy, firmware-version compatibility |

### Native Action Control specifics that matter

The [native reuse report](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md) documents actual Action 5 Pro library disassembly/function offsets, native capture/record APIs and state transitions (`idle=3`, `recording=1`), with real camera media saved. These offsets are **per binary and firmware**, not an ABI. The installer checks library and GUI fingerprints; it does not blindly apply an extension to unmatched firmware. Original recording pipeline, mode and SD writing remain DJI-managed.

The [README security and install sections](https://github.com/AlliotTech/action-control/blob/main/README.md) explicitly say:

1. Unlocked bootloader and `adb shell id -u` returning `0` are **prerequisites**; this repository itself does **not** unlock or root the camera. Its author's external [unlock research article](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) is a lead only; not independently validated for our camera/firmware here.
2. A local `systemd` service runs in camera Linux; a rear-screen plug-in can alter GUI behavior when firmware fingerprints match. This is a **parallel user program / extension**, not published DJI source code.
3. Its camera admin HTTP server has **no login/authentication or transport encryption**. Never expose port 8080 to public Wi-Fi or the Internet; local ADB forwarding only in research.
4. A sleeping or powered-off camera may halt the Linux service. `systemd`/`cron` scheduling alone **does not establish RTC wake from deep sleep or power-off**.

The most economical potential route is to **extend the already existing Timer Shooting daily task**, keeping DJI's internal timer wake/save mechanism, if one can identify a reversible task-duration setter/config. The alternative is to embed our own on-camera scheduler using the native Binder client, but it must first demonstrate the camera stays alive/wakes under an acceptable power budget.

## 4. Related reverse-engineering / firmware tooling — important exclusions

| Tool / precedent | Relevance | Caution |
|---|---|---|
| [o-gs/dji-firmware-tools](https://github.com/o-gs/dji-firmware-tools) | DJI drone firmware container/disassembly/DUML toolkit | **Not a confirmed Action 5 Pro firmware decryptor, unlocker or flash/recovery tool**; model/key/boot chain differ |
| [fvantienen/dji_rev](https://github.com/fvantienen/dji_rev), [darksimpson/jdjitools](https://github.com/darksimpson/jdjitools) | Historic DJI drone RE knowledge and packet tooling | Drone firmware exploit is **not** Action-series exploitation evidence |
| [cs2000/DankDroneDownloader](https://github.com/cs2000/DankDroneDownloader) | Firmware release archive/index across DJI product families | Downloading firmware is not decryption, bootloader unlock or signed-patch support |
| [xaionaro/reverse-engineering-dji](https://github.com/xaionaro/reverse-engineering-dji) | BLE packet and Mimo analysis lineage | Confirm exact target model before porting parsers |
| [GoPro Labs](https://gopro.github.io/labs/control/dailytl/) — [daily construction Timelapse](https://gopro.github.io/labs/control/construction/) | **Design benchmark**: full on-camera scripted daily shooting, standby/wake and recurrence | **GoPro only**. Neither the firmware nor QR commands can run on DJI Action 5 |
| [petabyt/liemoth](https://github.com/petabyt/liemoth) | Historic Ambarella action-camera hacks | Not evidence of Action 5 architecture or compatible exploit |

## 5. Cross-project design options

1. **Preferred—modify Action 5 native Timer Shooting safely:** research via read-only Mimo captures and, *only on a separately approved/recoverable device*, root read-only analysis. Keep camera's internal repetition/RTC scheme. A verified 8 h task persisted through reboot would be the strongest result.
2. **Alternative—new on-camera service:** extend or integrate with Action Control's existing Binder adapter; schedule native recording by local wall clock, retain official capture/save functionality, and independently prove overnight low power and auto wake. A service cannot run while the Linux host is actually off.
3. **Fallback—ESP32-C3 SuperMini / ESP32-C6:** use DJI R SDK + Timelapse `∞`. Cheap, but DJI says Timelapse moon low-power mode cuts BLE/Wi-Fi during capture; overnight broadcast wake is only documented for recent <=30-minute sleep cases. Both need physical tests, so external controllers are not a proved unattended 7-day solution.
4. **Fallback—Pi 4:** most capable diagnostic (Wi-Fi media checking/live preview), also highest controller energy. Existing Action 5 branch already has a prototype; do not rebuild it here.
5. **Pragmatic benchmark—GoPro Labs:** manufacturer-supported camera-only daily timers. This is a feature benchmark, not a software port.

## 6. Repository cross-reference (avoid duplication)

This project's existing branches remain separate; do not automatically merge draft work:

- [`feat/action5-multi-hardware`](https://github.com/jboehm1/remote-dji-action/tree/feat/action5-multi-hardware), [PR #4](https://github.com/jboehm1/remote-dji-action/pull/4): Action **5 Pro** Pi/ESP32 fallback, low energy, model verification, offline tests. **Starting base for this note**.
- [`feat/esp32-daily-timelapse`](https://github.com/jboehm1/remote-dji-action/tree/feat/esp32-daily-timelapse), [PR #1](https://github.com/jboehm1/remote-dji-action/pull/1): earlier Action **6** external BLE scheduler, C state machine.
- [`research/mimo-action6-protocol`](https://github.com/jboehm1/remote-dji-action/tree/research/mimo-action6-protocol), [PR #3](https://github.com/jboehm1/remote-dji-action/pull/3): Action **6** DUML payload, offline decoders, historical Task/Timer distinction.
- [`jboehm1/timelapse`](https://github.com/jboehm1/timelapse): **separate Android app**, not this Osmo remote/firmware project.

## 7. Open questions ranked by expected information gain

1. **P0:** Is the Action 5 Pro on the owner's firmware *already* capable of selecting a 5 h **native repeating Timer Shooting** task and shutting down/auto-waking the next day? Observe end of a short task and native next-day repeat. Do not infer from screen blackness.
2. **P0:** In a clean Android Mimo capture, does adjusting **Timer Shooting's 3 h → 5 h** duration (while ordinary Timelapse stays constant) change an independent `gui_autorecord_param` payload, other property ID, or IPC message? This isolates the real ceiling.
3. **P0:** Is root ADB on the **specific** Action 5 Pro firmware safe and recoverable without a full flash/brick risk? Cannot assume because Action Control author achieved it on another device.
4. **P1:** Is the 5 h bound only in Mimo GUI/receiver validation or also inside a native scheduler service? Can the existing scheduler store and honor 28800 s after reboot?
5. **P1:** Can a native `Timer Shooting` task retain the moon low-power capture profile and internal wake logic with an extended duration?
6. **P1:** If using a custom on-camera `systemd` process, does camera Linux stay awake between sessions, and what is its *measured* idle draw compared with native scheduled sleep?
7. **P2:** Do Action 4/3/2 earlier timer settings use a recognizable named property or similar enum? Use them as forensic hints only.
8. **P2:** Can backup/offload of finished clips be done from the local camera without waking Wi-Fi throughout shooting? Validate media integrity and SD capacity; no auto-delete without explicit safeguards.

### Research ethics / security

No firmware files, decrypted DJI binaries, unique camera identifiers, Bluetooth keys, Mimo APKs, raw packet captures, session credentials, or executable exploit material are committed. The only thing here is link-backed technical research and a non-destructive validation plan. Existing firmware/root/recovery gates in `AGENTS.md` remain binding.
