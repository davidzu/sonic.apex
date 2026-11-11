<h1 align="center">Apex Keyboard</h1>

<p align="center">Omarchy shell plugin for the SteelSeries Apex 7 / Apex 7 TKL:
per-key RGB, the 128×40 OLED, and the OLED scroll wheel.</p>

## Install

```bash
omarchy plugin add https://github.com/davidzu/sonic.apex.git --enable
```

That clones the plugin, validates it, and enables the bar widget. On first
load the panel:

- puts `apexctl` on `PATH` (`~/.local/bin`)
- enables the `apexctl` user systemd service
- installs theme-set and post-boot hooks so lighting follows `omarchy theme set`

Re-running install is cheap: it stamps `~/.local/state/apex/install.stamp` and
does nothing when the version and unit file are unchanged.

### Requirements

- Omarchy (Hyprland + Quickshell) — verified on `omarchy 4.5.0-3`
- Python 3 with Pillow (`python-pillow`, already on Omarchy)
- [OpenRGB](https://openrgb.org/) for RGB (`omarchy pkg add openrgb`), with its SDK server on `127.0.0.1:6742`

Start OpenRGB once:

```bash
systemctl --user enable --now openrgb.service
```

If that unit does not exist yet:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/openrgb.service <<'EOF'
[Unit]
Description=OpenRGB SDK server
After=graphical-session.target

[Service]
ExecStart=/usr/bin/openrgb --server --server-port 6742
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

[Install]
WantedBy=graphical-session.target
EOF
systemctl --user enable --now openrgb.service
```

The restart limits matter: without them a port conflict restarts OpenRGB every
few seconds forever.

### HID permissions

The OLED talks to USB HID interface 1. If `apexctl oled clock` says the
hidraw is missing or not writable:

```bash
sudo cp ~/.config/omarchy/plugins/sonic.apex/udev/99-steelseries-apex.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Unplug/replug the keyboard if it still cannot open the device.

## Use it

Click the **Apex Keyboard** widget in the bar (right section) to open the
panel: RGB effects, OLED pages (clock, media, system), and wheel modes.

CLI examples:

```bash
apexctl rgb wave --speed 2
apexctl rgb gradient -p ocean
apexctl oled clock
apexctl wheel mode workspace  # volume | workspace | brightness | oled | rgb
apexctl reload               # re-read the theme palette, keep current mode/page
apexctl modes                # modes, pages, and profiles as JSON
apexctl status --json
```

`rgb`, `oled`, and `wheel` work without the daemon by applying the change
directly and saving it for later. `reload`, `oled --next/--prev`, and wheel
mode switching need the daemon.

### Wheel and the passthrough port

Volume mode does not grab anything, so the media keys keep reaching Hyprland.
Every other wheel mode grabs the keyboard's consumer-control node and its
pointer node, which keeps roller motion out of the focused application. If you
plug a mouse into the Apex passthrough port and it stops working, disable the
pointer grab:

```bash
apexctl wheel --no-grab-pointer
```

### Configuration

Settings live in `~/.config/omarchy/apex/config.json`. An older
`~/.config/omarchy/apex.json` is migrated once on first start and renamed
`apex.json.migrated`.

## Uninstall

```bash
~/.config/omarchy/plugins/sonic.apex/uninstall
omarchy plugin remove sonic.apex --yes
```

`uninstall` stops and removes the user service, the `apexctl` symlink, the
Omarchy hooks, and the install stamp. It keeps your config and never touches
unrelated desktop configuration. The udev rule is system-wide and is left for
you to remove:

```bash
sudo rm /etc/udev/rules.d/99-steelseries-apex.rules
```

## Development

Run the portable checks from the repository root:

```bash
./tests/run
```

That runs the structural checks, the Node tests, and the Python unit suite
(no hardware needed). On the target Omarchy machine also run
`omarchy plugin validate .` and record the installed `omarchy-version`.
Portable validation covers structure, metadata, colour maths, event decoding,
and OLED framing only; it does not establish live desktop compatibility. Record
actual tests in [docs/ACCEPTANCE.json](docs/ACCEPTANCE.json).

[Architecture](ARCHITECTURE.md) · [Developing](docs/DEVELOPMENT.md) · [Release process](docs/RELEASE.md) · [Contributing](CONTRIBUTING.md)

## Credits

Built from [omarchy-plugin-template](https://github.com/tcballard/omarchy-plugin-template)
guidance and the Omarchy template set. See [CREDITS.md](CREDITS.md).

## Licence

[MIT](LICENSE).
