# AlliotTech/action-control: Action 5 Pro root, ADB, native API and GUI forensic audit

**Investigation date:** 2026-11-03.  
**Upstream pinned tree:** [`AlliotTech/action-control@b888a66`](https://github.com/AlliotTech/action-control/tree/b888a66adebdf6c65649efc074ff6867782756b4), commit dated 2026-09-27.  
**Scope:** documentary + source-code inspection only; no connected DJI camera, proprietary firmware image, EDL/bootloader operation, ADB root test, flashing, or Action Control installation.  
**Goal:** establish the exact foundation for a future **10 h native Timer Shooting** option while retaining the DJI camera's own scheduled wake. Bluetooth external control is a completely separate [fallback track](ACTION5_TWO_SEPARATE_TRACKS.md).

## Executive verdict

1. **This is an actual on-camera Linux application.** Alliot's program runs with root privileges *alongside* DJI's proprietary firmware. It is **neither the original DJI source code nor a full replacement ROM**.
2. The author reports **real Action 5 Pro hardware** tests of native Binder camera status, recording start/stop, still capture, Photo/Video mode selection, and a rear-screen GUI plugin. These are valuable reusable foundations.
3. **No known Timer Shooting getter/setter, 10 h validator patch, 10 h video, or safe reinstall/recovery of our own camera has been demonstrated.** `camera_set_mode_profile` currently exposes only proven Photo=5 and Video=1. Timelapse is not mapped.
4. The **GUI hook** already changes a real on-camera menu without replacing DJI's original GUI executable, via a fingerprint-gated proxy library. This is a promising *delivery mechanism* for a 10 h option **after** the true scheduled-task backend is understood. The existing plugin is not itself a Timer Shooting patch.
5. DJI confirms the stock [Timer Shooting feature can wake the camera automatically](https://www.dji.com/osmo-action-5-pro). Preserving this internal alarm is preferable to replacing scheduling with a Linux daemon that cannot run after deep suspend/power-off.

## 1. Authoritative source and link inventory

| Resource | Exact source / current knowledge | Confidence |
|---|---|---|
| Project | [AlliotTech/action-control](https://github.com/AlliotTech/action-control) (original source MIT, verified at commit above) | SOURCE |
| Main setup/constraints | [README](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/README.md) | SOURCE |
| Native ABI disassembly notes | [NATIVE_CAMERA_REUSE](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/NATIVE_CAMERA_REUSE.md) | DEVICE + SOURCE |
| Rear GUI research, freeze and recovery | [native/gui/README](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/native/gui/README.md) | DEVICE + SOURCE |
| Firmware unlock article | [author's linked blog](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd), linked in [issue #1](https://github.com/AlliotTech/action-control/issues/1) and the [V2EX announcement](https://v2ex.com/t/1243167) | Link verified; **article inaccessible to this audit** |
| Unlock asset | [action5pro-unlock-files.zip release](https://github.com/AlliotTech/action-control/releases/tag/action5pro-unlock-files.zip), [authenticated file-by-file static review](ALLIOT_UNLOCK_ZIP_STATIC_REVIEW.md) | **Original ZIP + two binary contents inspected offline**; unlock procedure and compatibility not established |
| Native root backend | [Python ABI adapter](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/native_camera_reader.py), [Go host](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/native_camera_reader.go), [recording API](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/native_camera_recording.go) | SOURCE |
| GUI injection mechanism | [plugin.c](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/native/gui/plugin.c), [ui.c](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/native/gui/ui.c), [gui_plugin.go](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/gui_plugin.go) | SOURCE |
| Installation/rollback | [install.sh](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/install.sh), [install.ps1](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/install.ps1), [install.go](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/install.go), [install_state.go](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/install_state.go), [install_update.go](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/install_update.go) | SOURCE |
| GUI rollback trial tooling | [test-gui-plugin.py](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/tools/test-gui-plugin.py), [gui_trial_guard.py](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/tools/gui_trial_guard.py), [gui_display.py](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/tools/gui_display.py) | SOURCE / author's DEVICE testing |
| Official baseline | [DJI Action 5 Pro release notes/downloads](https://www.dji.com/downloads/products/osmo-action-5-pro) and [Timer Shooting product description](https://www.dji.com/osmo-action-5-pro) | Official documentation |

The GitHub tree at the pinned revision contains **136 files**. The relevant C/Go/Python, root installation, native ABI, GUI, media/preview and support sources have been inventoried here. Web frontend UI controls and media-management modules are downstream of the root backend and are **not** a source of Timer Shooting's private C++ setter.

## 2. Root/bootloader/ADB: the exact known chain

| Stage | What is actually supported by the evidence | What remains missing |
|---|---|---|
| Physical chip / OS | On the verified camera, `/build.prop` contains `ro.product.name=qcs8550_ac204`; `uname -m=aarch64`. Author runs Linux/systemd, Python 3, proprietary DJI ELF/Binder clients. His announcement mentions Snapdragon 8 Gen 2 and Qualcomm **9008/EDL** access. | The owner camera's physical board revision, current firmware and secure-boot state; *do not assume another Qualcomm QCS8550 board is flash-compatible*. |
| EDL/9008 | Author and [announcement](https://v2ex.com/t/1243167) report use of 9008 to enable `adbd`; the author's blog claims bootloader unlocking. | The step-by-step method, compatible programmer, partition layout, raw flash operations, signature requirements and rollback for **this** device have not been read/validated here. |
| Published unlock materials | Owner-supplied original `action5pro-unlock-files.zip`, **928,018 bytes**, matching GitHub asset SHA-256 `995315621279cbff1a37690ddc98b0ea6732125403b001f4c9e59828b7fe81cd`; [full static review](ALLIOT_UNLOCK_ZIP_STATIC_REVIEW.md). | **Inspected:** `loader/RedMagicCommon_8Gen2_devprg` (Qualcomm/RedMagic-style EDL loader, 1,768,340 B), `img-unlock/abl-factory.img` (factory ABL candidate, 1,048,576 B, SecTools test-key-labelled cert). **Not present:** unlock scripts, readme, backup/restore files or DJI Timer patch. Real compatible unlocking and safe recovery remain unverified. |
| Root ADB | Upstream installer **requires** a camera already accessible through ADB with `adb shell id -u` returning `0`; it does **not** perform bootloader unlocking, ADB enablement or removal of Factory Mode. | Whether the owner's untouched Action 5 Pro has any ADB/EDL interface or recovery access. |
| Installation | After root, source includes a transactional Action Control installer with checks and backups. | This does not establish a safe root/unlock path; uninstall explicitly does **not** re-lock BL, disable root ADB or remove Factory Mode. |

**Do not transplant generic Android/phone instructions.** `fastboot flashing unlock`, a generic Qualcomm Firehose or a random QCS8550 image are **not verified** for DJI AC204. Merely seeing USB `05c6:9008` does not imply writable partitions or an available signed recovery image. No EDL flashing, test-point bridging, Factory Mode change or bootloader modification is authorized by this research document.

### Exact non-mutating identification checks

With the camera deliberately connected by USB and its identity selected, the following are **observations only**, not an unlock procedure:

```sh
adb devices -l
adb -s YOUR_VERIFIED_SERIAL get-state
adb -s YOUR_VERIFIED_SERIAL shell id -u
adb -s YOUR_VERIFIED_SERIAL shell uname -m
adb -s YOUR_VERIFIED_SERIAL shell cat /build.prop
```

The last command may expose more than the needed product property; do not paste a complete device fingerprint, serial or credentials into public issues. The [checked local preflight](../tools/action5_adb_preflight.py) extracts and reports only the product name, architecture and public library hashes. It **requires an exact `--serial`**, never guesses the nearest camera, stops before private-library probing when root ADB is absent, and issues no mutating command.

```sh
# No camera changes; useful only AFTER ADB is already available:
python3 tools/action5_adb_preflight.py --serial YOUR_VERIFIED_SERIAL
```

Exit 0 means *reference fingerprints match*, **not** that firmware patching is safe. Exit 2 blocks on model/root/ABI mismatch. The script has five simulated host regression tests. It does not bypass a stock locked camera's access controls.

## 3. Verified firmware identity and native ABI

The [upstream Python adapter](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/cmd/action-control/native_camera_reader.py) calls `check_environment()` **before** loading any proprietary `.so`:

- Linux, AArch64, **EUID 0**, 16-byte creation struct, 4-byte C integer.
- Exact `/build.prop` product marker `qcs8550_ac204`.
- **Both** client and server SHA-256 match known values.
- `ctypes.CDLL(..., RTLD_NOW | RTLD_LOCAL)` with isolated Python `-I -B`, not an injected library in the main Go server.
- Native camera manager creates an independent client name, connects to the **single camera ID 0**, and explicitly destroys its Binder manager afterward.
- An abstract UNIX socket serializes independent native reader processes. Go additionally uses timeout and concurrency locks; no speculative auto-retry of uncertain START/STOP results.

| Verified path | SHA-256 (upstream specific firmware) |
|---|---|
| `/usr/lib/libdcam_camera_service_client.so` | `98731a8252ee1d1e557af05e3369d33192b9c25142e97513c774f47c16bf27fa` |
| `/usr/lib/libdcam_camera_service_server.so` | `da7713234f19353054fd9faede2fa9feb211a99564ba4352d796d538cf9c859f` |
| `/usr/bin/dji_gui_on_disp0` | `30eb933b1c2315984e150885124d277c13c1cef3194ba6c08cb3d4d1f6656db1` |
| `/usr/bin/dji_gui_on_disp1` | `e965fbc8588445f5fa922fd1df38ed7051198fe28a50c33e51c94246c00fdb27` |
| `/usr/lib/libgui_image_loader.so` | `4774cc379c3cdbcc11242b7bde1b7490f3061c11c09ed79f05e2f0afd7c53c82` |

The first two hashes are from `native_camera_reader.py`; the latter three come from the upstream GUI trial's explicit `EXPECTED_SHA256` map in `tools/test-gui-plugin.py`. An upgraded official DJI firmware can invalidate **every** associated C++ offset, vtable or struct layout. **Never** bypass the hash gates to force compatibility.

### Native methods: proven, proposed and unsafe to guess

| Upstream symbol/API | Author's reported result | Relevance to Timer Shooting |
|---|---|---|
| `camera_manager_create` / `camera_manager_destroy` | Binder camera client lifecycle established | Useful safe local service access once root and ABI matched |
| `camera_manager_get_camera_amount` / `camera_manager_connect_camera` | Exactly one camera, camera 0 | Protects against wrong device/proxy |
| `camera_get_record_state`, `camera_get_capture_state` | `1=recording`, `3=idle`, capture `0=idle` in tested paths | Session observations; not Timer task data |
| `camera_start_recording`, `camera_stop_recording` | Real `3→1→3` sequence and saved MP4 without Mimo | Local trigger only; **Timelapse mode and schedule still unverified** |
| `camera_start_capture` | Photo saved while in Photo profile | Not scheduled Timelapse |
| `camera_get_mode_profile`, `camera_set_mode_profile` | Video `1`, Photo `5` tested, reversible | **No Timelapse profile ID has been safely identified**; do not brute-force integers |
| `camera_manager_get_workmode` | Returned `3` in both Video and Photo | Cannot distinguish Timelapse or Photo from this number |
| `camera_get_video_format`, codec/storage/EIS getters | Read-only video settings on exact ABI | Returning structs require **64-byte buffer**, not a 4-byte int; the author reports a segfault from the smaller buffer |
| A Timer Shooting setter / task readback | **Not found or tested** in published code | **Primary research blocker** |

Upstream documented the actual camera manager and recording call offsets in [NATIVE_CAMERA_REUSE](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/NATIVE_CAMERA_REUSE.md). They are **offsets in one exact ELF build**, not stable vendor API addresses. Treat them as Ghidra cross-reference leads only. The native video library holds storage, mode, thermal and asynchronous completion policy; invoking a private function is not proof that a real media file was saved.

## 4. Rear-screen GUI extension: the truly reusable on-camera mechanism

The [upstream menu implementation](https://github.com/AlliotTech/action-control/tree/b888a66adebdf6c65649efc074ff6867782756b4/native/gui) provides a concrete way to attach *one extra menu item* in DJI's running rear-screen interface:

1. A C shared library wraps `gui_image_loader_create` and delegates to the **original** `/usr/lib/libgui_image_loader.so` through `dlopen`/`dlsym`, rather than rebuilding DJI's GUI from source.
2. It validates the executable backing the current process: `/proc/self/exe` SHA must exactly match the verified **rear GUI** `30eb933b...`. On mismatch, the plugin does not attach its custom callback and leaves the stock image loader path intact.
3. GUI modifications run on the application's **`ew_gui_thread`** through `EwGuiRegisterUserEvent`, respecting the native Embedded Wizard (EW) object/thread model. Blocking HTTP/storage work is deferred to a separate worker.
4. It locates `TestTestApp.Application` / `OsmoGuiOsmoApp`, differentiates 712×712 canvas from 712×400 active rear-screen geometry, handles touch transformations and appends `Action Control` to the real System Settings list.
5. The added panel currently displays a hotspot switch, Wi-Fi QR, console URL QR and Back button. **It has no Timer Shooting duration controller.**
6. `native/gui/ui.c` contains recovered *private* EW object fields, interface/vtable slots and offsets for one specific GUI hash. These are not portable C headers or documented DJI plugin APIs. Reuse demands **new per-firmware inspection**.

### Persistent activation (what the installer actually modifies)

`cmd/action-control/gui_plugin.go` reads `/etc/disp0_plugins_config.json`. Under `plugins_configs` it finds `creator_func_name == "gui_image_loader_create"` and changes that entry's `plugin` to:

`/blackbox/upgrade/action-control/bin/libaction_control_gui.so`

It preserves existing parameter entries and appends `ac_mode=menu;` and `ac_state=/run/action-control-ui-persist;`, writes the config with original ownership/mode, and restarts `gui.service` **only if needed**. Before first write, it stores the original config in `.restore/gui-plugin.json`, for `restoreGuiPlugin()` to restore verbatim during uninstall. The plugin creates its private state directory as root with mode `0700`.

**Cold-boot detail:** the author found that this camera's `/etc` overlay is mounted *after* systemd reads the GUI service unit. Therefore `Environment=`/`ExecStartPre=` in a GUI systemd override cannot reliably pass the persistent extension settings. The verified approach embeds `ac_mode`/`ac_state` in the runtime image-plugin config parameter string.

### What to borrow for our 10 h implementation

- Borrow **the reversible, hash-gated extension pattern**, UI-thread discipline, explicit display verification and independent recovery watchdog.
- **Do not borrow the current hotspot panel as a 10 h UI implementation.** It proves attachment only, not task duration acceptance.
- Once the **actual Timer Shooting backend setter** is known and passes a real 10 h test, consider (a) adding a 10 h option through the original menu's model, or (b) an independent, clearly labelled Action Control configuration panel. Either is cosmetic until the underlying native task persists and executes.
- Never hardcode a menu entry or falsely show 10 h while the scheduled task still stops at 5 h.

### Real incident and risk controls reported by Alliot

The author reports an earlier **frozen physical display**, even when native processes, touch events and EW callbacks continued. The root cause was not determined. A later controlled version succeeded with several enter/click/back cycles and explicit captured GUI pixel verification. That success does not qualify all Action 5 firmware versions, front-screen behavior or long-duration capture coexistence.

Upstream `tools/test-gui-plugin.py` uses bounded temporary `/run/action-control-ui-*` state, a `BindReadOnlyPaths`-based trial override and an **independent systemd rollback timer** before restarting the rear GUI. `tools/gui_trial_guard.py` restores the prior configuration, checks for active media writes and only performs a controlled whole-camera reboot if display recovery failed **and** no camera media write is active. Do not assume a live process or click count proves the screen is actually displaying frames.

## 5. Installation: what is reversible and what is not

This is a **code audit, not installation instructions for an unrooted camera**. For a previously rooted qualified camera:

- `install.sh` / `install.ps1` require an **extracted complete release** containing `payload/action-control`, `payload/manifest.json`, and `SHA256SUMS`; both verify packaged file SHA-256 values before transfer.
- Both select one explicit/unique ADB device, require `get-state=device`, `id -u=0`, `uname -m=aarch64`, and read the boot ID. No automatic unlocking is attempted.
- Staging is created by restrictive `mktemp` under `/blackbox/.action-control-stage-*`. The scripts transfer the bootstrap and payload, invoke the camera-side installer, verify the installed version, and use a local ADB forward for the console.
- The actual app root is `/blackbox/upgrade/action-control`. The upstream README warns **not** to place it in the `/blackbox` root because device boot scripts may format this partition on failed checks.
- Go's installer records file hashes, ownership, modes and shared-file backups, refuses untracked paths, and supports an update rollback state under `.restore/` and `.update/`. It manages `action-control.service` and `action-control-network.service` via systemd.
- Startup persistence is mediated by `/etc/init.post_boot.sh` because of the `/etc` overlay/unit-load ordering. Some network files, Wi-Fi/DNS configuration and GUI display config can be touched by the **installer** even though our offline scout does not do so.
- Installing/updating the GUI extension can restart `gui.service`. The backend service uses `Restart=on-failure`; its default service listener is `:8080`.
- `uninstall.sh --reboot` and `uninstall.ps1 -Reboot` restore recorded owned files, the original GUI configuration and Wi-Fi/DNS baselines. Upstream requires a reboot to restore native runtime state. **Uninstall does NOT re-lock the bootloader, remove Factory Mode or disable root ADB.**
- An incomplete install or update may intentionally **retain staging/backups** for recovery; force deletion would remove evidence. The existence of application rollback is not proof of an unbrick path after incorrect boot/EDL/partition operations.

At the pinned tree, the Go source declares `Version = "0.1.17"`; published hardware test notes describe successful stages through **0.1.16**. Do not silently equate source HEAD with the exact camera-tested 0.1.16 binary. The build expects Go **1.27.1**, Node **24.20.0**, and a Zig **0.16.0** ARM64/glibc build for the native GUI module. The source is MIT, but that license **does not cover** proprietary DJI ELF blobs or device firmware.

## 6. Security audit: root Web console is not safe on a public network

The upstream README explicitly says the root HTTP control API has **no authentication and no TLS**. The service binds to port `8080`, can control native recording and networking, and its system endpoints include powerful process commands and reboot modes. The default camera hotspot has been reported as `192.168.2.1` but should never be considered an authenticated trust boundary.

**For investigation:** keep the Web console inaccessible to the internet and untrusted Wi-Fi; upstream recommends local USB ADB forwarding (`adb forward tcp:8080 tcp:8080`). A native-camera 10h product would require a dedicated low-privilege settings interface, authenticated controls or complete removal of the unauthenticated process-management surface before outdoor deployment. Firmware modification and network hardening are independent acceptance gates.

## 7. Native networking and media paths (relevance limited)

- [NATIVE_HOTSPOT_API](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/NATIVE_HOTSPOT_API.md) uses the existing `dji_network` native service with firmware fingerprint checks; the camera's AP may drop after roughly 60 s without active DJI app/BLE use, so the console resets the vendor inactivity timer every 25 s. This is **not a Timer Shooting wake proof**.
- [MIMO_PREVIEW_PROTOCOL](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/MIMO_PREVIEW_PROTOCOL.md) confirms that the author can passively capture and decode native Mimo UDP/SW/DUML traffic on the camera. The `mimo_pcap.py` parser is valuable for future *read-only* Timer task A/B captures, but the existing dataset captures preview/recording behavior, **not the unknown scheduled-duration SET**.
- [NATIVE_PREVIEW_LIFECYCLE](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/NATIVE_PREVIEW_LIFECYCLE.md) warns that `camera_start_stream` is an existing GUI front/rear stream path, not an arbitrary independent subscriber. Do not repurpose its string/terminal arguments as guessed scheduler parameters.
- [MIMO_WEB_PREVIEW](https://github.com/AlliotTech/action-control/blob/b888a66adebdf6c65649efc074ff6867782756b4/docs/MIMO_WEB_PREVIEW.md) mirrors an existing Mimo video stream; it is not an internal schedule API and does not function independently of Mimo for live preview.

## 8. The safe handoff: exact missing evidence to access and patch Timer Shooting

| Gate | Required evidence | State on 2026-11-03 |
|---|---|---|
| G0 source/links | Pin repo commit, release metadata, author references, original ZIP SHA and static file manifest | **Done for ZIP and source**; author's separate blog article remains inaccessible |
| G1 owner hardware identification | Action 5 firmware/build, AC204 board/product, ADB exposure, operator's camera serial kept private | **Missing** |
| G2 bootloader/root plan | Verified blog procedure, model-compatible programmer, partition backup map, signed recovery image, return-to-stock on identical unit | **Incomplete — original ZIP inspected but contains only two boot-related ELF binaries and no instructions/recovery. Do not unlock yet.** |
| G3 root-ADB read-only preflight | Correct `id -u`, architecture, product, known exact SHA values | Script ready; **no real camera tested** |
| G4 scheduled-task discovery | Native GUI and server ELF strings/xrefs, before/after 3h vs 5h task setter, persistence and alarm owner | **Missing** |
| G5 10h accepted task | Correct setter readback = 36,000 s; ordinary `02/6C` unchanged; UI coherent after reboot | **Missing** |
| G6 media + wake | Actual >5h Timelapse, automatic end, next-day repeat without phone/ESP32, safe night power | **Missing** |
| G7 deployment | Rollback rehearsal, secure control surface, storage/thermal safeguards, 7-day unattended validation | **Missing** |

### Research-only workflow after separately approved lawful access

1. Record model, exact firmware, OEM rollback assets, secure-boot/partition compatibility and a separate recovery review **before privileged changes**.
2. On an **already legitimately rooted** matched camera, run only the preflight script initially. Confirm service and GUI hashes against the source above.
3. Analyze **owner-held, offline, read-only copies** of the relevant ELF and GUI resources with [`scan_osmo_native.py`](../tools/scan_osmo_native.py), then use Ghidra/radare2 call graphs to identify **scheduled Timer Shooting** task UI, validation, persisted task and RTC wake path. Proprietary binaries, firmware dumps, raw HCI/PCAP, passwords, MACs and signed loaders stay outside Git.
4. Start with a known-good 3 h native schedule. Compare **only one variable** at a time (3→5 h, start time +1 h, Repeat off/on). Differentiate the native Timer task from ordinary Timelapse `02/6C` and the ambiguous `gui_autorecord_param` (could mean diving Auto Record).
5. If the actual service accepts 36,000 s, build a narrowly scoped reversible UI option while preserving DJI's native scheduler and wake. If not, stop and design a separate, explicit firmware-patch safety review rather than forcing an unknown ABI.

**The next decisive artifact is a real Action 5 Pro native scheduled-task setter/readback trace (or matching ELF xrefs), not another generic BLE remote.**

