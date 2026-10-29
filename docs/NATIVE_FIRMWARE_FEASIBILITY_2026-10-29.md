# Action 6 native / no-extra-device daily Timelapse feasibility — 2026-10-29

**User's priority:** No ESP32, phone or external scheduler needed while deployed. The camera autonomously starts a real Timelapse daily, runs for >=8 hours, finalizes the MP4, and returns to a power-saving state until the next day. A settings change for 8h alone is NOT daily scheduling.

## Evidence (separate documented facts from hypotheses)

| Item | Evidence | Conclusion |
|---|---|---|
| Timelapse time options include 5h finite and ∞ | https://www.dji.com/osmo-action-6/specs | 5h is a menu limit, not a demonstrated continuous-record limit |
| Mimo 02/6C 16-byte Timelapse settings body has LE32 duration | https://opencapture.org/openpocketcine/docs/devices/action-6/modes/ | 28800 can be represented but **acceptance not shown** |
| Camera enumerates durations 0,300,...,18000 seconds | OpenPocketCine same research, T13 cap `camcap_timelapse_duration` | 8h not advertised; 0 = ∞ |
| Native daily recurring schedule, RTC wake from full off | No supported operation found in the DJI Action 6 v1.0 user manual, official specs, firmware release notes reviewed | **Not documented**, not proof of impossibility. Must check actual Action 6 firmware UI |
| Press STOP on powered-on camera | Manual p14 only states recording stops | Automatic full shutdown **not proven** |
| SnapShot started from full off | Manual p14: after capture, auto power-off after 3 seconds idle | Works for special SnapShot origin, NOT generic remote STOP |
| Timelapse moon low-power mode | https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE&re=US&spaceId=17 | Bluetooth and Wi-Fi **disabled during shooting**. External BLE STOP is not assured |
| Official BLE sleep/wake advertisement restriction | https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/protocol_data_segment.md — Camera Power Mode Settings 001A | DJI's reference says remote connection must have happened recently and sleep must be **<=30 min** for wake packet, illustrated for Action 4/5. Applicability to Action 6 still requires direct test. Do NOT assume remote overnight wake |
| Official controller supports Action 6 sleep/wake buttons | https://repair.dji.com/help/content?customId=01700008289&lang=en&paperDocType=ARTICLE&re=US&spaceId=17 | Presence of manual wake/sleep does not prove 12–16 hour overnight sleep and automatic reconnection |
| Public firmware package / bootloader recovery | DJI public Action 6 download-center page lists release notes, manual, safety/quick start, not an obvious user-installable firmware binary; FAQ describes firmware pushes through Mimo | No verified reversible custom-firmware path yet. Do not patch blind |
| Official battery | Action 6 specifications: 7.5 Wh, 1950 mAh | Controller should be budgeted separately from the far larger unknown camera 10h draw |

## Technical paths to a camera-only product

### Path 1 — Native scheduler already present, custom duration SET
1. Record a video or photos of the actual 'daily' / '5h' UI on Action 6 and firmware version.
2. Distinguish standard **Timelapse duration** from **scheduled recurring shooting**.
3. If *genuine* native daily schedule exists, try a **non-flashing protocol write** of 28800s through the matching DJI Mimo protocol (02/6C), obtain ACK and state readback, power-cycle and check persisted setting.
4. Verify 8h real media file, schedule recurrence, daytime stop, shutdown, next-day wake.
5. If ACK fails or duration clamps to 18000, record it; DO NOT claim a working setting hack.

**Risk:** Moderate protocol/setting risk, low camera-brick risk, **conditional on native daily scheduler actually existing**.

### Path 2 — Patch a user-accessible config / preset
Determine whether the selected duration is stored in writable exported presets/config files. DO NOT assume. A writable config that stores `duration=28800` may be accepted only if camera validates against capability list. Test copying/restoring settings and power-cycle; never inject arbitrary untrusted file. This may extend a single session but won't create daily RTC alarms by itself.

### Path 3 — True camera firmware intervention
If no native daily scheduler exists, need both:
- A background local scheduler using RTC/time-zone and persistence across power-loss
- A reliable internal wake source, start-Timelapse service, finish/finalize, transition to safe standby
- Optional new 8/10/12h menu choices or numerical duration field; `∞` plus scheduled stop could work too

**Prerequisites before modifying firmware:**
- Find camera hardware chipset and boot chain from actual device/verified firmware, not a guess.
- Obtain legally redistributable/researchable correct firmware image, cryptographic signature/auth requirements, partition layout, configuration persistence.
- Confirm diagnostic access, signed update requirement (don't extrapolate drone secure-boot design to Action 6 without evidence), exact power/RTC owner.
- Create a tested, nondestructive recovery route before *any* write. Full restore and fail-safe power-loss test.
- Only proceed with physical camera and an explicit approval for modification risk.

As of this research no verified Action 6 custom firmware, unsigned image loading path, or restoration procedure is available in-project. **Firmware modification is therefore NOT ready.**

### Path 4 — Alternative camera supporting internal scripting
This would sacrifice user's preference for Action 6. GoPro Labs firmware has documented clock-conditionals, in-camera daily repeat scripts and sleep/wake, but is GoPro-only (https://gopro.github.io/labs/control/tech/). It is a useful benchmark for the **required architecture**, not code that can run on DJI hardware.

## Decision table: functionality must pass all columns

| Candidate | 8/10h | Repeats daily | Overnight low power | No external electronics |
|---|---:|---:|---:|---:|
| Action 6 ordinary finite duration ≤5h | No | Not shown | Not shown | Yes |
| Action 6 Timelapse ∞, manually controlled | Yes subject to power and storage | No | No scheduled daily stop | Yes (manual) |
| Mimo 02/6C write `28800` | Unknown | No unless native repeat independently exists | Unknown | Yes *after* initial setup |
| In-camera firmware scheduler patch | Theoretical | Theoretical | Requires RTC architecture | Yes |
| ESP32 BLE scheduler | Potential | Potential | Overnight BLE wake/camera STOP restrictions | **No** |

## Hardware protocol test matrix

Do not substitute code compilation or SET ACK for a proof of successful 8h recording.

**Non-destructive, short tests first:**
- Native Timelapse 5-min timed capture, moon mode ON/OFF: measure end-of-session power draw and BLE discoverability. This determines if the *camera*, not just ESP32, remains awake.
- SnapShot from full OFF: repeat and compare current draw 3 seconds after STOP.
- Remote sleep and wake 5/20/40/90 min and after **14h** on Action 6: record BLE response, power state, exact firmware. Official generic demo reports a 30-minute limit.
- Start Timelapse ∞ via official remote 1D03, try STOP while moon mode ON/OFF; record 1D02 status and actual saved MP4 (no fake acknowledgements).
- Use Mimo 02/6C only after capturing a baseline known-good frame; try `28800`, read back and test persistence after restart.
- Only when all above is safe: 8h, 10h and seven-day start/stop/power-cycle proof.

## What this investigation can and cannot conclude

- We can **prove** the vendor has an unlimited setting and the SDK has distinct status/power controls.
- We **cannot yet prove** an Action 6 native daily scheduler exists, supports modified settings, or that a firmware modification is safely flashable. Claiming otherwise would overstate current findings.
- We **can already flag** the external ESP32 strategy as blocked for unattended overnight scenarios until the 30-minute BLE wake rule and low-power radio-disabling are tested on real Action 6.
