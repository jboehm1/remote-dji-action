# DJI Action 6 — Daily Timelapse Controller

Goal: **start and stop a DJI Osmo Action 6 timelapse every day**, for a user-defined local-time window (for example 08:00–18:00), without the camera's built-in 5-hour duration choice limiting the schedule.

**Status:** experimental research and firmware development; no camera-hardware validation yet.

Development work lives on feature branches. See the current [pull requests](https://github.com/jboehm1/remote-dji-action/pulls).

## Design direction
- First: ESP32 BLE external scheduler using the DJI R SDK, camera configured to **Timelapse → unlimited duration**.
- Second: investigate a custom timelapse duration via DJI Mimo control protocol (not proven accepted beyond advertised values).
- Last: camera firmware modification only with full recovery path, because it brings avoidable brick/update risk.
- Avoid duplicating or uploading DJI firmware binaries or proprietary assets.

Reference projects: [rhoenschrat/DJI-Remote](https://github.com/rhoenschrat/DJI-Remote) and [DJI's official GPS remote demo](https://github.com/dji-sdk/Osmo-GPS-Controller-Demo). Please respect upstream licenses and DJI's SDK terms.
