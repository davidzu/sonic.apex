# Apex Keyboard

Omarchy shell plugin for the **SteelSeries Apex 7 / Apex 7 TKL**: per-key RGB, the 128×40 OLED, and the OLED scroll wheel.

## Install

```bash
omarchy plugin add https://github.com/davidzu/sonic.apex.git --enable
```

That clones the plugin, validates it, and enables the bar widget. On first load the panel:

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

The OLED talks to USB HID interface 1. If `apexctl oled clock` says the hidraw is missing or not writable:

```bash
sudo cp ~/.config/omarchy/plugins/sonic.apex/udev/99-steelseries-apex.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger
```

Unplug/replug the keyboard if it still cannot open the device.

## Use it

Click the keyboard icon in the bar, or:

```bash
apexctl status
apexctl rgb theme|solid|wave|breathe|rainbow|reactive|off
apexctl rgb solid -c '#89b4fa' -b 70
apexctl rgb -k 'Enter=#f38ba8' -k 'Space=#89b4fa'
apexctl oled clock|now-playing|workspace|logo|text|clear
apexctl oled --text 'hello'
apexctl oled --image ~/Pictures/logo.png
apexctl wheel volume|workspace|brightness|oled|rgb
```

Config lives in `~/.config/omarchy/apex.json` (created on first run).

Wheel default is **volume** (Hyprland already binds `XF86Audio*`). Other modes grab the roller so it does not also change volume. Click the wheel to mute / cycle.

## Uninstall

```bash
~/.config/omarchy/plugins/sonic.apex/uninstall
omarchy plugin remove sonic.apex
```

## Manual / local checkout

```bash
git clone https://github.com/davidzu/sonic.apex.git ~/.config/omarchy/plugins/sonic.apex
~/.config/omarchy/plugins/sonic.apex/install
omarchy plugin enable sonic.apex --section right
```

## License

MIT
