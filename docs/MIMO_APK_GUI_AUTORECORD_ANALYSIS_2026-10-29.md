# DJI Mimo APK and `gui_autorecord_param`: evidence-level investigation (2026-10-29)

## Main answer

No publicly indexed source found in this investigation decodes `gui_autorecord_param` or ties it to **Action 6 Timer Shooting**. The literal name **DOES** appear in a captured DJI Mimo 53-topic subscription inventory (Osmosis), but that inventory was reverse-engineered on Nano / Action 5-class devices, not from a verified Action 6 schedule-setting capture. **Auto Record could instead concern the DJI Action 5/6 diving feature that automatically starts recording below a depth threshold.** This is a hypothesis, not a decoded mapping. Never send a write based on the name alone.

## Source provenance and exact meaning

| String / feature | Source | What is actually proven | What is NOT proven |
|---|---|---|---|
| `camcap_timelapse_duration` | Action 6 physical capture, 2026-09-21, firmware V01.02.0521, Mimo iOS 2.12.0: https://opencapture.org/openpocketcine/docs/devices/action-6/modes/ | Named capability table listing **9** allowed ordinary Timelapse durations: 0,300,600,1200,1800,3600,7200,10800,18000 seconds. Longer interval constrains this list further. | Firmware necessarily rejects non-listed duration; Timer Shooting task uses the same table. |
| `cam_lapse_param` | Same Action 6 capture; independent https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md | 21-byte readback of **ordinary Timelapse**; duration uint32 little-endian seconds at bytes 5..8. `02/6C` changes this state and has an explicit ACK. | This holds Timer Shooting daily schedule/alarm or controls the task runtime. |
| `gui_autorecord_param` | https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md, named among **53 Mimo subscription topics** | **Name exists on the `00/99` named-property bus** in that project's examined device/firmware. | Any bytes, structure, readback, write command, Action 6 support, or relation to scheduled shooting. No public decoded value found. |
| **Action 5 Pro diving Auto Record** | DJI FAQ https://www.dji.com/osmo-action-5-pro/faq | Camera can automatically start recording when diving below 1m, after enabling Auto Record in Depth & Altitude / Diving. | `gui_autorecord_param` specifically belongs to diving; the hypothesis is only a competing explanation. |
| **Timer Shooting** | 2024-10-16 DJI firmware notes: https://dl.djicdn.com/downloads/DJI_Osmo_Action_5_Pro/RN/20241126/DJI_Osmo_Action_5_Pro_Release_Notes_en.pdf ; hands-on: https://dronexl.co/2024/10/21/dji-osmo-action-5-pro-firmware-update-bitrate/ | Action 5 Pro was given **camera-side clock start, shooting mode, duration and Repeat**. User reports Action 6 already has daily Timer Shooting, with a 5-hour option. | Native task duration protocol encoded in `02/6C` or `gui_autorecord_param`. |

**Very important:** Camera capabilities and phone UI are separate. If a setting is configured ONLY on the camera touch screen, DJI Mimo may never send a SET for it. Capturing Mimo network packets while tapping the physical camera screen may show no relevant command. A read-only named-property push might still exist, but must be proven.

## Why `gui_autorecord_param` is suspicious, but not yet a lead with confidence

- Prefix `gui_` suggests camera firmware GUI settings, NOT necessarily DJI Mimo GUI.
- Suffix `autorecord` could mean record on dive threshold, camera power-on, remote trigger or schedule; there is no decoded data to disambiguate.
- Osmosis has the name in its **subscription list only**, without documented response value. It should not be promoted to a proven camera timer protocol.
- A strong A/B differential test is **Timer Shooting OFF versus ON**, then **scheduled 3h versus 5h**, then separately **Diving Auto Record OFF/ON**. Only if the same topic changes for Timer Shooting and not diving would this name become compelling.
- The camera can publish a status for an existing setting even if the phone cannot write it. Source and destination of a message matter.

## A/B property push protocol: DUML 00/99

Reference decoder: https://github.com/brianmerchant/Kaze-for-DJI/blob/main/docs/POCKET3_DUML_PROTOCOL.md

OpenPocketCine and Osmo Client identify camera push structures as:

```text
00/99 DUML body for one documented push variant:
02 06 00 00 [transaction:u32le] [5 bytes header]
[topic_name_length:u16le] [ASCII topic name]
[6 reserved 00 bytes] [value_length:u16le] [value bytes]
```

Subscription `02 02` uses a related format and sometimes a name-length offset two bytes later. Our parser verifies an ASCII topic and lengths rather than interpreting arbitrary bytes as schedule data.

Safe offline analysis:

```sh
python3 tools/duml_topic_audit.py topics /path/to/private-capture.pcapng
python3 tools/duml_topic_audit.py diff /path/to/timer-3h.pcapng /path/to/timer-5h.pcapng
```

This searches for **contiguous CRC-valid** DUML frames in opaque data and reports targeted topic bodies and byte differences only. It is not a full PCAP/HCI reassembler and cannot prove absence of a topic when packets are fragmented.

## APK feasibility, actual state

Latest DJI official Android Mimo listing: **2.12.4**: https://www.dji.com/downloads/djiapp/dji-mimo ; the Samsung Galaxy Store entry dated 2026-10-12 lists ~**991 MB**, and APKMirror's 2.12.1 archive lists **1.30 GB**. We did NOT receive an APK in this conversation. The current container cannot resolve internet hostnames for downloading a nearly 1GB proprietary APK, and JADX is not installed. **No DJI Mimo APK was downloaded or decompiled.** Do not present our scanner as an APK analysis result.

### What has now been implemented, without needing JADX

`tools/inspect_mimo_apk.py`: reads a legitimate locally provided APK **directly as ZIP** and extracts:

- Android **DEX string_ids** entries from `classes.dex`, `classes2.dex`, etc. (without executing anything);
- Android `resources.arsc` text labels (UTF-8/UTF-16 string pools);
- **native ELF .so** ASCII occurrences (important if DJI protocol codecs reside in JNI libraries);
- ZIP-entry names, only for matching terms. Reports source entry, location and index, not full proprietary decompilation.

Targets exact names `camcap_timelapse_duration`, `cam_lapse_param`, `gui_autorecord_param`, plus English UI labels and decimal strings `18000`, `21600`, `28800`, `36000`, `43200`.

```sh
python3 tools/inspect_mimo_apk.py /local/path/DJI_Mimo.apk --output local-private/mimo-audit.json
python3 -m unittest discover -s tests -p 'test_mimo_native_settings.py' -v
```

### What APK string inspection CANNOT do

- **Numeric constants** such as 18000 embedded as literal DEX bytecode/ELF constants generally do NOT appear in the string pool. A zero-match does not prove they are absent.
- Obfuscation, string encryption, runtime reflection or dynamic loading may hide names.
- A string in app code does not prove it is used for Action 6.
- Camera-local Timer Shooting validation can happen entirely in camera firmware. Modifying the Mimo APK would not change firmware's advertised capabilities or internal RTC alarms.
- A duration can be stored in a calendar/alarm service binary with no Mimo involvement.

### Next level static code analysis when APK is locally available

1. Check package certificate/signature/version, SHA256 and `classes*.dex` inventory.
2. Run fast scanner above to locate strings in APK/DEX/resources and native .so.
3. Run JADX (`jadx --no-res -d local-private/mimo-jadx /path/to/DJI_Mimo.apk`) for Java/Kotlin call-site analysis, then `tools/inspect_mimo_jadx.py`.
4. In JADX, trace xrefs from `camcap_timelapse_duration` and `cam_lapse_param` to command builder and `02/6C`; locate any Timer Shooting UI keys. For native .so hits inspect function xrefs with Ghidra/IDA locally, not in GitHub.
5. Specifically compare Timer Shooting, scheduled-shot, daily-repeat, deep-water Auto Record menu strings and related public firmware versions; record all candidate DUML command set/id **with observed caller**, not speculated offsets.
6. Use a physical Action 6 for a **non-destructive** 3h↔5h scheduled task readback and eventual 8h write; preserve original setting.

## Specific outcome as of 2026-10-29

- **Confirmed:** two Action 6 ordinary Timelapse property names/encodings; `gui_autorecord_param` appears in Mimo subscription names in another Osmo model study.
- **Not confirmed:** `gui_autorecord_param` semantics; Timer Shooting duration setter; camera ability to accept scheduled 8h; any modification to DJI Mimo APK or device firmware.
- **Project recommendation:** prioritize the correct on-camera **Timer Shooting** task, with a deliberate diving-Auto-Record control experiment to avoid false positives.
