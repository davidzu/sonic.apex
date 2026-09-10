"""Apex 7 TKL OLED (128x40) via HID feature reports on interface 1."""

from __future__ import annotations

import fcntl
import os

from PIL import Image

OLED_WIDTH = 128
OLED_HEIGHT = 40
OLED_REPORT_ID = 0x61
VENDOR = 0x1038
PRODUCT = 0x1618
OLED_INTERFACE = 1

_IOC_WRITE = 1
_IOC_READ = 2


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
        return int(open(iface, encoding="utf-8").read().strip(), 16)
    except (OSError, ValueError):
        return None


def find_oled_hidraw(vendor=VENDOR, product=PRODUCT, interface=OLED_INTERFACE):
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
            return os.path.join("/dev", name)
    return None


def image_to_report(image: Image.Image) -> bytes:
    im = image.convert("L")
    if im.size != (OLED_WIDTH, OLED_HEIGHT):
        im = im.resize((OLED_WIDTH, OLED_HEIGHT), Image.Resampling.LANCZOS)
    pix = im.load()
    bits = []
    for y in range(OLED_HEIGHT):
        for x in range(OLED_WIDTH):
            bits.append(1 if pix[x, y] > 127 else 0)
    payload = [int("".join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    return bytes([OLED_REPORT_ID, *payload, 0x00])


def send_report(data: bytes, hidraw=None):
    path = hidraw or find_oled_hidraw()
    if not path:
        raise FileNotFoundError("Apex 7 TKL OLED hidraw (interface 1) not found")
    buf = bytearray(data)
    fd = os.open(path, os.O_RDWR)
    try:
        fcntl.ioctl(fd, hidios_feature(len(buf)), buf, True)
    finally:
        os.close(fd)
    return path


def send_image(image: Image.Image, hidraw=None):
    return send_report(image_to_report(image), hidraw=hidraw)


def send_file(path, hidraw=None):
    return send_image(Image.open(path), hidraw=hidraw)


def clear(hidraw=None):
    return send_image(Image.new("L", (OLED_WIDTH, OLED_HEIGHT), 0), hidraw=hidraw)
