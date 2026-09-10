"""Read the Apex 7 TKL OLED control wheel (and optional key reactive input)."""

from __future__ import annotations

import glob
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


def _device_name(event_node):
    path = f"/sys/class/input/{os.path.basename(event_node)}/device/name"
    try:
        return open(path, encoding="utf-8").read().strip()
    except OSError:
        return ""


def apex_event_nodes():
    nodes = {"wheel": [], "keys": []}
    for node in sorted(glob.glob("/dev/input/event*")):
        name = _device_name(node)
        if "Apex 7 TKL" not in name and "SteelSeries" not in name:
            continue
        if "Consumer Control" in name or "Mouse" in name:
            nodes["wheel"].append(node)
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
        import fcntl
        try:
            fcntl.ioctl(self.fd, EVIOCGRAB, 1 if grab else 0)
            self.grabbed = bool(grab)
        except OSError:
            self.grabbed = False

    def read(self):
        events = []
        while True:
            try:
                buf = os.read(self.fd, EVENT.size)
            except BlockingIOError:
                break
            except OSError:
                break
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


def decode_wheel(events, invert=False):
    """Return (rel_steps, key_steps, clicked) from a batch of input events.

    rel_steps comes from the physical roller (REL_WHEEL / HWHEEL).
    key_steps comes from KEY_VOLUME* (already bound by Hyprland unless grabbed).
    clicked is True on a wheel / mute press.
    """
    rel_steps = 0
    hires = 0
    key_steps = 0
    clicked = False
    for etype, code, value in events:
        if etype == EV_REL:
            if code in (REL_WHEEL, REL_HWHEEL) and value != 0:
                rel_steps += int(value)
            elif code in (REL_WHEEL_HI_RES, REL_HWHEEL_HI_RES):
                hires += int(value)
        elif etype == EV_KEY and value == 1:
            if code in (KEY_MUTE, BTN_MIDDLE, BTN_LEFT):
                clicked = True
            elif code == KEY_VOLUMEUP:
                key_steps += 1
            elif code == KEY_VOLUMEDOWN:
                key_steps -= 1
    if rel_steps == 0 and abs(hires) >= HIRES_NOTCH / 2:
        rel_steps = int(round(hires / HIRES_NOTCH))
    if invert:
        rel_steps = -rel_steps
        key_steps = -key_steps
    return rel_steps, key_steps, clicked
