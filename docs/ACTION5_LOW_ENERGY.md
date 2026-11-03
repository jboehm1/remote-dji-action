# Action 5 Pro: Timelapse low-energy behavior and power commissioning

Status: **researched, NOT bench-measured** (2026-11-03). Target camera is
**Osmo Action 5 Pro**, native **Timelapse**, interval **1 or 2 seconds**.
Evidence below does not certify an unattended schedule or battery life.

## What DJI actually documents

1. In Timelapse, the **moon icon** enables *Low Power Consumption*.
   DJI states the camera minimizes power **between captures**; it turns off
   **Wi-Fi and Bluetooth connections** when the feature is enabled, and turns
   the screen off **10 seconds after recording begins**.
   Source: [DJI Timelapse Low Power Consumption](https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE).
   It does **not** specify the exact radio cutoff time after START. An initial
   Mimo START succeeding therefore does not demonstrate that an ESP32/Pi can
   send STOP hours later. Physical test: read camera status at 10 s, 60 s and
   10 min, and attempt an authenticated, non-destructive status query.
2. The moon's **Always On Display** versus **Screen Off** choices affect screen
   appearance and must not be interpreted as a separate permission to retain
   wireless control. DJI's statement about both radios being disabled applies
   to *Low Power Consumption* mode. AOD's dim essential-information display is
   [documented by DJI](https://www.dji.com/osmo-action-5-pro).
3. The separate system setting **Scrn Off When Rec** has selectable timers of
   3 s to 10 min, but DJI describes its applicability for **Video and
   Slow Motion**, NOT native Timelapse. Do not assume it can blank the screen
   while retaining BLE in Timelapse with the moon **off**.
   Source: [DJI recording screen timeout](https://repair.dji.com/help/content?customId=01700006930&lang=en&paperDocType=ARTICLE).
4. In **System Settings > Wireless Connection**, turning off wireless disables
   **both Wi-Fi and Bluetooth**. A camera-wide separate Wi-Fi-off/BLE-on
   switch has not been demonstrated. **BLE-only remote control nevertheless
   is possible**: the DJI GPS Controller protocol uses BLE without requesting
   Mimo's Wi-Fi video session. This is a *connection strategy*, not proof
   that the camera Wi-Fi circuitry consumes zero power.
   Sources: [DJI wireless switch](https://repair.dji.com/help/content?customId=01700006964&lang=en&paperDocType=ARTICLE),
   [official DJI BLE controller demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo).
5. DJI publishes **0.5 W** for **standby mode / low-power mode** on Action 5
   Pro, but NOT a controlled measurement of **4K Timelapse at 1 s or 2 s**.
   Its approximately **7.5 Wh** battery and **4 h** maximum video runtime
   correspond to a separate video workload (about **1.9 W** *average* in that
   test, NOT a Timelapse measurement).
   Sources: [DJI Action 5 specs](https://www.dji.com/support/product/osmo-action-5-pro),
   [DJI Action 5 video battery conditions](https://www.dji.com/osmo-action-5-pro/faq).
6. DJI's BLE protocol documents **broadcast wake** only when the controller
   was recently connected and the camera has slept **no more than 30 min**.
   This is *not* proof that every paired remote or still-connected controller
   stops working after 30 min; it **does prohibit a claim of guaranteed
   broadcast wake after 14–16 h**. A daily morning wake-up is a separate,
   unvalidated acceptance gate.
   Source: [DJI protocol data segment](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/protocol_data_segment.md).

### Why 1–2 s is particularly uncertain

Nothing in the manufacturer specifications establishes the processor/sensor
enters full **deep sleep** between shots. The approximate electrical model is:

`P_average = P_between_frames + E_per_capture / interval_seconds`

Reducing interval 2 s to 1 s doubles the per-capture contribution if the
camera's processing duty cycle does not overlap. This is a model, not
evidence for actual camera watts. Further, wireless radio, sensor warmup,
video encoding, screen and display policy may behave differently by mode.

## User's actual field observation, November 3 (important)

**Reported, not instrumented:** Osmo Action 5 Pro battery started at **14%**;
a **10,000 mAh** power bank started at **90%**. Both showed **0%** at the end,
after producing **14 minutes of finished Timelapse MP4**. Capture interval is
**uncertain**: user recalls **1 s**, but an earlier interpretation was **2 s**.
The MP4 frame rate and real stopwatch duration have not been verified. Camera
moon/AOD status was not recorded. This is a substantial owner-supplied
real-world test, but not a measured camera draw or DJI mode A/B test.

DJI [Action 5 Pro official specs](https://www.dji.com/osmo-action-5-pro/specs)
state native Timelapse MP4 is **25 or 30 fps**. With **14 min playback**:

| Interval | 25 fps real capture time | 30 fps real capture time |
|---|---:|---:|
| 1 s | 5 h 50 min | 7 h |
| 2 s | 11 h 40 min | 14 h |

The 14 h interpretation is consistent with **2 s at 30 fps**, not 1 s.
If 14 min was the *wall-clock recording time* instead of the final accelerated
video length, the table does **not** apply. Verify the actual clip metadata.

Energy approximation: original Action 5 battery 7.5 Wh x 14% = **1.05 Wh**;
bank nominal 10,000 mAh x approximately 3.7 V x 90% = **33.3 Wh**.
Assuming **80–90% bank conversion efficiency** and representative percentage
gauges, about **27.7–31.0 Wh** reaches the camera in total. This is imprecise
because USB power also charges the camera and battery percentages are not
laboratory energy readings.

| Interpretation | Estimated average draw (energy / actual capture time) |
|---|---:|
| 1 s, 25 fps | 4.8–5.3 W |
| 1 s, 30 fps | **4.0–4.4 W** |
| 2 s, 25 fps | 2.4–2.7 W |
| 2 s, 30 fps | **2.0–2.2 W** |

The result is **not** evidence moon OFF uses exactly 2–4 W, or that moon ON
fails: the user did not record which moon/screen options were active. It does
show why replacing this with the DJI **0.5 W standby** rating would produce
an unrealistic runtime forecast.

Reproduce the conditional numbers, then adapt them to the measured clip FPS
and actual interval, using `python3 tools/action5_calibrate.py --interval-s 1
--fps 30`. The script also predicts a possible runtime for a **20,000 mAh
100% bank plus 50% original camera battery**, conditional on identical draw.

Next field test: read MP4 `avg_frame_rate` and `duration` with `ffprobe`, note
the exact menu interval and moon choice, and record real start/end timestamps.
Keep *reconstructed Wh* separate from USB wattmeter/Wh data.

## Profiles and supported/unsupported promises

| Profile | Moon | Camera connections | External timed STOP | Preview | Power measurement |
|---|---|---|---|---|---|
| `NATIVE_ECO` | ON, Screen Off | DJI says BLE + Wi-Fi off during capture | **No guaranteed external STOP**; rely on camera-native finite timer | No normal Wi-Fi live | 0.5 W low-power spec **not** a 1–2s measurement |
| `BLE_ECO` | OFF | ESP32 BLE control, no camera Wi-Fi session requested | **Plausible**, must test actual Action 5 | Status+battery BLE only; no video | **Unknown**; moon off may keep screen awake |
| `PI_LIVE` | OFF | Pi BLE for pairing + Wi-Fi session to camera | **Plausible**, must test | Osmo Client MJPEG endpoint exists; during Timelapse **unverified** | **Unknown**, likely higher than BLE-only |
| `CAMERA_NATIVE_TIMER` | Usually ON, if permitted by native timer | No remote runtime required | Uses camera internal timer, with known **5 h** ceiling | No live during shot | Needs own wake/standby tests |

`NATIVE_ECO` and `CAMERA_NATIVE_TIMER` may be useful for camera-only sessions
up to five hours today. Finding a safe native way to schedule longer than 5 h
is a **separate** protocol/reverse-engineering question from sending a custom
`02/6C` ordinary Timelapse duration. Do not equate the two.

No currently implemented profile on *stock* Action 5 Pro offers **both**
documented moon-mode savings **and** guaranteed external STOP over BLE.

## Energy scenarios (NOT camera measurements)

Assume 8 recording hours + 16 non-recording hours per calendar day. The
numbers below are illustrative *constant average draw inputs*. DJI's **0.5 W
standby/low-power** reference does not guarantee 0.5 W in actual Timelapse.

| Hypothetical daytime draw | Energy for 8 h capture | 7 days capture (56 h) | Added if night stays at 0.5 W for 16 h x 7 |
|---:|---:|---:|---:|
| 0.5 W | 4 Wh | 28 Wh | +56 Wh |
| 1.0 W | 8 Wh | 56 Wh | +56 Wh |
| 1.5 W | 12 Wh | 84 Wh | +56 Wh |
| 2.0 W | 16 Wh | 112 Wh | +56 Wh |

**16 h x 0.5 W = 8 Wh at night**, more than one nominal 7.5 Wh
Action 5 battery. That 8 Wh is *conditional* on the camera actually remaining
at 0.5 W all night; a properly switched-off camera should use much less. A
20,000 mAh power bank rated at its cells' nominal ~3.7 V has ~74 Wh nominal;
at a hypothetical 85% conversion efficiency, ~63 Wh **usable**. This alone
cannot certify a week of 8h/day shooting with an always-awake camera.

Use `python3 tools/action5_energy_budget.py --day-w 1.5 --night-w 0.5` to
recalculate with **your measurements**, including power-bank efficiency. The
spread between 0.5 W and 1.5 W over 56 h is **56 Wh**: a potentially large
penalty if disabling the moon increases consumption by that much. The
actual penalty remains **unknown** until tested.

## Electrical and radio test protocol (ordered)

1. Fully update firmware; record its exact version. Install a logging USB-C
   **voltage/current/Wh** meter at camera input, a stable charger and a known
   data-capable cable. Log battery %, ambient temperature and final files.
   Beware: charging the internal battery distorts the instantaneous USB
   measurement. If testing with battery removed, independently validate the
   external supply: camera behavior may change or stop on marginal power banks.
2. Run **20–30 min each**, same 4K encoding/light/temperature, same interval:
   (a) Moon ON + Screen Off, (b) Moon ON + AOD, (c) Moon OFF with *no Mimo*
   and the ESP32 BLE controller, (d) Moon OFF with Pi Wi-Fi / live client.
   Record W average, Wh, display state, Bluetooth scans/status, Wi-Fi
   availability, camera internal battery %, camera temperature and saved MP4.
3. Repeat (a) and (c) at **1 s, 2 s and 10 s** interval. Each difference
   isolates to first order extra photo/encoding duty cycle (not deep sleep).
   See whether the screen actually shuts off in moon-OFF native Timelapse.
4. For every radio profile, after START wait **2 min** and **15 min**; read
   status and attempt **STOP**, documenting real state and playable output.
   Never assume that receiving the initial START ACK guarantees STOP access.
5. STOP at 18:00; leave a meter on for 16 h and attempt next START at 08:00.
   Also test explicit controller sleep/wake after **45 min, 2 h and 14 h**;
   expect no guaranteed broadcast wake beyond DJI's documented 30-min scope.
6. Test with external battery and mains separately; camera may automatically
   power down in idle. Observe whether timer/shooting remains armed and whether
   the Pi/ESP32 can reconnect after power loss. Unattended 7-day deployment
   only after at least 7 physical cycles of start, verified footage, stop,
   power and morning restart.

### Practical choice pending measurements

- **No external power:** prioritize **camera-native scheduled capture with moon
  ON**, accepting the documented 5 h native timer until its separate setter is
  resolved. More aggressive BLE automation trades away DJI's published
  low-power behavior; it cannot currently be marketed as battery optimized.
- **Reliable external USB-C power:** use **Pi / Osmo Client** for rich status,
  gallery and potential live view, or **ESP32 BLE** for low-complexity
  START/STOP. Both should select Timelapse `duration=0` (infinite), with moon
  OFF and physical verification.
- **Hybrid:** a Pi on mains can do Wi-Fi live only during user inspection, then
  disconnect its Wi-Fi client; this reduces Pi/network activity, but does not
  prove the Action 5 returned to DJI moon low-energy mode. Measurement needed.

The ideal future `AUTO` profile should record measured current power,
recording state, camera temperature, battery, free card capacity, night
wake reliability and (only when available) stream freshness. A public web
portal requires authentication/VPN and must never expose raw camera commands.
