# Deep reverse engineering: DJI Mimo ↔ Osmo Action 6, native 8–12 h daily timelapse
**Research baseline: 2026-10-29. No physical Action 6 access in this environment. All facts scoped to cited versions.**

## 0. Correct end-state and distinction

**Target:** after one-time setup, Action 6 alone automatically starts a native Timelapse at a chosen local time every day (e.g. 08:00), runs for 8–12 h, finalizes media, enters a truly low-energy state, wakes the next morning, repeats; **no ESP32, phone or network at runtime**.

This requires TWO separate capabilities:
1. Native user-configurable Timelapse duration >5h, or infinite Timelapse with an internal timed STOP.
2. A camera-resident **recurring start-time scheduler** plus RTC wake, persistence across restart and valid low-power transitions.

**Warning:** Extending the finite duration to 8h does not create a daily schedule.

## 1. Ground truth from real Action 6 Mimo captures

Most useful discovery: OpenPocketCine's [physical Action 6 Mimo modes survey](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) on **2026-09-21** (Action 6 firmware **V01.02.0521**, iOS Mimo **2.12.0**). It contains frame-level identifiers, ack and camera state, not just a speculative undocumented command list.

| Fact | Evidence / precision | Confidence |
|---|---|---|
| Timelapse SET is **DUML CmdSet 02 / CmdID 6C** | Their T13 and T14 captures; 46 observed requests | High for captured firmware |
| Payload length **16 bytes**, starts `04 00` | T13 examples | High |
| Byte 2 save enum `00`=Video, `02`=JPEG+Video, `03`=RAW+Video | T13 56568, 57450, 58364 | High |
| Bytes 3–4 **interval LE16, 0.1s unit** | T14 interval sweep 0.5s..1h | High |
| Bytes 5–8 **duration LE32 seconds**, 0=∞ | T14 all 9 duration choices | High |
| Bytes 9–15 **7 zero bytes** | All observed T13 requests | High only for captured layout |
| Actual capability topic `camcap_timelapse_duration` | T13 11329: **9 values** 0,300,600,1200,1800,3600,7200,10800,18000 seconds | High |
| **Every advertised choice selected + ACK 00 + matching state** | T14 request/ACK/state table; 5h T14 6699/6707/6750 | High |
| `cam_lapse_param` readback selected duration | 21-byte topic data, bytes 5–8 LE32 | High |
| **Custom 28800s accepted by camera** | **NOT tested** by source nor in this repo | Unknown |
| **Action 6 on-device recurring alarm** | Not established by these captures or DJI manual | Unknown |

### Exact 8-hour payload (10-second interval, Video)
```text
             header  SAVE  INTERVAL_LE16 DURATION_LE32         seven reserved zeros
02/6C body:  04 00    00     64 00        80 70 00 00     00 00 00 00 00 00 00

Duration 8h = 28800 decimal = 0x00007080 (LE: 80 70 00 00).
Duration 10h = 36000 decimal = 0x00008CA0 (LE: A0 8C 00 00).
Duration 12h = 43200 decimal = 0x0000A8C0 (LE: C0 A8 00 00).
Duration  5h = 18000 decimal = 0x00004650 (LE: 50 46 00 00).
Duration  ∞ = 0 (LE: 00 00 00 00).
```
**This is a 16-byte parameter body, NOT a ready-to-send BLE packet.** Connection, routing, DUML envelope, CRCs, acknowledgement and readback all matter. Encoder in `tools/mimo_action6.py` deliberately has NO radio transmitter.

### Timelapse readback is NOT the SET body
OpenPocketCine documented 21-byte **topic data** `cam_lapse_param`, not the full `00/99` status notification envelope:
```text
0       save format
1..2    selected interval, tenths of sec, LE16
3..4    minimum interval, tenths of sec, LE16
5..8    selected duration, seconds, LE32
9..10   Hyperlapse ratio LE16
11..12  companion ratio LE16
13..16  elapsed-correlated counter LE32; unit not measured precisely
17..20  output-correlated counter LE32; exact file frame semantics unknown
```
**Acceptance sequence** = request sent → command-specific response status==0 → new `cam_lapse_param` reports 28800 → setting survives camera restart → camera actually creates 8h media. **ACK without readback is insufficient.**

### Dynamic legal combinations
At 30-minute Timelapse interval, the duration capability list shrinks to ∞/30m/1h/2h/3h/5h. At 1-hour interval it shrinks to ∞/1h/2h/3h/5h. Shorter intervals allow all nine original values. RAW+Video removes the short interval choices 0.5s and 1s. Therefore the camera may validate duration against a *mode-dependent capability table*, not just uint32 width. Mimo displaying only ≤5h is consistent with such validation.

### Capture command is different
On Action 6, Timelapse start/stop is **DUML 02/01** payload `01` / `00`, with T14 real capture and original 3840×2880 HEVC file. Normal video start/stop uses **02/02**. **Do not confuse either with the official R-SDK accessory 1D03**; the latter is a different protocol family and cannot be used as proof of Mimo's command behavior.

## 2. Packet carrier and pairing, critical for controlled experiments

- DUML wire frame: `55 LEN_LOW VERSION/LEN_HIGH CRC8 SENDER RECEIVER SEQ_LE16 FLAGS CMDSET CMDID BODY CRC16_LE16`. App sender `02`, camera receiver `01`, typical request flags `40`, response `C0`. The CRC8 uses init `0x77`, reflected poly `0x8C`; CRC16 init `0x3692`, reflected poly `0x8408`. Reference [OpenPocketCine DUML format](https://opencapture.org/openpocketcine/docs/protocol/duml-frame/) and [Osmosis CRC implementation](https://github.com/KonradIT/osmosis/blob/main/app/src/main/java/dev/konraditurbe/osmosis/duml/DjiCrc.kt).
- Real Action 6 BLE observation: service `FFF0`, notify `FFF4`, write `FFF5`. GATT transport includes initial app approval/pairing `07/45`; subsequent Wi-Fi credential retrieval and data-link startup. See [OpenPocketCine Action 6 BLE](https://opencapture.org/openpocketcine/docs/devices/action-6/bluetooth/). **Do not hardcode Mimo behaviour from a different Osmo model.**
- Mimo communicates with Action 6 over Wi-Fi UDP **9004** data link for rich control/preview after BLE setup. Routing/window headers precede DUML. See [Action 6 connection reference](https://opencapture.org/openpocketcine/docs/devices/action-6/connection/) and [Osmo Client protocol](https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md).
- `02/6C` observed in **Mimo control session**; this does NOT prove that taking the naked 16-byte body and sending it straight to `FFF5` works. Use correct transport established by a captured successful exchange.
- Another independent source, [Osmo Client](https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md), independently documents `02/6C` with matching layout and `02/01` Timelapse START/STOP. Its README says that some other settings may accept non-advertised values, **but does not show a successful non-advertised Timelapse duration on Action 6**.
- `gui_autorecord_param` appears on a list of Mimo-subscribed **topic names** in [Osmosis MEDIA_PROTOCOL](https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md). **Important research lead:** find its contents and event timing under timed-shooting controls. The *name alone* does not prove scheduled or recurring capture; it may mean automatic recording on camera boot. Determine with A/B captures rather than assuming.

## 3. Device/firmware/app versions absolutely matter

- The September 2026 physical capture used camera firmware **01.02.05.21** and Mimo **2.12.0** on **iOS**.
- DJI's download center already lists July 22 2026 release notes; [OpenPocketCine normalized firmware table](https://opencapture.org/openpocketcine/docs/devices/action-6/specifications/) reports **01.05.08.03** on 2026-07-22.
- DJI's current [Mimo download center](https://www.dji.com/downloads/djiapp/dji-mimo) lists **Android 2.12.4** and **iOS 2.12.5** as of this research.
- Therefore all direct packet observations are firmware-specific. Capture your real Action 6 firmware version; do NOT infer current validation semantics from the older loaner survey.

## 4. Does Action 6 have a genuine native daily scheduler?

**Still UNPROVEN.** DJI Action 6 [v1.0 manual](https://dl.djicdn.com/downloads/DJI_Osmo_Action_6/UM/1104/DJI_Osmo_Action_6_User_Manual_v1.0_en.pdf) describes TimeLapse parameters, presets and SnapShot but no native autonomous **daily recurring alarm** in the examined UI instructions. Conversely, DJI's [Action 5 Pro marketing](https://www.dji.com/osmo-action-5-pro) advertises **scheduled shooting** that wakes at a preset time, but does not establish daily repetition on Action 6. Do NOT confuse scheduled-once shooting with daily recurrence or a finite Timelapse duration.

The **fastest proof** is a photograph of the actual Action 6 'daily' setting and whether the camera offers *Repeat: Every day*. Then capture only the start-time settings change, inspect DUML request/state, and map `gui_autorecord_param` or other relevant topics.

## 5. Firmware modification risk and reality

The official Action 6 [download center](https://www.dji.com/osmo-action-6/downloads) lists manuals/release notes, but no confirmed open firmware build chain or public custom firmware. Updates generally arrive via Mimo. No signed boot chain details, accessible restore partition or bricked-camera recovery is verified in this project.

**Do not flash** any edited firmware or untrusted payload before confirming secure boot/update signatures, available backup, recovery, RTC alarm support and persistent settings. A harmless protocol settings test is a much better first experiment than invasive firmware hacking.

If the camera supports the desired native daily schedule and accepts 28800s through `02/6C`, one-time external provisioning is sufficient and the phone/ESP32 is unnecessary at runtime. Otherwise a new *internal service* and wake timer would be required; changing 5h UI options alone cannot implement a missing scheduler.

## 6. Evidence-to-action decisions

| Experiment result | Meaning | Next step |
|---|---|---|
| `02/6C` 28800 → ACK E3/unsupported, state unchanged | Server-side validation likely | Do not retry blindly; research table/firmware branch |
| ACK00 → readback reverts to 18000 | Clamped by camera/UI or policy | Isolate immediate camera status vs Mimo display |
| ACK00 → readback 28800, reboot loses it | Temporary setting | Investigate custom preset retention and reboot semantics |
| ACK00 → readback 28800, reboot retains, capture lasts 8h | **Custom finite duration works** | Separately test native daily scheduling |
| 8h duration works, no RTC daily alarm | Not the requested finished product | Native scheduler feasibility remains blocker |
| RTC daily alarm exists, 8h unsupported | Use ∞ and native internal timed STOP if available | Test automatic stop and auto-off |
| No safe signed-firmware recovery | Firmware hacking still unsafe | Keep external solution as fallback |

## 7. What is actually implemented in this research branch

- `tools/mimo_action6.py`: standalone **offline-only** 16-byte 02/6C encoder, 21-byte `cam_lapse_param` decoder, normalized duration-capability parser, CRC8/CRC16 DUML scanner that filters out unrelated private packets.
- `tests/test_mimo_action6.py`: golden frame from OpenPocketCine, observed Action 6 example body, custom 8h, malformed data and CRC failures.
- `docs/MIMO_CAPTURE_PROCEDURE.md`: staged Android 15/Mimo capture and safe A/B experiment matrix.
- No camera connected, no BLE packet sent, no firmware patched, and **no claim of custom duration acceptance**.

**Licenses:** independently implemented decoding based on documented wire facts, not vendored source. Review license terms of upstream references separately before copy/pasting any code. Do not commit HCI logs, raw PCAPs, Wi-Fi SSIDs/passwords, PINs, tokens, precise GPS or camera MAC identifiers.
