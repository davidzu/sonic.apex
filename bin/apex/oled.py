"""Apex 7 TKL OLED (128x40) via HID feature reports on interface 1.

Pillow is imported lazily: the CLI's `status` path must not pay for it.
"""

from __future__ import annotations

import fcntl
import os

OLED_WIDTH = 128
OLED_HEIGHT = 40
OLED_REPORT_ID = 0x61
VENDOR = 0x1038
PRODUCT = 0x1618
OLED_INTERFACE = 1

_IOC_WRITE = 1
_IOC_READ = 2

# hidraw paths are stable while the device is plugged in; cache the lookup and
# the open fd so a 4 fps page does not reopen the node every frame.
_cached_path = None
_fd = None


def _ioc(direction, type_, nr, size):
    return (direction << 30) | (size << 16) | (ord(type_) << 8) | nr


def hidios_feature(length):
    return _ioc(_IOC_WRITE | _IOC_READ, "H", 0x06, length)


def _hid_id(sys_path):
    try:
        with open(os.path.join(sys_path, "device", "uevent"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("HID_ID="):
                    parts = line.strip().split("=")[1].split(":")
                    return int(parts[1], 16), int(parts[2], 16)
    except (OSError, ValueError, IndexError):
        pass
    return None, None


def _interface_number(sys_path):
    iface = os.path.join(sys_path, "device", "..", "bInterfaceNumber")
    try:
        with open(iface, encoding="utf-8") as fh:
            return int(fh.read().strip(), 16)
    except (OSError, ValueError):
        return None


def find_oled_hidraw(vendor=VENDOR, product=PRODUCT, interface=OLED_INTERFACE):
    global _cached_path
    if _cached_path and os.path.exists(_cached_path):
        return _cached_path
    try:
        names = sorted(os.listdir("/sys/class/hidraw"))
    except OSError:
        return None
    for name in names:
        sys_path = os.path.join("/sys/class/hidraw", name)
        vid, pid = _hid_id(sys_path)
        if vid != vendor or pid != product:
            continue
        if _interface_number(sys_path) == interface:
            _cached_path = os.path.join("/dev", name)
            return _cached_path
    _cached_path = None
    return None


def image_to_report(image):
    """Convert a PIL image to the 642-byte feature report payload."""
    from PIL import Image

    im = image.convert("L")
    if im.size != (OLED_WIDTH, OLED_HEIGHT):
        im = im.resize((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
    # Threshold and pack in C. PIL packs "1" mode MSB-first per byte, which is
    # exactly the controller's expected bit order.
    packed = im.point(lambda p: 255 if p > 127 else 0, mode="1").tobytes()
    return bytes([OLED_REPORT_ID]) + packed + b"\x00"


def _open(hidraw=None):
    global _fd
    if _fd is not None and hidraw is None:
        return _fd
    path = hidraw or find_oled_hidraw()
    if not path:
        raise FileNotFoundError("Apex 7 TKL OLED hidraw (interface 1) not found")
    if hidraw is None:
        _fd = os.open(path, os.O_RDWR)
        return _fd
    return os.open(path, os.O_RDWR)


def reset():
    """Drop the cached fd/path (call after a device error or replug)."""
    global _cached_path, _fd
    if _fd is not None:
        try:
            os.close(_fd)
        except OSError:
            pass
    _fd = None
    _cached_path = None


def send_report(data, hidraw=None):
    global _fd
    buf = bytearray(data)
    fd = _open(hidraw)
    try:
        fcntl.ioctl(fd, hidios_feature(len(buf)), buf, True)
    except OSError:
        if hidraw is None:
            reset()
        else:
            try:
                os.close(fd)
            except OSError:
                pass
        raise
    if hidraw is not None:
        try:
            os.close(fd)
        except OSError:
            pass
    return hidraw or _cached_path


def send_image(image, hidraw=None):
    return send_report(image_to_report(image), hidraw=hidraw)


def send_file(path, hidraw=None):
    from PIL import Image

    with Image.open(path) as img:
        return send_image(img, hidraw=hidraw)


def clear(hidraw=None):
    from PIL import Image

    return send_image(Image.new("L", (OLED_WIDTH, OLED_HEIGHT), 0), hidraw=hidraw)
