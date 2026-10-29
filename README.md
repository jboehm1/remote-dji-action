# DJI Osmo Action 6 — autonomous daily Timelapse research

**Desired end state:** configure the **Action 6 itself** once, then let it independently wake at (say) 08:00, record a real native Timelapse for 8–12 hours, stop at 18:00, finalize its video, enter power-saving sleep, and repeat daily **without any ESP32, phone, or network attached**.

**Current state: protocol research and offline tooling, NOT a working camera hack.** The existence of a 32-bit duration field does **not** prove the camera accepts an 8-hour value; an 8-hour timer does **not** create an internal recurring alarm. Hardware verification and a safe recovery strategy are mandatory before claiming a finished solution.

## Important research correction: native Timer Shooting is the real target

DJI introduced **Timer Shooting with Repeat** in Action 5 Pro in October 2024, and you report the Action 6 already provides daily scheduled captures up to 5 hours. That means our priority should be **extending the duration of the native scheduled job**, not just the 02/6C ordinary Timelapse setting. The on-wire schedule duration setter is **not yet known**. The existing 8-hour encoder is a hypothesis for ordinary Timelapse only. See [historical out-of-menu evidence audit](docs/HISTORICAL_OSMO_FORCED_SETTINGS_2026-10-29.md).

## Key research discovery — DJI Mimo's 8-hour field

On a physical Action 6 running firmware **V01.02.0521** and iOS DJI Mimo **2.12.0**, [OpenPocketCine's detailed capture survey](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) documented camera-accepted **DUML 02/6C** Timelapse settings messages and matching `cam_lapse_param` readbacks.

```text
DUML command: set 0x02, command 0x6C
16-byte settings payload:
04 00 | save | interval:u16_le (tenths sec) | duration:u32_le (seconds) | 7 zero bytes

Example: video, 10 s interval, 8h duration:
04 00 00 64 00 80 70 00 00 00 00 00 00 00 00 00

8h   = 28,800 seconds (LE u32: 80 70 00 00)
10h  = 36,000 seconds (LE u32: A0 8C 00 00)
12h  = 43,200 seconds (LE u32: C0 A8 00 00)
∞    =      0 seconds (LE u32: 00 00 00 00)
```

**Important:** the observed camera capability list contains only 0, 300, 600, 1200, 1800, 3600, 7200, 10800, **18000** seconds. **28800 has NOT been sent or acknowledged on an Action 6** in this project or the identified source captures. DJI Mimo communicates over BLE to establish connections and often Wi-Fi/UDP port 9004 for subsequent DUML control: a 16-byte payload alone is not a writable Bluetooth packet.

## Primary documentation

- [Deep reverse-engineering report](docs/MIMO_REVERSE_ENGINEERING_2026-10-29.md): capture evidence, exact bytes, frame and CRC, status topics, version caveats, 8h feasibility, native RTC scheduling, and rollback gates.
- [Android capture and safe test procedure](docs/MIMO_CAPTURE_PROCEDURE.md): Bluetooth HCI snoop/ADB and network PCAP capture, how to isolate 5h/∞ settings changes and readback, privacy cautions.
- [Offline DUML research tool](tools/mimo_action6.py): constructs an 8h settings **payload**; parses verified 0x55 DUML frames from saved binary; decodes `cam_lapse_param` and count-prefixed duration capability lists.
- [Unit-test source](tests/test_mimo_action6.py): published golden wire frame, CRC, Action 6 600s example, 8h hypothesis, malformed messages.
- [Mimo APK static investigator](tools/inspect_mimo_jadx.py): locally index relevant strings in a legitimately obtained JADX-decompiled DJI Mimo APK, without copying APK or decompiled code to GitHub.

## Minimal offline commands (no camera interaction)

```sh
python3 tools/mimo_action6.py proposal --interval 10 --hours 8 --show-frame
python3 tools/mimo_action6.py proposal --interval 10 --hours 10
python3 tools/mimo_action6.py proposal --interval 10 --hours 12
python3 -m unittest discover -s tests -p test_mimo_action6.py -v

# Use only on a copy of an authorized, locally stored traffic capture:
python3 tools/mimo_action6.py scan ./local-private/camera_capture.pcapng
```

The scanner only reports complete, CRC-valid 0x02/0x6C frames; it does **not** reassemble split packets, act as a full PCAP parser, or transmit new commands.

## Two independent blockers

1. **Finite >5h acceptance.** A LE32 field holds 28,800, but on-camera validation and persistence after reboot have not been demonstrated; a reversible protocol test is needed.
2. **Daily recurrence + sleep/wake.** Even a successfully changed duration does not prove the Action 6 has a daily RTC alarm or automatically powers down after normal Timelapse. Investigate the actual menu and named `gui_autorecord_param` notification, if present. A modified internal service would require a safe firmware restore/recovery strategy, currently unverified.

DJI documents **∞** Timelapse already, so an internal daily timer could theoretically start ∞ at 08:00 and stop at 18:00 without any new finite duration option. This remains a design hypothesis, not a feature we have found in firmware.

## Status / work branches

- `research/mimo-action6-protocol`: **primary camera-only investigation** (this branch).
- `feat/esp32-daily-timelapse`: earlier *fallback* ESP32 prototype, untested on camera; not the preferred deployment.
- No signed camera firmware patched, no 8h values written to a real camera, no physical hardware tested.

References: [OpenPocketCine](https://github.com/erik-sutton95/OpenPocketCine), [Osmo Client](https://github.com/luisreysan/osmocam), [Osmosis](https://github.com/KonradIT/osmosis), [DJI Action 6 specs](https://www.dji.com/osmo-action-6/specs).

**Privacy:** keep raw HCI/PCAP files, camera MACs, pairing tokens, Wi-Fi credentials and unredacted Android bug reports out of Git.
