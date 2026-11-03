# Alliot Action 5 Pro unlock release ZIP — static inspection checkpoint

**2026-11-03 status: archive content NOT acquired; do not represent this as an inspected unlock procedure.**

This is **Native Track N** only. The unrelated ESP32/BLE work stays in [Track B](ACTION5_TWO_SEPARATE_TRACKS.md). The camera-only goal is a DJI Timer Shooting duration of **10 h / 36,000 s** with internal wake and daily repeat.

## Identified original archive

| Attribute | Observed public release metadata |
|---|---|
| Publisher | [`AlliotTech/action-control`](https://github.com/AlliotTech/action-control) |
| Release | [`action5pro-unlock-files.zip`](https://github.com/AlliotTech/action-control/releases/tag/action5pro-unlock-files.zip) |
| Direct asset | [`action5pro-unlock-files.zip`](https://github.com/AlliotTech/action-control/releases/download/action5pro-unlock-files.zip/action5pro-unlock-files.zip) |
| Size | 928,018 bytes (GitHub release metadata; **not checked against local bytes**) |
| Asset SHA-256 | `995315621279cbff1a37690ddc98b0ea6732125403b001f4c9e59828b7fe81cd` (release metadata; **not recomputed locally**) |
| Publication | 2026-09-19 |
| Associated author article | [`osmo-action5pro-unlock-bootloader-adbd`](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) — link verified from author's [issue #1](https://github.com/AlliotTech/action-control/issues/1) and [V2EX announcement](https://v2ex.com/t/1243167); article text inaccessible during this session |

## Attempt and blocker

- The GitHub **release webpage** loaded and showed the 906 KB asset link.
- Two browser download mechanisms were attempted: download-event click and direct asset `downloadMedia`. Both timed out; no bytes were delivered to the inspection workspace.
- GitHub repository-content fetch does not fetch **release** binary assets and returned 404 for that download URL. Direct terminal egress to GitHub was unavailable.
- Thus **no filename list, extracted script, executable loader, partition map, readme, exploit chain, rooting command or recovery instructions can yet be claimed**. Do not infer ZIP contents from the release title, online articles or generic Qualcomm EDL advice.

## What to do when the authentic ZIP is available

Provide the original `.zip` as a chat attachment or place it locally; do not run any content and do not connect the camera for this stage. For example:

```sh
python3 tools/inspect_alliot_unlock_zip.py ./action5pro-unlock-files.zip
python3 tools/inspect_alliot_unlock_zip.py ./action5pro-unlock-files.zip --preview-text
```

The script reads archive bytes without extraction, execution, flashing, root escalation or network access. It compares the whole-archive SHA-256 to the pinned release hash and enumerates **every entry** with its compressed/uncompressed size, CRC, SHA-256, leading magic bytes, encryption state, symlink flag and path-traversal warnings. `--preview-text` adds the first 4096 bytes of likely textual files to the report. If the hash is different, stop and establish provenance before analyzing it as *Alliot's* release. It limits entry reading to 16 MiB and cumulative uncompressed reading to 64 MiB; skipped entries remain visible in the manifest.

For high-risk binary files, prefer local read-only `file`, `strings`, `readelf`, `objdump`, Ghidra and checksums after a **safe isolated extraction** only if the archive has passed the path/symlink/size inventory. Treat any claimed executable, loader, signed programmer, `boot.img`, `firehose`, `abl`, `vbmeta`, `super`, `adbd`, `edl`, `fastboot`, `patch`, `factory`, or `misc` payload as *untrusted until fully analyzed*. A potentially matching SoC does **not** prove camera revision, firmware, signing or recovery compatibility.

## Detailed remaining questions to answer file-by-file

1. Exact contents: filenames, sizes, cryptographic hashes, formats and license provenance. Any third-party loader or proprietary vendor blob?
2. Are instructions/scripts present? For each step, record **host or camera execution**, preconditions, USB VID/PID and command **effect on persistent storage**. No speculative execution.
3. Which Action 5 Pro **firmware build**, hardware board and boot-chain version are targeted? What guards prevent use on Action 4/6 or another AC204 revision?
4. Is Qualcomm EDL/9008 merely used to **start temporary `adbd`**, or to write any partition and change verified boot / bootloader state? Which parts persist over reboot?
5. Which OEM signature, loader programmer, patched image and flash layout does it assume? Are the binaries redistributable and authenticity-verifiable?
6. Can all critical partitions be **backed up before** first destructive operation? How is stock firmware restored if the camera will not boot?
7. Can root ADB be enabled **without** firmware flashing? Is Factory Mode involved and reversible? Does unlocking erase user settings/media?
8. What exact **root command output** and `ro.product.name`, `/usr/lib/*` hashes were captured on real Action 5 hardware? Can we cross-check the [Alliot ABI audit](ALLIOT_ACTION5_ROOT_ABI_AUDIT_2026-11-03.md)?
9. Where are the **Timer Shooting** task and GUI validation implemented? The ZIP may only unlock access and contain **no timer-related code at all**.
10. Is an independently proven recovery path available? If not, **stop before any boot/EDL/flash experiments**.

## Separate blocker for the 10-hour feature

Even if the ZIP provides a reproducible ADB-root path, that **does not** identify the native Timer Shooting setter. The high-leverage next artifact remains a device-matched **read-only** copy of the GUI/service ELF or a 3 h vs 5 h Timer Shooting settings trace. Only after that can we decide whether a 10 h value is a UI menu addition or needs native backend modification. See [firmware target and validation gates](ACTION5_TIMER10H_FIRMWARE_TARGET.md).
