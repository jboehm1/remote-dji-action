# Action 6 firmware hacking ecosystem: what actually exists (2026-10-29)

## Executive finding

The **Action 6** was launched by DJI on **18 November 2025**, so the model is just under a year old at this audit. The *Osmo Action series* dates back to 2019, and there is significant third-party protocol reverse engineering, but this is NOT the same as a successful custom firmware/root/mod for Action 6.

**Search conclusion:** A multi-language source search (English, German, Chinese, GitHub, Reddit, DJI forums and DJI official documentation) did **not identify a publicly reproducible Action 6 root, unlocked bootloader, installable modified camera firmware, or proven eight-hour override of its native daily scheduled Timer Shooting duration**. Absence in public search is NOT proof that no private exploit exists.

Launch source: https://www.dji.com/mc/newsroom/news/dji-release-osmo-action-6

## Working Action 6 reverse-engineering is real — but mostly protocol and camera control

| Project | Evidence / scope | What it gives us | What it DOES NOT give |
|---|---|---|---|
| [OpenPocketCine Action 6](https://opencapture.org/openpocketcine/docs/devices/action-6/) | Physical camera survey **2026-09-21**, firmware V01.02.0521, Mimo 2.12.0; millions of packets across iOS/Action 6, CRC-valid DUML frames, capture files, request/reply/readbacks | Real 02/6C ordinary Timelapse settings, 02/01 start/stop, BLE and Wi-Fi transport, mode capabilities, color/aperture controls | NOT a full camera firmware dump, custom flashed firmware, native Timer Shooting duration encoding or tested 8h override; project says its own implementation was not hardware-checked on Action 6 after loaner returned |
| [Osmosis](https://github.com/KonradIT/osmosis) | Active third-party Android Osmo app. Now lists **Action 6 as verified on hardware** (media browse/download). Independent Android implementation, named-property Mimo 00/99 bus; `gui_autorecord_param` in 53-name subscription inventory | Demonstrates reproducible Action 6 BLE/Wi-Fi communication without DJI Mimo, identifies model id 0x18 in its BLE scanner; suitable source for app integration and control transport | Does NOT document what `gui_autorecord_param` means, an eight-hour scheduled Timer Shooting override, or OS/root access to camera |
| [Osmo Client](https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md) | Detailed reverse-engineered DUML command set, settings, named-property readbacks; primarily physical Nano observations | Independent 02/6C parameter-layout corroboration, 02/01 Timelapse shutter, response semantics, capability tables | No qualified Action 6 scheduled-job bypass or proof out-of-menu 28800 seconds works |
| [djictl & reversing docs](https://github.com/xaionaro-go/djictl) / [RE traces](https://github.com/xaionaro/reverse-engineering-dji) | Third-party replacement of DJI Mimo BLE/Wi-Fi control (focus was Pocket 3) | BLE packet dissector, HCI snoop capture workflow, Wi-Fi session and DUML tooling | No camera firmware root or Action 6 internal RTC service patch |
| [DJI Remote](https://github.com/dimadesu/dji-remote) / Moblin | Independent Action 4 RTMP control; author reports sending bitrate > Mimo 6 Mbps menu | **Positive camera-family precedent**: numeric settings beyond advertised menus can work | Not evidence a finite Timelapse/Timer Shooting value is accepted on Action 6 |
| [Official DJI R-SDK demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo) | Official accessory Bluetooth control; explicitly documents Action 6 device ID **0xFF55** and commands | Model-aware official BLE external remote start/stop/status | Distinct from Mimo DUML 02/6C settings and doesn't expose Timer Shooting preset storage. **DJI R SDK != Mimo DUML** |

## Older genuine DJI hacks exist, but they target different products and firmware stacks

- [o-gs/dji-firmware-tools](https://github.com/o-gs/dji-firmware-tools) includes signed/IMAH firmware parsing, Ambarella pack/unpack/ELF tools, firmware hard-coded value modifications. **Its stated focus is quadcopters**, with product-specific support lists. No identification of an Action 6 firmware image or compatible device modules in the source examined. Don't try these tools with Action 6 unless firmware format is first established.
- [fvantienen/dji_rev](https://github.com/fvantienen/dji_rev) documents DJI image blocks, signatures, U-Boot and secure authentication; DJI drone image formats in its description. Again **no verified Action 6 compatibility**.
- [Bin4ry/deejayeye-modder](https://github.com/Bin4ry/deejayeye-modder) patches **DJI GO 4** drone Android application (old versions 4.1.x), NOT DJI Mimo 2.x, and explicitly notes that some application-only patches require firmware modifications to work. It is not an Action 6 firmware unlock.
- [hdnes/pyduml](https://github.com/hdnes/pyduml), [P0VsRedHerring](https://github.com/MAVProxyUser/P0VsRedHerring), [dji_system.bin](https://github.com/MAVProxyUser/dji_system.bin) exploit/flash DJI drone/remote families. No verified public evidence these exploits apply to Action 6. Avoid blind USB command or modified package trials.
- The **original 2019 Osmo Action** exposed an official **microSD firmware update** path; its [original manual](https://dl.djicdn.com/downloads/Osmo%20Action/Osmo_Action_User_Manual_v1.0_en_7.pdf) and [official download center](https://www.dji.com/downloads/products/osmo-action) mention a public firmware update package. DJI [Action 6 FAQ](https://www.dji.com/support/product/osmo-action-6) instead describes **Mimo firmware push**; Action 6 download center currently shows release notes/manuals but not a standalone user flashing package. Old SD update instructions are **NOT transferable**.

## Important real-world warning — firmware failures

Action 6 users have publicly reported firmware revisions disappearing from release pages and lack of ordinary downgrade routes. These are **user reports, not official proof of downgrade impossibility**. A 2026 Reddit post also reports an Action 6 bricked during an update. These reports justify a strict *no-camera-firmware-write without independently verified recovery* policy. Sources:

- https://www.reddit.com/r/djiosmo/comments/1v83i0o/can_dji_please_explain_the_constant_firmware/
- https://www.reddit.com/r/djiosmo/comments/1twu1kq/psa_do_not_buy_dji_osmo_action_6_in_the_us_no/

## Current firmware versions / version control

- Model launched **2025-11-18**.
- DJI [download-center release notes](https://www.dji.com/osmo-action-6/downloads) dated **2026-07-22**; [OpenPocketCine version inventory](https://opencapture.org/openpocketcine/docs/devices/action-6/specifications/) lists **01.05.08.03** for that date, but forum users claim some firmware entries were withdrawn. Don't assert it is the currently installable version without on-camera evidence.
- The published physical protocol study's camera firmware **01.02.05.21** corresponds to a December **2025** firmware release, though its Mimo reverse-engineering survey took place in September **2026**. Avoid equating data-capture date and firmware release date.
- DJI Mimo downloads page currently lists **Android 2.12.4** (https://www.dji.com/downloads/djiapp/dji-mimo). No DJI APK was downloaded or decompiled here.

## What this means specifically for the 8h daily scheduled Timelapse goal

1. The Action 6 already offers user-reported **native Timer Shooting with daily repeat**. Find this job's **actual scheduled duration** setting first; don't assume ordinary Timelapse duration DUML `02/6C` is the same field.
2. The 02/6C normal Timelapse body encodes duration as 32-bit seconds and advertises finite 18000 max and infinity = 0. A reversible 28800 candidate is easy **once the transport is validated**, but still untested. The actual Timer Shooting task may use another storage representation.
3. The named `gui_autorecord_param` appears in an Osmosis Mimo subscription list but has **no public schema**. It might concern **Dive Auto Record** (documented by DJI for Action 5 Pro), not Timer Shooting. Do A/B readbacks Timer Shooting 3h->5h and Diving Auto Record OFF->ON.
4. If scheduled time/duration changes on the **camera touchscreen only** and Mimo does not emit any control commands, reverse engineering Mimo APK alone may never reveal its internal scheduler logic. Need camera-generated status or safe firmware diagnostics (if ever discovered).
5. **No verified standalone camera custom firmware patch available**. Continue with non-invasive read-only and authenticated protocol experiments. Firmware research becomes justified only after a product-specific image, authentication and full restore path are demonstrated.

## Device-specific validation matrix (not yet performed)

| Experiment | What would constitute success | State |
|---|---|---|
| APK/JADX search `gui_autorecord_param`, Timer Shooting, 18000 | Direct camera/model-specific callsite and protocol command identity | APK unavailable locally; script only |
| Action 6 scheduled 3h->5h camera UI change | DUML command OR camera named-status/state delta establishing schedule duration field | Not performed |
| Diving Auto Record negative control | Isolate `gui_autorecord_param` effect if any | Not performed |
| Timer Shooting 8h write | ACK 00 + independent camera readback + survives reboot | Not performed |
| Actual scheduled capture >5h | Saved media + self-scheduled next-day repeat without phone/ESP32 | Not performed |
| Action 6 signed firmware/recovery | Verified official fallback image and non-bricking restore procedure | No public route found |

**Research outcome:** Deeply reverse engineered **communications**, yes. Proven Action 6 **root/custom firmware/daily 8h hack**, no documented working implementation found.
