# Alliot Action 5 Pro unlock ZIP — verified file-by-file static inspection

**2026-11-03 status: ORIGINAL ZIP ACQUIRED FROM OWNER; ZIP AND BOTH BINARIES AUTHENTICATED AND INSPECTED STATICALLY.** This is **not** a verified, complete or safe unlock procedure. No binary was executed; no EDL/USB/root/flash operation was performed. The ZIP itself is not redistributed in this repository.

This is **Native Track N** only. The unrelated ESP32/BLE work stays in [Track B](ACTION5_TWO_SEPARATE_TRACKS.md). The camera-only goal is a DJI Timer Shooting duration of **10 h / 36,000 s** with internal wake and daily repeat.

## Identified original archive

| Attribute | Observed public release metadata |
|---|---|
| Publisher | [`AlliotTech/action-control`](https://github.com/AlliotTech/action-control) |
| Release | [`action5pro-unlock-files.zip`](https://github.com/AlliotTech/action-control/releases/tag/action5pro-unlock-files.zip) |
| Direct asset | [`action5pro-unlock-files.zip`](https://github.com/AlliotTech/action-control/releases/download/action5pro-unlock-files.zip/action5pro-unlock-files.zip) |
| Size | **928,018 bytes**, recomputed from uploaded file; matches release metadata |
| Asset SHA-256 | `995315621279cbff1a37690ddc98b0ea6732125403b001f4c9e59828b7fe81cd`, recomputed locally; **exact match** |
| Publication | 2026-09-19 |
| Associated author article | [`osmo-action5pro-unlock-bootloader-adbd`](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) — **now read in full**; [verified A-to-Z reconstruction](ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md) |

## 1. Complete original ZIP manifest (verified)

The archive contains precisely **two data files**, in two directories. It has no README, source code, host script, manifest, install instructions or camera timer patch. The static inspector found **no encrypted ZIP entries, traversal paths or symlink entries**. Both payloads begin with ELF magic `7f 45 4c 46`.

| Archive member | Uncompressed | Compressed | CRC32 | Extracted SHA-256 |
|---|---:|---:|---|---|
| `loader/RedMagicCommon_8Gen2_devprg` | 1,768,340 B | 766,871 B | `45331fc9` | `b85fb0e651f88f12e3c9b7b56c0f7229449c410f87fc20c6bc35698516383297` |
| `img-unlock/abl-factory.img` | 1,048,576 B | 160,665 B | `04005025` | `658af73f3319af4c07c733fe6ad184f68c299b678819815bbdacbaaff3b12466` |

Directory entries `loader/` and `img-unlock/` are zero-length. Aggregate uncompressed data is **2,816,916 B**. The published 906 KB ZIP is **not** the same as GitHub's automatically generated source-code ZIP for the tag.

## 2. File-level forensic observations

### `RedMagicCommon_8Gen2_devprg` — EDL bootstrap/loader candidate

- **Direct observation:** ELF32 little-endian, `e_type=EXEC`, `e_machine=1`; GNU `readelf` maps 1 to `WE32100`, but that label **must not** be interpreted as the target processor/host runtime. The file is a Qualcomm boot-image style container with no ELF section table; it is **not** a normal executable intended for this Linux development host.
- Entry address `0x22126000`; two PT_LOAD segments: file offset `0x74`, address `0x22126000`, size `0x20000`, and offset `0x20074`, address `0x22283000`, size `0x280`. Additional content sits outside these ordinary program segments, consistent with a vendor boot/programmer container; its detailed signed layout has not been proven.
- **Strings observed:** multiple `Qualcomm Technologies, Inc.` certificate references; UFS/eMMC and GPT code; `Enter PBL EDL USB`, `reset_to_edl`, `skip_ddr_init_in_EDL`, `Secure Boot:`, and `OEM_IMAGE_VERSION_STRING=crm-ubuntu261`. The file also contains `Unlock = Yes`, but **only as text at offsets approximately `0x19eb64` and `0x19ec08`**; this is **not proof that the target camera unlocks automatically**, nor an instruction to modify the binary.
- **Inference, not validated:** the filename references a **RedMagic Snapdragon 8 Gen 2** development programmer that Alliot used or bundled as part of his Qualcomm EDL research. Its provenance, target board compatibility, authentication/loader handshake and whether it can read or write the DJI's partitions are unconfirmed. A generic phone programmer is **not** a verified DJI rescue loader.

### `abl-factory.img` — factory ABL boot-image candidate

- **Direct observation:** 1 MiB ELF32 little-endian; `e_machine=40` (ARM); entry address `0x9fa00000`; three program headers, including a PT_LOAD segment at file offset `0x1000`, address `0x9fa00000`, size `0x32000`, and a non-load block around offset `0x33000`. No ELF section table; no user-visible shell commands or timer settings.
- **Certificate evidence (DER parsed with OpenSSL):** a leaf X.509 certificate at file offset `0x33218` has subject **`CN=SecTools Test User, O=SecTools`** and issuer **`CN=SECTOOLS SECP384R1 CURVE TEST ROOT0, O=QUALCOMM, OU=General Use Test Key 0 (for testing only)`**. Leaf validity: 2024-09-18 through 2044-09-13, serial `01`. This is an embedded **test-key-labelled** certificate chain, not evidence of a DJI production-certified image. Whether the boot ROM/bootloader on the owner's camera would accept it is unknown.
- `strings` finds mostly nonsemantic high-entropy-looking content and certificate text (e.g. `QUALCOMM`); there is no verified plaintext `Timer Shooting`, `36000`, `18000`, `dji_gui` or adbd patch table in this file. **Do not infer** that a firmware setting can be hex-edited directly here.
- **Inference, not validated:** the naming and certificate placement are compatible with a candidate factory/engineering ABL payload, but the actual boot-policy changes, AVB/rollback handling, partition name and authenticity are unproven. Writing this to an arbitrary device is a **brick risk**.

## 3. What this ZIP does and does not establish

| Question | Answer from files alone |
|---|---|
| Does Alliot publish the original DJI source code? | **No.** No source files here; his separate `action-control` repo adds a root-side app. |
| Is a boot/EDL unlock chain **plausible**? | **Author hardware-verified on AC204 firmware 10.00.16.13:** read-only GPT/backup → change two `devinfo` flags → replace active ABL with this image → engineering boot/root ADB. See [author's article](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) and [A-to-Z reconstruction](ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md). **Not tested or authorized on owner's hardware.** |
| Does the ZIP include `adbd`, a 10 h duration patch or Timer Shooting setter? | **No.** No such additional member. |
| Are there direct instructions/host tools/backup and unbrick scripts in ZIP? | **No.** Exactly two binary members. The separate author's **now-accessible blog** documents `bkerler/edl` (pinned), per-device GPT, backups, two writes and rollback; the ZIP itself does **not** include or validate any backups. |
| Is it safe to flash `abl-factory.img` to the Action 5? | **Not established.** No matching build/board signature verification, backup strategy or recovery validation. |
| Can an already rooted Action 5 run custom menu code? | **Yes, per Alliot's independent native/GUI research**, but not as proof of this ZIP's applicability to our device. |

## 4. Reproduce *static* verification (never execute either payload)

With an authentic local `.zip`, run:

```sh
python3 tools/inspect_alliot_unlock_zip.py ./action5pro-unlock-files.zip
python3 tools/inspect_alliot_unlock_zip.py ./action5pro-unlock-files.zip --preview-text
```

The script reads archive bytes without extraction, execution, flashing, root escalation or network access. It compares the whole-archive SHA-256 to the pinned release hash and enumerates **every entry** with its compressed/uncompressed size, CRC, SHA-256, magic bytes, encryption state, symlink flag and path-traversal warnings. It limits entry reading to 16 MiB and cumulative uncompressed reading to 64 MiB; skipped entries remain visible in the manifest. The owner-provided ZIP passed all these checks and the **existing automated synthetic tests**.

After this inventory passed, the two specific members were extracted **offline** to an isolated transient directory, then analyzed with `file`, `readelf`, `strings`, `od`, `objdump`, `openssl x509`, and `sha256sum`. No binary was run; no proprietary payload is committed. Future work may use Ghidra on these already-verified hashes. Treat both vendor/third-party blobs as untrusted; a potentially matching SoC does **not** prove board revision, firmware, signing or recovery compatibility.

## Detailed remaining questions to answer file-by-file

1. **Done:** exact filenames, sizes, ZIP and member cryptographic hashes, ELF formats. **Open:** provenance and licenses of both vendor/third-party boot binaries.
2. **Done:** no scripts in ZIP; **author blog read**: EDL `05c6:9008` with tested RedMagic programmer, `devinfo` two-bit flags and factory ABL active-slot replacement, followed by readback. **Open:** applicability to our exact camera; no speculative execution.
3. Which Action 5 Pro **firmware build**, hardware board and boot-chain version are targeted? What guards prevent use on Action 4/6 or another AC204 revision?
4. Is Qualcomm EDL/9008 merely used to **start temporary `adbd`**, or to write any partition and change verified boot / bootloader state? Which parts persist over reboot?
5. **Observed:** Qualcomm/test-labelled X.509 certificate in factory ABL; **open:** actual accepted OEM key/secure-boot policy, programmer handshake and flash layout. Are these vendor blobs redistributable or authentic beyond the release ZIP hash?
6. Can all critical partitions be **backed up before** first destructive operation? How is stock firmware restored if the camera will not boot?
7. Can root ADB be enabled **without** firmware flashing? Is Factory Mode involved and reversible? Does unlocking erase user settings/media?
8. What exact **root command output** and `ro.product.name`, `/usr/lib/*` hashes were captured on real Action 5 hardware? Can we cross-check the [Alliot ABI audit](ALLIOT_ACTION5_ROOT_ABI_AUDIT_2026-11-03.md)?
9. Where are the **Timer Shooting** task and GUI validation implemented? The ZIP is **confirmed to contain no timer-related source or documented setter**, and serves only as an unlock research artifact.
10. Is an independently proven recovery path available? If not, **stop before any boot/EDL/flash experiments**.

## Separate blocker for the 10-hour feature

**The ZIP alone does not provide a reproducible ADB-root path**, because it has no procedure, compatibility check or recovery script. However, the [author's newly-read article](https://blog.alliot.tech/post/osmo-action5pro-unlock-bootloader-adbd) **does document** his AC204/firmware 10.00.16.13 procedure, individual-device backups and rollback. The owner-camera compatibility is still unverified. Even if root ADB becomes available, that **does not** identify the native Timer Shooting setter. The high-leverage next artifact remains a device-matched **read-only** copy of the GUI/service ELF or a 3 h vs 5 h Timer Shooting settings trace. See [firmware target](ACTION5_TIMER10H_FIRMWARE_TARGET.md) and [A-to-Z reconstruction](ALLIOT_A_TO_Z_FIRMWARE_ACCESS.md).
