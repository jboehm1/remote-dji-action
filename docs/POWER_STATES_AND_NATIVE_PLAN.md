# Action 6 power states and standalone 8h+ daily Timelapse: investigation (2026-10-29)

> **Research note, no hardware verification.** User preference: camera-only solution, with no ESP32 or Bluetooth remote needed in production.

## What DJI actually documents

1. **Normal powered-on Shutter/Record STOP:** stops recording. The [Action 6 user manual](https://dl.djicdn.com/downloads/DJI_Osmo_Action_6/UM/1104/DJI_Osmo_Action_6_User_Manual_v1.0_en.pdf) p.14 does **not** say that this puts the camera to sleep or fully off.
2. **Power-off-initiated SnapShot:** Manual p.14 and [DJI Action 6 FAQ](https://www.dji.com/osmo-action-6/faq) say recording starts from powered off when Shutter/Record is pressed and **after capture camera powers off after 3 seconds idle**. This guarantee is specific to SnapShot, not generic BLE STOP.
3. **Official DJI remote wake-and-record flow:** [DJI GPS remote Q&A](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/Q%26A.md) #2 and #6 say long record-button press can put camera to sleep, sleep/wake works via advertisement, Snapshot from sleeping camera can wake, shoot, then automatically **return to sleep**. This does **not** imply every Timelapse START/STOP follows this flow. BLE connection can remain active in sleep but wake temporarily disconnects it.
4. **Timelapse low-power moon icon:** [DJI Support](https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE&re=US&spaceId=17) explicitly says the low-consumption Timelapse mode **disables Bluetooth AND Wi-Fi while shooting**; display turns off after 10s. This is not the same as deep sleep at end of Timelapse. If enabled, naive BLE STOP at arbitrary end time probably cannot reach the camera until recording finishes. Do **not** promise the ESP32 prototype works with this mode.
5. **Finite Timelapse values:** [DJI specs](https://www.dji.com/osmo-action-6/specs) list 5/10/20/30 min, 1/2/3/5h and unlimited (∞). This does **not** establish any native *daily recurring start-time* function. Check whether user's 5h refers to duration within standard Timelapse or a separate scheduled/daily UI before assuming that extending 5h fixes recurring operation.
6. **DJI Mimo survey:** [OpenPocketCine Action 6 modes](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) documents a Mimo timelapse 02/6C payload with a LE32 duration and an advertised finite menu that ends at 18000 seconds. This only demonstrates serialization capacity; firmware acceptance of 28800 seconds and retained setting after power cycle **not proven**.

## Difference between camera states

| Transition | Documentation | Verified on Action 6 hardware here? |
|---|---|---|
| User stops a recording while camera is fully awake -> liveview/idle | Manual p.14 describes STOP only | No |
| SnapShot initiated while camera off -> stop -> auto power-off 3s | DJI explicitly documents it | No |
| Official remote wakes sleeping camera -> snapshot -> return to sleep | Official DJI remote SDK Q&A | No |
| Regular BLE Timelapse START with ∞ -> BLE STOP -> deep sleep | **No proof found** | No |
| Low-power Timelapse recording -> radio stays reachable by ESP32 | Contradicted by DJI low-power support note | No |

Terminology: screen off ≠ idle/liveview ≠ DJI remote sleep ≠ full power-off. All have different current draw and wake paths.

## Camera-only implementation investigation

**Stage 0, non-invasive UI check:** On the camera, photograph precisely the screen offering 'daily' and '5h', note camera firmware version and whether this is (a) native Timelapse **duration**, (b) custom scheduled capture, (c) recurring daily timelapse. Locate wake/RTC/alarm capabilities and whether end-of-shot auto-off is present. An 8h duration option by itself does **not** create daily recurrence.

**Stage 1, safe protocol-settings test:** Use non-flashing Mimo commands to write/read back a custom duration of **28800 seconds**, if supported, and verify if it persists through restart. Isolate control path (Mimo 02/6C ≠ DJI remote R SDK 1D03), write only a known reversible setting. Preserve originals and do not attempt factory reset. If camera rejects the value, record response and fall back safely.

**Stage 2, standalone scheduler:** Confirm a native daily repeat function or on-device schedule storage, how the camera wakes while off, and how it finalizes an MP4 and enters low-power mode when done. If there is no exposed native scheduler, extending the Timelapse duration cannot solve the user's full request. An on-camera firmware/service modification must integrate RTC alarms and resume after deep sleep.

**Stage 3, firmware modification feasibility:** Identify official Action 6 firmware package, signing/encryption/secure boot, disassembly legality and recovery options. Do not flash modified binaries without a tested restore method and explicit opt-in. No proven signing bypass/recovery currently.

**Stage 4, acceptance:** 08:00–18:00 for 7 consecutive days, independent of phone, ESP32, Internet or external schedule; verify end-of-day power state and overnight draw, next-day RTC wake, stored clips, storage/thermal alarms and interruption handling.

## Immediate experiment on real camera (no firmware hacks)
1. Set ordinary **Timelapse**, 5min duration, low-power moon icon OFF.
2. Start using normal on-camera record control, allow the duration to expire. Note status after 5 min and after another minute: screen on/off, physical power LED, button behaviour and wireless availability.
3. Repeat with moon icon ON (note BLE/Wi-Fi are expected off during recording).
4. Separately test **SnapShot from fully powered off** and record whether it actually powers off 3s after capture.
5. Compare standby/night battery draw by measuring current where practical, rather than inferring 'deep sleep' from the screen being black.
