# Action 5 Pro on-camera Timer Shooting: investigation and reversible validation plan

**Updated:** 2026-11-03. **Status: not implemented or tested on our physical camera.**  
**Companion map:** [Osmo open-source projects and historical models](OSMO_OPEN_SOURCE_ECOSYSTEM_2026-11-03.md).  
**Authority:** research/documentation only. The user has not authorized bootloader unlock, root deployment, overwriting DJI binaries, flashing or erasing partitions.

## Manufacturer-confirmed native wake (priority update)

[DJI's Action 5 Pro product page](https://www.dji.com/osmo-action-5-pro) states that **Timer Shooting can wake the camera at its set time and start capture in the preset mode**. The native schedule/wake system therefore exists on stock Action 5 Pro. This is stronger evidence than any speculative Linux `cron`/`systemd` wake. It does **not** document a 10 h task duration or disclose how to change its limit. Our first priority is to preserve this working native path while identifying the *separate scheduled-task* duration field; an on-camera companion daemon is only a fallback if we can prove it remains running or can safely wake.

**Latest code:** [read-only, offline ELF/string/LE32 Timer Shooting scout](ACTION5_OFFLINE_NATIVE_SCOUT.md) and five synthetic regression tests. No device access or code flashing is performed by the tool.

## 0. First answer: what does the discovered Action 5 root project actually change?

**[AlliotTech/action-control](https://github.com/AlliotTech/action-control) is not an alternate DJI firmware image.** It is user-created, open-source software running as an additional service **on the Action 5 Pro's own Linux OS**; the proprietary DJI programs and shared libraries remain compiled (no DJI source tree is published). The installer requires an **already bootloader-unlocked camera with root ADB**, and can install a firmware-hash-guarded rear GUI extension. The author performed **binary disassembly / symbol and offset analysis** and then invoked the *existing* DJI Binder camera API from a native adapter. Unlike remote software, it starts/stops DJI recording *locally*, preserving official encoder/media writing. See [README](https://github.com/AlliotTech/action-control/blob/main/README.md) and [NATIVE_CAMERA_REUSE.md](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md).

This proves **some** original camera services are callable without Mimo and without rewriting the entire firmware. It **does not yet prove** an undocumented Timer Shooting task setter, accepted 8 h, Linux RTC wake while powered off, or compatibility with the owner's current firmware.

Three possible implementations, in increasing risk:

1. **Settings-only extension:** the native scheduler accepts `28800` but its UI advertises a maximum `18000`. Identify and update only the **correct scheduled-task** value or menu option, and confirm the service really honors it. No proof yet.
2. **Native scheduler task interface:** the internal task setter validates the menu list, but the correct scheduler service/API is callable. Investigate an 8 h task via a narrowly scoped, reversible **settings** operation. No proof yet.
3. **Own on-camera companion service:** schedule DJI's proven native `camera_start_recording`/`camera_stop_recording` calls using a local clock. This does not require altering DJI executables, but **requires proven native Timelapse mode, session ownership, sleep and RTC wake**; systemd/cron is not a hardware wake source.

Do not assume the lowest-risk approach is available before the source evidence identifies the true limitation.

## 1. Actual variables/properties discovered upstream

| Name / command | Source with direct evidence | What it means | What it does **not** mean |
|---|---|---|---|
| `camcap_timelapse_duration` | [OpenPocketCine Action 6 Mimo capture](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) | Capability list includes 0=∞ and finite `{300, 600, 1200, 1800, 3600, 7200, 10800, 18000}` seconds | Not a firmware-C variable name; not evidence that Action 5's Timer Shooting duration is this property |
| `cam_lapse_param` | Same Action 6 capture; [Osmosis topic map](https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md) | Current *ordinary Timelapse* interval/duration observable via protocol | Not a decoded repeating schedule |
| DUML `02/6C` | [OpenPocketCine](https://opencapture.org/openpocketcine/docs/devices/action-6/modes/) and [Kaze protocol notes](https://github.com/brianmerchant/Kaze-for-DJI/blob/main/docs/CAMERA_SETTINGS_PROTOCOL.md) | Ordinary Timelapse settings payload includes 16-byte body and a LE32 seconds duration; 8 h encodes as `80 70 00 00` | Bytes fitting `uint32_t` do **not** prove the camera accepts values outside its advertised menu |
| `gui_autorecord_param` | [Osmosis subscription-name list](https://github.com/KonradIT/osmosis/blob/main/MEDIA_PROTOCOL.md) | Genuine named subscribed property from Mimo, **not decoded** in available documentation | **Cannot yet assert** it governs Timer Shooting or Repeat, nor its setting format |
| `camera_start_recording`, `camera_stop_recording`, `camera_get_record_state` | [Action Control native adapter/disassembly](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md) | Locally callable compiled DJI camera Binder client on *some rooted Action 5 Pro firmware* | Not proof of selected Timelapse vs video, native future scheduled wake, or duration adjustment |

These are **protocol/topic/function names**, not evidence that we have the private DJI source code. Native symbol names and function offsets are firmware-specific and need hash matching.

## 2. Best next experiment: isolate the *actual* five-hour field, without root

Perform this on the **Action 5 Pro itself**, not a simulator. Preserve firmware version, Mimo version, locale/time zone and exact capture preset. Run all tests with stable power and sufficient SD space. Do not capture/commit secrets or raw pairing logs.

| Test | Change on camera/Mimo | Observe | Expected information |
|---|---|---|---|
| **A0 baseline** | Ordinary Timelapse = `1 s`, `∞`, chosen format; Timer Shooting **Repeat daily**, 08:00, **3 h** | Controlled Mimo request/reply/topic stream; camera screenshot | Known starting task and normal Timelapse `cam_lapse_param` |
| **A1 duration delta** | Change **only Timer Shooting duration 3 h → 5 h** | Compare CRC-valid commands, ACK and named property updates | **Primary discovery:** scheduled-task setter/property, whether `gui_autorecord_param` changes |
| **A2 ordinary delta** | Restore 3 h native task; modify **only ordinary Timelapse duration** `∞ → 5 h` | Compare with A1 | Distinguish `02/6C` from independent Timer Shooting command |
| **A3 alarm delta** | Native task start time **08:00 → 09:00**, keep 3 h | Compare changed fields | Identify start-time encoding and local vs UTC behavior |
| **A4 Repeat delta** | Toggle Repeat daily, keep all other values | Compare changed fields | Identify recurrence flag, task persistence and schedule format |
| **A5 reboot read-only** | Power-cycle normally and reconnect Mimo | Native GUI task data, status, clip times, persistence | Is task stored by camera and does it operate without phone? |
| **A6 end-of-session power** | Use **shortest native task** with external USB wattmeter; check camera when task ends | Power/current, Wi-Fi/BLE discovery, time to sleep/off | Is the native timer power-efficient and does it maintain future wake? |

Action 5 owner may need an Android Mimo BLE HCI capture and/or local Wi-Fi UDP capture; use the existing [`docs/MIMO_CAPTURE_PROCEDURE.md`](https://github.com/jboehm1/remote-dji-action/blob/research/mimo-action6-protocol/docs/MIMO_CAPTURE_PROCEDURE.md) procedure, adapting it to **Action 5 Pro** and carefully filtering private fields. Do not confuse a network packet containing `02/6C` with the complete 3h→5h task delta.

### What would establish that 8 h is really possible?

Only if A1 reveals the true task setter and **all** of the following pass:

1. Unmodified baseline and revert path are saved on the camera, and operator explicitly approves one controlled **28800-second** test. No blind brute-force values.
2. Correct task SET request gets valid ACK **and camera task readback = 28800 s**; original Timelapse settings unchanged.
3. The native Timer Shooting UI/status remains coherent after reboot and the camera **actually records more than 5 h** when started by its own timer (confirm saved MP4/media metadata).
4. It stops at the configured end, retains Repeat, enters a measured low-power state and **wakes itself next day** without any host; verified several cycles and a 7-day final soak.

A request ACK without readback or a `02/6C` ordinary-duration success does **not** satisfy these criteria.

## 3. If Mimo A/B capture is insufficient: read-only root research gate

**Do not start this on the user's camera until model-specific recovery and permission exist.** [Action Control](https://github.com/AlliotTech/action-control) openly requires unlock/root; its repository **does not provide the unlock operation**. The author's [blog article](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) is a lead, not a tested recovery procedure here.

After owner explicitly accepts the risk and a working return-to-stock/recovery path has been independently demonstrated on an identical model/firmware:

1. Inventory firmware `version`, chip/board identity, partition layout, kernel, all relevant ELF and shared-object **hashes**. Record an exact branch/version matrix; do not infer binary offsets from another firmware.
2. **Read-only** discover files and internal message names associated with `autorecord`, `timer`, `schedule`, `repeat`, `duration`, `lapse`, `alarm`, `wakeup`, `rtc` and GUI model. Start with string references/call graphs (Ghidra/radare2). Avoid publishing full proprietary ELF blobs.
3. Cross-reference Mimo A1/A3/A4 traffic with native service events and GUI callbacks. Identify which component owns (a) task options, (b) persistent task setting, (c) recording start/stop and (d) RTC/PMIC wake.
4. Treat an **8 h GUI choice** as separate from the **service accepting 8 h**. Identify both validators. Prefer supported/private API or user-configurable file to raw binary overwrites. Keep original signed system binaries intact.
5. If no native Timer Shooting setting is writable, investigate Action Control native camera service as an **optional on-camera companion**. Confirm mode=Timelapse and genuine MP4 capture, avoid stopping manually started sessions, and prove 14–16h sleep/wake before calculating a low-energy daily schedule.
6. No flashing/replacing partitions, `dd` writes, root persistence modifications, OTA interception or bootloader changes until a separate safety review and explicit approval.

**Most relevant existing internals:** Action Control's [native Binder reuse notes](https://github.com/AlliotTech/action-control/blob/main/docs/NATIVE_CAMERA_REUSE.md) document stable *for their verified library hashes* status getter, `camera_start_recording`, `camera_stop_recording`, mode-profile and GUI extension. They report native recording **3→1→3** plus actual clip creation. The vendor API still owns encoding, heat/storage policy and save format. It does **not** currently document Timer Shooting's own task schema.

## 4. Sleep and power-state fault tree

We should not promise the camera can shut fully down at 18:00 and self-start next morning just because a custom local service exists.

| Night state | Does custom Linux process run? | Can it wake itself in morning? | Evidence requirement |
|---|---|---|---|
| Camera stays booted, screen black | Possibly | Clock service can trigger if Linux remains awake | USB wattmeter at 18:05 / midnight / 07:55, kernel uptime/logs |
| Camera enters suspend | Usually **not while suspended** | Needs working RTC wakealarm / PMIC owner | Controlled wakealarm and verified post-suspend state |
| Camera enters deeper vendor low power | Unknown | Requires undocumented vendor wake mechanism | Original native Timer Shooting wake trace / power measurement |
| Camera is fully off | No | Generic `cron` or `systemd` task **cannot execute** while off | Demonstrated hardware RTC/PMIC boot alarm |
| External ESP32 broadcast wake | External controller alive | DJI reference only documents recent pairing and sleep **≤30 min** for particular wake path | Action 5 40 min / 2 h / 14 h real tests, version reported |

Additionally, DJI [Low Power Timelapse](https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE) turns off Wi-Fi **and Bluetooth** during capture, so a remote R SDK `STOP` cannot be assumed to work in moon mode. An internal native task may retain efficiency; measure it.

## 5. Deliverables and hard stop conditions

Required measurements for a factual result:

- Camera: firmware/build, model AC204, Mimo version, task mode, 1 s or 2 s interval, native Moon mode, temperature/ventilation, active power source, storage.
- Protocol: exact scrubbed command/topic, direction, 3 h baseline, 5 h delta, ACK, independent camera readback, whether ordinary `02/6C` changed.
- Native service (if approved): module name + **hash**, architecture, symbol/call graph, source of scheduler persistence, safe **read-only** logs. Never share full extracted firmware or private device credentials.
- Functional: real video **frame count / fps / duration / total capture time**, scheduled stop timestamp, persistence after reboot, repeat next day, radio reachability and wattmeter Wh.
- Acceptance: two short end-to-end daily repetitions, 8 h capture, then **at least seven consecutive days** unattended. No “works” claim before these.

**Stop immediately** if unlock/root has no validated recovery route, correct model/firmware is unknown, important native hashes mismatch, camera starts/stops another owner's/manual recording, readback clamps to 5 h, wake fails, SD approaches full, heat exceeds safe behavior, or OTA/boot state changes unexpectedly.

## 6. Implemented code elsewhere in this repository (do not duplicate)

| Current asset | Where | Status |
|---|---|---|
| Action 5 Pi 4 external BLE+Wi-Fi scheduler and 8 h **ordinary Timelapse** setter probe | [`feat/action5-multi-hardware`](https://github.com/jboehm1/remote-dji-action/tree/feat/action5-multi-hardware), [PR #4](https://github.com/jboehm1/remote-dji-action/pull/4) | Offline tests; **no physical Action 5 test** |
| ESP32-C6 external BLE scheduler | [`feat/esp32-daily-timelapse`](https://github.com/jboehm1/remote-dji-action/tree/feat/esp32-daily-timelapse), [PR #1](https://github.com/jboehm1/remote-dji-action/pull/1) | Code prototype, overnight BLE/wake still blocked |
| `02/6C` offline Mimo packet builder/decoder and camera-only capture procedure | [`research/mimo-action6-protocol`](https://github.com/jboehm1/remote-dji-action/tree/research/mimo-action6-protocol), [PR #3](https://github.com/jboehm1/remote-dji-action/pull/3) | Action **6** wire research; Timer Shooting setter **not** identified |

This document **changes no firmware, sends no protocol commands, introduces no code into camera root and makes no claim of field success**. It provides a reproducible research decision tree for the next action.
