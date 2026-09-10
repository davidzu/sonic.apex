"""Read the current MPRIS player over the session bus without extra deps."""

from __future__ import annotations

import re
import subprocess

_DEST_RE = re.compile(r"org\.mpris\.MediaPlayer2\.[^\s'\",]+")


def _gdbus(*args, timeout=0.4):
    try:
        return subprocess.check_output(
            ["gdbus", "call", "--session", *args],
            text=True,
            timeout=timeout,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return ""


def _list_names():
    out = _gdbus(
        "--dest", "org.freedesktop.DBus",
        "--object-path", "/org/freedesktop/DBus",
        "--method", "org.freedesktop.DBus.ListNames",
    )
    return _DEST_RE.findall(out)


def _unescape(value):
    value = value.replace("\\'", "'")
    return bytes(value, "utf-8").decode("unicode_escape", "replace")


def _kv(blob, key):
    match = re.search(rf"'{re.escape(key)}':\s*<\s*'([^']*)'\s*>", blob)
    if match:
        return _unescape(match.group(1))
    match = re.search(rf"'{re.escape(key)}':\s*<\s*\[(.*?)\]\s*>", blob)
    if match:
        names = re.findall(r"'([^']*)'", match.group(1))
        return ", ".join(_unescape(n) for n in names)
    return ""


def now_playing():
    for dest in _list_names():
        meta = _gdbus(
            "--dest", dest,
            "--object-path", "/org/mpris/MediaPlayer2",
            "--method", "org.freedesktop.DBus.Properties.Get",
            "org.mpris.MediaPlayer2.Player",
            "Metadata",
        )
        status = _gdbus(
            "--dest", dest,
            "--object-path", "/org/mpris/MediaPlayer2",
            "--method", "org.freedesktop.DBus.Properties.Get",
            "org.mpris.MediaPlayer2.Player",
            "PlaybackStatus",
        )
        title = _kv(meta, "xesam:title")
        artist = _kv(meta, "xesam:artist") or _kv(meta, "xesam:albumArtist")
        playing = "Playing" in status
        if title or artist:
            return {
                "title": title or "Unknown",
                "artist": artist,
                "playing": playing,
                "player": dest.rsplit(".", 1)[-1],
            }
    return {"title": "", "artist": "", "playing": False, "player": ""}
