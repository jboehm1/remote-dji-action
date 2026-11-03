# Action 5 Pro 10 h — minimum viable investigation BEFORE root/EDL

**Date:** 2026-11-03. **Decision:** The primary requirement remains **10 h of on-camera scheduled Timer Shooting, daily Repeat and native wake, with no runtime phone/BLE/ESP32/Pi**. A one-time connected phone/USB tool during setup is acceptable **only if the camera later operates autonomously**. The **first diagnostic route is rootless**; the proven Alliot EDL path is a separately gated fallback, not a mandatory first step.

## Prioritized decision tree

| Rank | Route | Camera change | Additional hardware | Evidence / stop criterion |
|---|---|---|---|---|
| **A1 — first** | Check stock Action 5 Timer Shooting menu, presets, Mimo exposure and any official scheduling controls | **None** | Phone already used with DJI Mimo | Only regard Timer Shooting as solved if the *native scheduled task* stores >5 h and still wakes next day |
| **A2 — next** | Passive 3 h ↔ 5 h **scheduled** Timer Shooting A/B captures/readback; isolate start time, Repeat and duration separately | **None** (read-only capture) | Phone/PC during lab session | Determine whether Mimo sends an actual native scheduled-task SET or the task is **local-GUI-only** |
| **A3 — conditional** | After identifying the *real task setter*, safely try 36,000 s once, then read back and power-cycle | Reversible setting write; not a firmware flash | No special cable | Go only if identified payload/field is truly **Timer Shooting**. Stop on rejection/clamp/uncertain state |
| **B — research only** | Check for documented stock USB diagnostic/ADB/fastboot access | No flash during identification | Ordinary USB cable | **No verified cable-free root path for a stock locked AC204** has been found; `adb reboot edl` presupposes working ADB |
| **C — only if A fails** | Alliot's verified AC204 10.00.16.13 EDL → `devinfo` → factory ABL → root ADB → GUI/native service research | **Boot-related partition writes** | EDL/9008 button cable (small purchase), bench computer | Requires explicit separate approval, identical firmware checks, per-device GPT/backups, repeated EDL access and a recoverable rollback plan |

## Important protocol boundaries

- `camcap_timelapse_duration`, `cam_lapse_param`, and Mimo/DUML `02/6C` are **ordinary Timelapse leads**, especially from Action 6 investigations. The 5 h / `18000` ordinary Timelapse duration and `0=∞` do **not** prove anything about **Action 5 Pro Timer Shooting / daily Repeat**.
- `gui_autorecord_param` is an **unmapped name**; it may concern diving Auto Record, not the scheduled Timer task. Do not treat it as the answer without a controlled A/B trace.
- If the daily task is configurable **only on the camera screen**, there may be no relevant Mimo SET packet to replay. This negative result should redirect research to native GUI/ELF analysis; repeated speculative `02/6C` injections would be uninformative.
- A protocol test is successful **only** when Timer Shooting displays/reads back 10 h, saves real footage past 5 h, stops after 10 h, survives reboot, and wakes autonomously the following day. An ACK, a different Timelapse setting, or a UI label alone is insufficient.

## Is a special USB cable unavoidable?

**No for research route A.** For **the exact bootloader unlock that Alliot demonstrated**, **yes**: his [first-hand procedure](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) uses a *second-generation Qualcomm 9008/EDL engineering cable with a button*, disconnecting power/battery for connection and then restoring the battery for stable UFS access. The EDL VID:PID is **`05c6:9008`** (`QUSB_BULK`). The cable is **not DJI proprietary**.

Qualcomm's [board EDL guidance](https://github.com/qualcomm-linux/qcom-linux-skills/blob/main/skills/qcom-flash-qdl/references/entering-edl.md) makes clear that entry differs by board and may use a boot-time hardware switch or, **when already authorized**, a software reboot; the existence of a command on Android/Linux elsewhere does not make it accessible on an unrooted Action 5. Classic [EDL cable research](https://alephsecurity.com/2018/01/22/qualcomm-edl-1/) describes button cables that briefly influence USB D+ relative to ground; **do not DIY short or modify the camera or USB leads based solely on that generic description**.

### Indicative price in Germany (search observation, 2026-11-03)

- Multiple consumer listings labelled `Qualcomm EDL 9008 Deep Flash`, USB-C adapter/2-in-1 and push-button were found at **~€8–15** on German-accessible shops; examples of Amazon.de third-party offers were **€9.25** and **€12.49** (stock, shipping and compatibility not verified). These are **not certified Action 5 Pro cables**, and an item with the keyword “EDL” alone does not guarantee the author's method works.
- Cable **cost is not the main issue**. The risk is **direct UFS partition modification and recovery uncertainty**. Do not buy additional hardware until the rootless protocol investigation is exhausted and our camera firmware has been identified.

## Why a backup is not zero risk

Alliot's [author blog](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) backs up **his device's own** `devinfo`, both `abl` slots, critical small partitions and `userdata` separately, hashes them, and requires an external second copy. It skips several large partitions from his bulk read, so this is **not a certified full-disk recovery image**. Restoration depends on **the camera still entering EDL, the loader still authenticating, consistent GPT and intact original data**. A power loss, wrong active slot, wrong sector, incompatible boot image or loss of EDL may make recovery impossible with the available tools. Reversible **in principle** does not mean risk-free **in practice**.

## Exact next experiment — no root/no cable

1. Record exact **model, firmware and Timer Shooting menu screenshot** on our physical camera; distinguish Timer Shooting max 5 h from ordinary Timelapse `∞` and current 1-second interval.
2. Configure a **3 h Timer Shooting with daily Repeat**, record the displayed state, then change **only duration** to **5 h** and compare. Repeat separately for start time and Repeat flag. If Mimo supports editing those tasks, capture a redacted controlled session and find the actual setter/readback; if it does not, explicitly document “local screen only”.
3. Do **not** transmit guessed 10 h bytes through ordinary `02/6C`. Only when a genuine scheduled-task setter is identified and reversible, test `36000` seconds and independent readback on the owner's explicit test unit.
4. Confirm persistence over reboot, real >5 h footage, autonomous next-day start and scheduled end **without any external controller**. If backend rejects the task or the schedule never leaves the local GUI, proceed to [Alliot native/root research](ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md) with its separate recovery gate.

**Separate-track rule:** this rootless path is a way to configure the **camera's internal schedule once**. It is *not* the external ESP32/BLE daily START/STOP fallback documented in [two tracks](ACTION5_TWO_SEPARATE_TRACKS.md).
