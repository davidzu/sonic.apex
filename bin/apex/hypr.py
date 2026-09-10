"""Hyprland workspace helpers."""

from __future__ import annotations

import json
import subprocess


def _hypr(*args, timeout=0.3):
    try:
        return subprocess.check_output(["hyprctl", *args], text=True, timeout=timeout, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""


def active():
    ws = {}
    win = {}
    try:
        ws = json.loads(_hypr("activeworkspace", "-j") or "{}")
    except json.JSONDecodeError:
        ws = {}
    try:
        win = json.loads(_hypr("activewindow", "-j") or "{}")
    except json.JSONDecodeError:
        win = {}
    name = str(ws.get("name") or ws.get("id") or "")
    title = str(win.get("title") or "")
    klass = str(win.get("class") or "")
    return {"workspace": name, "window": title, "class": klass}


def dispatch(command):
    _hypr("dispatch", *command.split())
