# Action 6 + DJI Mimo: controlled capture and safe protocol verification

**Hardware requirement:** one real DJI Osmo Action 6, an Android phone (Samsung S21 on Android 15 can be used), USB debugging and development PC. **Nothing in this document flashes firmware or sends modified commands.** One-time external diagnostic hardware is allowed: the final product should operate autonomously.

## Experiment matrix (change only one UI setting per capture)

| Label | Camera/Mimo action | What to find in decoded trace |
|---|---|---|
| S0 | Record exact installed firmware and Mimo version; **no setting change** | Calibration baseline; don't assume captured firmware matches OpenPocket survey |
| S1 | Select Timelapse, 10s, Video, **5h** | `02/6C` body `04 00 00 64 00 50 46 00 00 ...`; status `cam_lapse_param` duration 18000 |
| S2 | Select Timelapse **∞** | `02/6C` same except 4-byte duration = zero; readback zero |
| S3 | Select Timelapse **1h** | `02/6C` duration = 3600 `10 0e 00 00`; readback matches |
| S4 | Navigate any camera **timer/scheduled shooting** page and change **start time only** (if present) | Correlate request set/id and named status topic with alarm timestamp, check for daily repeat options |
| S5 | Stop/restart Mimo, power-cycle CAMERA, inspect selected values | Prove persistence or reset; never infer from UI without camera status |
| S6 | On a separate short 1–2min test, timed Timelapse finishes moon mode OFF/ON | Does it turn off, idle, or radio sleep? Camera energy measurement, not screen alone |

### Prerequisites / capture hygiene
- Do not update firmware in the middle of tests. Write down full camera firmware number (Settings / About), Mimo version, OS version and time zone, noting DST; if you later update firmware, label a new capture series.
- Use an unimportant SD card / backed-up contents; avoid file deletion and reset operations.
- Avoid pairing prompts with screen recording visible publicly (PINs), SSID/password or network traces in GitHub. No raw sensitive logs committed. Prefer only sanitized command families or JSON summaries.
- Record visible camera status and settings before and after each action; audio/screenshots can identify exact button presses.
- Capture each individual operation separately, e.g. at precise event times, so matching DUML frames have clear causality.

## Android Bluetooth HCI capture

1. Open **Settings > About phone > Software information**, tap Build number 7 times to enable Developer options (if not already enabled).
2. In **Developer options**, enable **Bluetooth HCI snoop log**; turn Bluetooth off/on or reboot if Android requests it.
3. Connect the camera via Mimo. Capture S0–S4, then stop logging. On some devices a `/sdcard/btsnoop_hci.log` file exists; many newer Android/Samsung builds instead include it in a bug report under `FS/data/misc/bluetooth/logs/`. Confirm using a short test first.
4. On computer with Android Debug Bridge, run:
   ```sh
   adb devices
   adb bugreport action6_mimo_capture.zip
   unzip -l action6_mimo_capture.zip | grep -iE 'btsnoop|bluetooth.*log'
   ```
   If `/sdcard/btsnoop_hci.log` exists and is readable, copy it:
   ```sh
   adb pull /sdcard/btsnoop_hci.log ./
   ```
   Do NOT assume any device provides this path. A bug report can contain personal information, account identifiers and tokens: store locally only. **Never upload a complete bug report to GitHub.**

Bluetooth HCI traffic often contains the pairing and Wi-Fi credential/bootstrap phase; **02/6C may instead appear on the Wi-Fi data link**, after Mimo connects to the camera AP.

## Android Wi-Fi DUML capture (Mimo controls)

Use [PCAPdroid](https://github.com/emanuele-f/PCAPdroid) in non-root VPN-capture mode, filtered to DJI Mimo and the camera's local IP, when possible. Android Mimo generally accesses the camera at `192.168.2.1`; verify this from the active Wi-Fi gateway, do not assume on every network.

**Non-root limits**: PCAPdroid recreates L3/L4 headers, may change packet boundaries, and can miss links that bypass the VPN or do not route through it. It does not capture Bluetooth. If Mimo disconnects or UDP control packets do not appear, stop instead of forcing incompatible settings. A rooted device / Wi-Fi monitor / capture on a supported host can provide a truer radio/network picture, but is NOT required for first protocol research.

OpenPocketCine's physical Action 6 Mimo survey used an iOS network capture plus PacketLogger; the observed control traffic was UDP port **9004** after BLE bootstrap. Protocol messages can be embedded in extra routing/window headers, so our scanner searches for CRC-valid DUML records.

## Offline parsing after capture

One frame known to be valid (OpenPocketCine's public test vector):
```text
55 11 04 92 02 01 00 a0 40 02 0c 01 01 00 01 b6 3b
```
Reproduce a simulated 8h **payload** (no transmission):
```sh
python3 tools/mimo_action6.py proposal --interval 10 --hours 8
python3 tools/mimo_action6.py proposal --interval 10 --hours 10
python3 tools/mimo_action6.py proposal --interval 10 --hours 12
python3 -m unittest discover -s tests -p test_mimo_action6.py -v
```

For a **raw binary trace** with DUML frames embedded (could be a .pcapng, HCI capture or DUML raw bytes), the scanner extracts only full CRC-verified frames:
```sh
python3 tools/mimo_action6.py scan ./local-private/session-s1.pcapng
```
**Limitations:** it does not reassemble packets split across boundaries and cannot guarantee every DUML packet is found in HCI/PCAPNG. A dedicated HCI reassembler or a UDP reassembler may be required for complete traffic analysis. It intentionally does NOT output credentials, nearby device identities or arbitrary raw packet bodies.

Decode a known **21-byte cam_lapse_param data** (not the full `00/99` wrapper):
```sh
python3 tools/mimo_action6.py readback --hex "00 64 00 05 00 80 70 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
```

## After baseline is reproduced: the minimal 8h intervention

**Only after verifying matching real Action 6 SET/ACK and state on current firmware:**
1. Keep original settings to restore.
2. Reuse the **same proven carrier** (Wi-Fi datalink or Mimo BLE where observed), sender/receiver, sequence and frame CRC handling. No random command sweeps.
3. Send a single, controlled `02/6C` with one changed field: 18000→28800 while preserving interval/save format/trailer.
4. Inspect reply code and `cam_lapse_param` readback **immediately** (status push is authoritative), then reboot and inspect persistence.
5. If accepted, test **short controlled state changes** first, then an actual 6h/8h recording, and independently investigate scheduled daily recurrence. No 8h running test on internal battery alone.
6. If rejected, do not brute-force fields. Examine `camcap_timelapse_duration` validation and UI preset serialization, never flash camera without full recovery plan.

**Current state:** The project contains offline packet tools and published research, but there is **NO live 8h write implementation and NO camera acceptance result**.

## Useful official/community references

- https://opencapture.org/openpocketcine/docs/devices/action-6/modes/
- https://opencapture.org/openpocketcine/docs/devices/action-6/bluetooth/
- https://github.com/luisreysan/osmocam/blob/main/docs/PROTOCOL.md
- https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md
- https://developer.android.com/studio/debug/dev-options
- https://source.android.com/docs/core/connect/bluetooth/verifying_debugging
- https://emanuele-f.github.io/PCAPdroid/quick_start.html
