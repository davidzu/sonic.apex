"""Read the Apex 7 TKL OLED control wheel (and optional key reactive input)."""

from __future__ import annotations

import glob
import fcntl
import os
import struct

# struct input_event on 64-bit Linux: timeval(16) + type(2) + code(2) + value(4)
EVENT = struct.Struct("llHHi")
EV_KEY = 0x01
EV_REL = 0x02
REL_HWHEEL = 0x06
REL_WHEEL = 0x08
REL_WHEEL_HI_RES = 0x0B
REL_HWHEEL_HI_RES = 0x0C
KEY_MUTE = 113
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
BTN_MIDDLE = 0x112
BTN_LEFT = 0x110
EVIOCGRAB = 0x40044590

HIRES_NOTCH = 120


class DeviceGone(OSError):
    """The event node disappeared (unplug, dock drop, suspend/resume)."""


def _device_name(event_node):
    path = f"/sys/class/input/{os.path.basename(event_node)}/device/name"
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def apex_event_nodes():
    """Group Apex event nodes by role.

    ``wheel``  — consumer control: media keys and the roller's HWHEEL/click.
    ``pointer`` — the keyboard's built-in pointer node (REL_X/Y/WHEEL). It also
                  receives events from a mouse plugged into the passthrough port,
                  so it is never used for wheel clicks.
    ``keys``   — the main keyboard node, used for reactive lighting.
    """
    nodes = {"wheel": [], "pointer": [], "keys": []}
    for node in sorted(glob.glob("/dev/input/event*")):
        name = _device_name(node)
        if "Apex 7 TKL" not in name and "SteelSeries" not in name:
            continue
        if "Consumer Control" in name:
            nodes["wheel"].append(node)
        elif "Mouse" in name:
            nodes["pointer"].append(node)
        else:
            nodes["keys"].append(node)
    return nodes


class Evdev:
    def __init__(self, path, grab=False):
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.grabbed = False
        if grab:
            self.set_grab(True)

    def fileno(self):
        return self.fd

    def set_grab(self, grab):
        try:
            fcntl.ioctl(self.fd, EVIOCGRAB, 1 if grab else 0)
            self.grabbed = bool(grab)
        except OSError:
            self.grabbed = False

    def read(self):
        """Drain pending events, or raise DeviceGone when the node is gone.

        A hung-up fd stays readable forever, so treating EOF/ENODEV as "no
        events" would spin the select() loop at 100% CPU.
        """
        events = []
        while True:
            try:
                buf = os.read(self.fd, EVENT.size)
            except BlockingIOError:
                break
            except OSError as exc:
                raise DeviceGone(self.path) from exc
            if not buf:
                raise DeviceGone(self.path)
            if len(buf) < EVENT.size:
                break
            _sec, _usec, etype, code, value = EVENT.unpack(buf)
            events.append((etype, code, value))
        return events

    def close(self):
        if self.grabbed:
            try:
                self.set_grab(False)
            except OSError:
                pass
        try:
            os.close(self.fd)
        except OSError:
            pass


class WheelDecoder:
    """Turn input events into wheel steps, keeping HI_RES remainders.

    High-resolution wheels count in 120-unit notches; a slow scroll that does
    not reach a full notch must carry over to the next read instead of being
    dropped.
    """

    def __init__(self):
        self._hires = 0

    def feed(self, events, invert=False, allow_pointer_buttons=False):
        """Return (rel_steps, key_steps, clicked) for one batch of events."""
        rel_steps = 0
        key_steps = 0
        clicked = False
        for etype, code, value in events:
            if etype == EV_REL:
                if code in (REL_WHEEL, REL_HWHEEL) and value != 0:
                    rel_steps += int(value)
                elif code in (REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES):
                    self._hires += int(value)
            elif etype == EV_KEY and value == 1:
                if code == KEY_MUTE:
                    clicked = True
                elif code == BTN_MIDDLE:
                    clicked = True
                elif code == BTN_LEFT and allow_pointer_buttons:
                    clicked = True
                elif code == KEY_VOLUMEUP:
                    key_steps += 1
                elif code == KEY_VOLUMEDOWN:
                    key_steps -= 1
        if self._hires:
            whole = int(self._hires / HIRES_NOTCH)
            if whole:
                rel_steps += whole
                self._hires -= whole * HIRES_NOTCH
        if invert:
            rel_steps = -rel_steps
            key_steps = -key_steps
        return rel_steps, key_steps, clicked


def decode_wheel(events, invert=False, allow_pointer_buttons=False):
    """One-shot decode for CLI/tests. Use WheelDecoder to keep HI_RES state."""
    return WheelDecoder().feed(events, invert, allow_pointer_buttons)
