**Documentation:** [Install](install.md) • [Backup & restore](backup-restore.md) • [Build](build.md) • [Config](config.md) • [VIA & debug](via-debug.md)

# Install

nxmk runs from Flash Bank 2 (`0x08010000-0x0801FFFF`) of the Hybrid's STM32L072.
The factory Bank 1 updater stays in place and is the install path. Keep a
[full backup](backup-restore.md) before the first flash.

The Hybrid update file (`.hfb`) is a composite container: a 64 KiB STM32 image
followed by the factory payload for the board's second chip. That payload is
proprietary and is not in this repository, so you build the `.hfb` locally by
patching your own copy of the official PFU file. The patcher replaces only the
STM32 image and recomputes the CRCs; the rest of the container is kept
unchanged.

## 1. Build or obtain the STM32 binary

See [Build](build.md). The result is `build/hhkb-script/nxmk_hhkb_stm32l072.bin`.
The CI workflow also uploads it as `nxmk-hhkb-hybrid-ansi.bin` together with
`hhkb.html` and `via.json` (`.github/workflows/build_test.yml`).

## 2. Patch the official Hybrid ANSI update

Download the official ANSI update `HHKB800_FW_A048.hfb` from the
[HHKB download page](https://happyhackingkb.com/download/). The patcher accepts
only the file with SHA-256
`635b995eb5a15aa50c2cedc60da7d8998fcca8285a09d41d984c07fffcaf9d43`.

Python:

```bash
mkdir -p keyboards/hhkb/local
# put the unmodified HHKB800_FW_A048.hfb in keyboards/hhkb/local/
python3 tools/hhkb/patch_hybrid_hfb.py \
  build/hhkb-script/nxmk_hhkb_stm32l072.bin \
  keyboards/hhkb/local/HHKB800_FW_A048.hfb \
  keyboards/hhkb/local/nxmk_hybrid.hfb
```

The output path must not exist (the script refuses to overwrite) and must end
in `.hfb`. The output container is model `AHUX01`, version `A0.50`.

Browser: open [`tools/hhkb/hhkb.html`](../../../../tools/hhkb/hhkb.html) locally
in Chrome or Edge, use the **Hybrid patching** tab, select the official HFB and
the nxmk `.bin`, and click **Patch and download**. The page checks the stock
file's CRCs, version and SHA-256 and the binary's embedded model/version
metadata (`DMKHHKB1|<model>|<version>|END`, defined in
`platforms/stm32l072/platform.c`). Processing is local.

> `patch_hybrid_hfb.py --stm32-only` builds an experimental Hybrid container
> with a deliberately invalid blank radio image. It is not part of the
> supported install flow and is not documented here.

Do not commit or redistribute the patched `.hfb`: it contains the vendor
payload.

## 3. Get the keyboard into the Bank 1 updater

- **Running the stock firmware:** the PFU update interface is already
  available. Do not use SW6.
- **Running nxmk:** nxmk has a different USB identity (`cafe:4014`), so the
  PFU tools cannot see it. With the keyboard unplugged, set SW6 ON, connect
  USB, and return SW6 to OFF once the Bank 1 device appears. This invalidates
  Bank 2 (erases its first 128-byte page); see
  [SW6 recovery](backup-restore.md#sw6-recovery). Keep SW5 OFF unless you also
  want the nxmk EEPROM records erased.

> Keep SW6 OFF during normal use and while flashing.

## 4. Flash the `.hfb`

### Python flasher

`tools/hhkb/hhkb_flasher.py` talks to the PFU raw HID update interface
(VID `0x04FE`, usage page `0xFF00`, usage `0x01`) using the `E0`-`E3`
commands.

```bash
uv run --with hidapi python3 tools/hhkb/hhkb_flasher.py --info
uv run --with hidapi python3 tools/hhkb/hhkb_flasher.py keyboards/hhkb/local/nxmk_hybrid.hfb
```

Before sending anything it checks both CRCs, that the container model matches
the connected keyboard, and (with a prompt to continue) that the Bank 2 reset
vector lies in `0x08010000-0x0801FFFF`. `--skip-crc`, `--skip-model-check` and
`--force` turn those local checks off; they do not bypass the keyboard's own
validation.
Afterwards, if the container carries the nxmk metadata marker, it waits for a
`cafe:4014` device with a VIA raw HID interface (`--skip-verify` disables
this).

### Browser flasher

Open `tools/hhkb/hhkb.html` (Chrome or Edge, WebHID), go to **Flash keyboard**,
select the `.hfb` and click **Connect and flash**. Grant access to the PFU
interface when prompted; select it again after the recovery reboot.

### Official HHKB Keymap Tool

Open the `.hfb` in the [HHKB Keymap Tool](https://happyhackingkb.com/download/).
After the transfer the tool may report an error because the device
re-enumerates with a different USB identity. This is expected behaviour
inherited from upstream notes; confirm success by checking that
`cafe:4014` appears.

### DFU / SWD

ROM DFU and SWD write Bank 2 directly and bypass the PFU metadata, so they are
recovery/development paths only. See [Backup & restore](backup-restore.md).

## 5. Load `via.json`

Load [`keyboards/hhkb/via.json`](../../via.json) in the
[VIA web app](https://www.usevia.app/) (see [VIA & debug](via-debug.md#load-the-custom-definition)).
If VIA does not see the keyboard, follow
[Check USB detection](via-debug.md#check-usb-detection).
