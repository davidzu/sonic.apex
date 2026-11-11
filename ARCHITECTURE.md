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

## Daemon contracts

- **Single instance.** The daemon takes an exclusive `flock` on
  `$XDG_RUNTIME_DIR/sonic-apex.sock.lock` before binding the socket and exits 0
  if another instance owns it. Without this a second start unlinks the live
  socket and leaves an orphan fighting over the device.
- **Hot-plug.** Event nodes are re-scanned every 2 s. A node that reports EOF
  or `ENODEV` raises `DeviceGone`, is closed, and is reopened when it returns;
  a hung-up fd must never stay in the `select()` set or the loop spins at 100%
  CPU.
- **Wheel roles.** The consumer-control node supplies media keys and clicks.
  The pointer node also reports roller motion but may carry a mouse plugged
  into the passthrough port, so it never contributes wheel clicks and its grab
  is opt-out (`wheel.grab_pointer`).
- **RGB push.** The daemon renders at 24 fps but only sends a frame when the
  colour tuple changed, so static modes cost one USB write instead of 24/s.
  A lost OpenRGB connection is retried every 5 s.
- **OLED push.** Frames are compared before sending; the hidraw fd and image
  decode are cached, and Pillow is imported lazily so `apexctl status` stays
  cheap.

External text rendered on the OLED or in tooltips uses explicit
`Text.PlainText` content. No Qt AutoText.

Node and Python/Pillow are development/runtime dependencies respectively;
Node is used only by portable checks, never by the runtime widget.

Do not declare additional manifest kinds (panel/overlay/menu/service) until
their entry points exist.
