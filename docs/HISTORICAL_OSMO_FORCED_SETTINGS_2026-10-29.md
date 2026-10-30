# Verified historical DJI Osmo out-of-menu control values — 2026-10-29

## Biggest finding: we targeted the wrong duration field

**The user already has the native Action 6 DAILY Timer Shooting UI, with a 5-hour maximum.** This is a different object from the ordinary Timelapse capture duration. DJI introduced **Timer Shooting** in Action 5 Pro firmware v01.01.05.20 on 2024-10-16; a contemporary hands-on review shows separate recording mode, clock start, duration and **Repeat**. This establishes internal schedule functionality in this family. Reverse engineering ordinary Timelapse DUML 02/6C may NOT change the duration of a recurring Timer Shooting task.

Sources: https://dl.djicdn.com/downloads/DJI_Osmo_Action_5_Pro/RN/20241126/DJI_Osmo_Action_5_Pro_Release_Notes_en.pdf ; https://dronexl.co/2024/10/21/dji-osmo-action-5-pro-firmware-update-bitrate/

## Historical evidence table

| Camera / period | Out-of-GUI value or changed setting | Evidence level | What we can actually conclude |
|---|---|---|---|
| **Action 4** (2023 onward) | **RTMP livestream bitrate >6000 kbps**, e.g. third-party app suggests not exceeding **10000 kbps** | **Positive report from developer with working Action 4**: https://github.com/dimadesu/dji-remote ; official DJI Mimo limit 6 Mbps: https://repair.dji.com/help/content?customId=zh-cn03400006728&spaceId=34 | **Best direct precedent** for an Action-series camera taking an out-of-menu numerical parameter. Developer claims higher bitrate works, but no raw measured RTMP trace in this source; it is not a Timelapse test. |
| **Osmo Nano**, not Action (2026) | Undocumented ISO selectors 0x01/0x02 below offered list, 0x0D above | Physical protocol write observations: https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md | Camera **accepts but coerces** 0x01/0x02 to 0x03 and 0x0D to 0x0C. A successful command can be silently clamped. |
| **Action 5 Pro** (2024-10-16) | High bitrate and Timer Shooting became available | DJI official firmware release notes + CineD https://www.cined.com/dji-osmo-action-5-pro-firmware-update-adds-high-bitrate-option-and-more/ | **Official firmware change, not third-party bypass.** Proves timer/repeat is native firmware functionality in newer Action line. |
| **Action 6**, firmware V01.02.0521 (2026-09-21) | Ordinary Timelapse duration 28800 seconds, vs 18000 maximum finite menu | OpenPocketCine real Mimo captures: https://opencapture.org/openpocketcine/docs/devices/action-6/modes/ | DUML **02/6C** uses a 32-bit duration (so 28800 can be serialized); **no unsupported duration tested** and camera capability list includes 0 and up to 18000 only. |
| **Action 6**, current model | Genuine 6+ hour Timelapse via native **infinity** mode | DJI spec https://www.dji.com/osmo-action-6/specs ; independently described 6h capture https://www.senses.se/en/review-dji-osmo-action-6/ | It is physically possible to record longer than five hours without changing a value, but **not** a forced finite value or daily scheduled limit bypass. |
| **Action 1, Action 2, Action 3** | Public numeric protocol override with confirmed out-of-range resulting camera state | Search across historic GitHub projects, DJI documentation, forums | **None found with sufficient direct evidence**; this is not proof none exist. |
| **Pocket 3** (not Action) | Direct setters for ISO, shutter and various control values | https://github.com/brianmerchant/Kaze-for-DJI/blob/main/docs/CAMERA_SETTINGS_PROTOCOL.md | Useful command layouts, but examples mostly reproduce normal menu choices, **not** a proven out-of-range bypass. |

## Critical two-duration distinction

1. **Capture Timelapse duration**: DUML 02/6C, 16-byte payload: save + interval:u16 LE in 0.1s + duration:u32 LE seconds. Firmware V01.02.0521 advertises max finite 18000, 0=unlimited. Changing 02/6C is only proven to change *ordinary Timelapse settings*.
2. **Timer Shooting daily task duration**: Native scheduler lets user set mode, start time, duration, repeat. The **DUML setter / named topic / parameter ID for this scheduled duration is NOT mapped** in the public Action 6 captures. It may or may not be related to 02/6C.
3. A candidate named topic **gui_autorecord_param** appears in Osmosis's Mimo subscription list (https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md), but is **NOT decoded**. The name alone doesn't prove it is Timer Shooting.

## Prioritized exact physical A/B capture (native DAILY schedule)

1. Keep Timelapse normal settings identical. Capture Timer Shooting repeat **daily**, **08:00**, duration **3 hours**.
2. Change **ONLY Timer Shooting duration** to **5 hours**. Record CRC-valid DUML SET, ACK and independent camera GET/status readback. A 3h->5h binary diff isolates the **real** field.
3. Change **ONLY daily start time** (08:00->09:00), then separately toggle **Repeat**. Identify the task format, power-state and persistence.
4. Read back timer settings after reboot. Distinguish start/stop schedule from normal Timelapse 02/6C.
5. If schedule duration is an unsigned seconds/minutes field, try exactly one reversible **8h** candidate after baseline and restore the old setting immediately if rejected.
6. Only claim success after 8h native MP4 and subsequent next-day automatically recurring capture, without BLE/phone/ESP32.

## Evidence hierarchy

- **Camera-recorded media at non-menu value**: strong proof.
- **ACK plus camera readback**: accepted setting; actual long-run behavior still unproven.
- **Developer report with known working camera**: credible precedent, not direct trace proof.
- **Payload encodable without camera reply**: hypothesis.
- **GUI capability list alone**: advertised choices, not a proven firmware validation bound.

**Recommendation:** Focus our next protocol implementation on the Timer Shooting task, not ordinary Timelapse 02/6C. No successful Action 6 8h override was found in public evidence.
