# Architecture

`Panel.qml` is the bar widget entry point (manifest kind: `bar-widget` only).
It renders the Apex status in the Omarchy bar and shells out to `bin/apexctl`
(a Python CLI) for all device work. No QML-side device I/O.

Ownership map:

- `bin/apex/` — Python package: `daemon.py` (long-running control daemon),
  `cli.py` (`apexctl` command surface), `rgb.py` (OpenRGB SDK on
  127.0.0.1:6742), `oled.py` (USB HID interface 1), `wheel.py`, `hypr.py`
  (Hyprland integration), `mpris.py` (media titles for the OLED),
  `config.py`, `layout.py`, `render.py` (OLED frame rendering).
- `hooks/` — post-boot and theme-set hooks so lighting follows
  `omarchy theme set`.
- `systemd/apexctl.service` — user service for the daemon.
- `udev/99-steelseries-apex.rules` — hidraw permissions for the OLED.
- `install/`, `uninstall/` — first-load install and clean removal.

State: device state lives in the `apexctl` daemon, not in QML. The panel is
stateless across reloads and re-reads state on demand. Destroying the widget
does not stop the daemon (documented deliberate choice; the daemon is owned
by the user systemd service).

External text rendered on the OLED or in tooltips uses explicit
`Text.PlainText` content. No Qt AutoText.

Node and Python/Pillow are development/runtime dependencies respectively;
Node is used only by portable checks, never by the runtime widget.

Do not declare additional manifest kinds (panel/overlay/menu/service) until
their entry points exist.
