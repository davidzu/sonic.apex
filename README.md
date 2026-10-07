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

### Requirements

- Omarchy (Hyprland + Quickshell)
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

[Install]
WantedBy=graphical-session.target
EOF
systemctl --user enable --now openrgb.service
```

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
apexctl oled clock
apexctl wheel mode media
```

## Development

Run the portable checks from the repository root:

```bash
./tests/run
```

On the target Omarchy machine also run `omarchy plugin validate .` and record
the installed `omarchy-version`. Portable validation covers structure and
metadata only; it does not establish live desktop compatibility. Record
actual tests in [docs/ACCEPTANCE.json](docs/ACCEPTANCE.json).

[Architecture](ARCHITECTURE.md) · [Developing](docs/DEVELOPMENT.md) · [Release process](docs/RELEASE.md) · [Contributing](CONTRIBUTING.md)

## Credits

Built from [omarchy-plugin-template](https://github.com/tcballard/omarchy-plugin-template)
guidance and the Omarchy template set. See [CREDITS.md](CREDITS.md).

## Licence

[MIT](LICENSE).
