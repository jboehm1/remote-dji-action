# ESP32-C6 daily start/stop power budget (2026-10-29)

**All figures are MODELS, not measured hardware.** The active prototype in `main/app_main.c` **never enters deep sleep**; it leaves Wi-Fi/BLE initialized and loops once a second. Therefore use the **always-on** rows for the current code; the ~0.01 Wh/day low-power rows are targets requiring software and hardware work.

## Official silicon sources

1. Espressif ESP32-C6 [datasheet](https://documentation.espressif.com/esp32-c6_datasheet_en.html): chip-only 3.3V typical **7 µA deep sleep**, **180 µA light sleep** (with extra domains), BLE RX 71 mA while RF active, TX 94mA at -15dBm / 130mA at 0dBm / 190mA at 9dBm / 315mA at 20dBm, modem sleep with idle CPU ~14-28mA. **RF active figures are not 24-hour averages.**
2. Espressif [timekeeping](https://docs.espressif.com/projects/esp-idf/en/v5.5.6/esp32c6/api-reference/system/system_time.html): default internal RTC oscillator drifts in sleep with temperature; external 32.768 kHz crystal is more accurate at about 1uA deep-sleep penalty.
3. Espressif [sleep modes](https://docs.espressif.com/projects/esp-idf/en/release-v5.4/esp32c6/api-reference/system/sleep_modes.html): neither BLE nor Wi-Fi stays connected in deep sleep. Waking requires fresh BLE handshake; cannot assume camera remains discoverable.
4. [Analog Devices DS3231](https://www.analog.com/en/products/ds3231.html): ±2ppm 0..40C RTC and independent calendar alarms, optional for no-Wi-Fi timekeeping. 2ppm corresponds to ~0.173s/day, excluding board/module consumption and temperature.

## Reproducible equation

At 3.3 V output, for N active BLE session attempts each day, each `t` seconds:

```text
active_h = N * t / 3600
E_wh/day = (3.3 / 1000) * (I_active_mA * active_h +
                           I_sleep_mA  * (24 - active_h))
5V_input_mAh/day = E_wh/day * 1000 / (5.0 * 0.85)
1000mAh_3.7V_days = (1.0 Ah * 3.7 V * 0.85) / E_wh/day
```

0.85 is an **assumed** DC-converter efficiency, not a measured board value.

## Illustrative controller-only scenarios

| Configuration | Sleep draw | Active duty cycle | Controller energy Wh/day | 5V input mAh/day (85%) |
|---|---:|---|---:|---:|
| Bare C6 chip, optimistic | 7µA | 2 × 30 s at 100mA | **0.0061** | **1.4** |
| Optimized low-leakage board (one daily start + stop) | 30µA | 2 × 60 s at 100mA | **0.0134** | **3.1** |
| Optimized board (two daily sessions = 4 commands) | 30µA | 4 × 60 s at 100mA | **0.0244** | **5.7** |
| Conservative low-leakage board | 100µA | 2 × 120 s at 150mA | **0.0409** | **9.6** |
| Every 15 min reconnection / wake attempt | 30µA | 96 × 5 s at 120mA | **0.0552** | **13.0** |
| Ordinary dev board sleeping, optimistic regulator | 1mA | 2 × 60 s at 100mA | **0.0901** | **21.2** |
| Ordinary dev board sleeping, high leakage | 5mA | 2 × 60 s at 100mA | **0.4065** | **95.6** |
| Always on 20mA (illustrative avg) | N/A | 24h @ 20mA | **1.5840** | **372.7** |
| Always on 50mA (illustrative avg) | N/A | 24h @ 50mA | **3.9600** | **931.8** |

The 20-50mA continuous figures are **assumed average currents**, not certified measured ESP32-C6 firmware profiles. A continuously connected Wi-Fi + BLE prototype may be above them. Every RF TX pulse can be much higher than 100mA.

## Camera energy dominates and cannot be inferred from ESP32

DJI [Action 6 specs](https://www.dji.com/osmo-action-6/specs) list a **7.5 Wh** internal battery. The camera's *measured* power consumption in idle/BLE sleep, Timelapse moon mode, 10h capture and post-stop state is **unknown** in this project.

For illustration ONLY:
- A camera that stays at 0.5 W for 14h overnight consumes **7 Wh overnight**, dwarfing even low-power ESP32.
- Camera at 0.1 W for 14h consumes **1.4 Wh overnight**.
- Camera at 0.01 W for 14h consumes **0.14 Wh overnight**.

These are scenarios, **NOT Action 6 measurements**. A screen going black does not prove 0.01W deep sleep.

## Hidden overnight problem

DJI's [official GPS remote protocol reference](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo/blob/main/docs/protocol_data_segment.md) says wake-by-BLE-advertising requires camera to have slept for **no more than 30 minutes**, based on examples for Action 4/5. **Action 6 has not been checked**; never assume an ESP32 sleeping 14h can wake the camera. This is a functional blocker independent of the controller's tiny power budget.

DJI's [Timelapse low-power article](https://repair.dji.com/help/content?customId=01700006949&lang=en&paperDocType=ARTICLE&re=US&spaceId=17) says **Bluetooth/Wi-Fi are disabled during shooting** in moon mode. Even a continuously awake controller might not be able to STOP a Timelapse from BLE in that mode.

If we must wake/reconnect the camera every 20 minutes, the 0.055Wh/day estimate covers **only ESP32 radio use**; it does not include the camera's repeated boot/wake cost. It may also interrupt native low-power Timelapse. Camera-only native control remains preferable.

## Power architecture alternatives

- **USB-powered, always-on ESP32:** simplest to debug, approximate 1.6–4.0 Wh/day with the stated 20–50mA assumptions, BUT don't consider this a low-power finished design.
- **Low-leakage ESP32 + efficient regulator + RTC crystal:** 0.01–0.05 Wh/day *if two 1–2-minute wake sessions work reliably*, subject to camera BLE wake limitation.
- **BLE-connection maintained (modem-sleep):** depends on duty cycle/connection parameters; cannot substitute chip 7µA deep sleep.
- **Self-powered ESP32 on 1000mAh, 3.7V Li-ion:** illustrative idealized 235 days for optimized case, 77 days for conservative, 8 days with 5mA dev-board standby, and <1 day at 50mA continuous average. Capacity, load peaks, battery degradation, safety/protection, temperature and self-discharge can shorten these drastically.

## Required hardware measurements

Use inline USB power meter for input energy (with caution about resolution) and a high-dynamic-range power analyzer/shunt for µA deep-sleep currents. Measure camera and controller **separately**:
1. Controller: powered idle, connected idle, BLE pairing, start/stop burst, Wi-Fi NTP and true deep-sleep.
2. Camera: off after SnapShot, normal idle after STOP, remote sleep after 5/40/120/840 min, moon mode during Timelapse, post-timer stop.
3. Test real response at 08:00 after 14h night, battery at realistic temperatures, firmware version, SD output.

**Reproduce table:** `python3 tools/esp32_power_budget.py`

All estimates intentionally exclude camera capture/overnight draw, which is likely the dominant unknown.
