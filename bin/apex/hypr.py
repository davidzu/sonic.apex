"""Hyprland workspace helpers."""

from __future__ import annotations

import json
import subprocess
import time

_CACHE_TTL = 0.6
_cache = {"at": 0.0, "value": None}


def _hypr(*args, timeout=0.3):
    try:
        return subprocess.check_output(["hyprctl", *args], text=True, timeout=timeout, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""


def _query():
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


def active():
    """Active workspace/window, cached briefly to avoid a hyprctl per OLED frame."""
    now = time.monotonic()
    if _cache["value"] is not None and now - _cache["at"] < _CACHE_TTL:
        return _cache["value"]
    value = _query()
    _cache["value"] = value
    _cache["at"] = now
    return value


def dispatch(command):
    _hypr("dispatch", *command.split())
