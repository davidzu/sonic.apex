"""Portable tests for the apexctl runtime package (no hardware required)."""

from __future__ import annotations

import io
import json
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin"))

from apex import config, layout, oled, render, rgb, wheel  # noqa: E402


class ParseHexTests(unittest.TestCase):
    def test_accepts_hash_and_bare(self):
        self.assertEqual(rgb.parse_hex("#89b4fa"), (0x89, 0xB4, 0xFA))
        self.assertEqual(rgb.parse_hex("89b4fa"), (0x89, 0xB4, 0xFA))

    def test_rejects_bad_input(self):
        self.assertEqual(rgb.parse_hex("", ("fallback",)), ("fallback",))
        self.assertEqual(rgb.parse_hex("#zzzzzz", (1, 2, 3)), (1, 2, 3))
        self.assertEqual(rgb.parse_hex("12345", (1, 2, 3)), (1, 2, 3))

    def test_scale_color_clamps(self):
        self.assertEqual(rgb.scale_color((100, 200, 255), 0), (0, 0, 0))
        self.assertEqual(rgb.scale_color((100, 200, 255), 100), (100, 200, 255))
        self.assertEqual(rgb.scale_color((100, 200, 255), 150), (100, 200, 255))
        self.assertEqual(rgb.scale_color((100, 200, 255), 50), (50, 100, 127))


class ColorMathTests(unittest.TestCase):
    def test_mix_endpoints(self):
        self.assertEqual(rgb.mix((0, 0, 0), (255, 255, 255), 0), (0, 0, 0))
        self.assertEqual(rgb.mix((0, 0, 0), (255, 255, 255), 1), (255, 255, 255))
        self.assertEqual(rgb.mix((0, 0, 0), (255, 255, 255), 2), (255, 255, 255))

    def test_hsv_wraps(self):
        self.assertEqual(rgb.hsv(0.0), rgb.hsv(1.0))
        self.assertEqual(rgb.hsv(0.0, 0.0, 0.0), (0, 0, 0))

    def test_gradient_is_cyclic(self):
        colors = [rgb.parse_hex(h) for h in rgb.PROFILES["ocean"]]
        self.assertEqual(rgb.sample_gradient(colors, 0.0), rgb.sample_gradient(colors, 1.0))
        mid = rgb.sample_gradient(colors, 0.5)
        self.assertTrue(all(0 <= c <= 255 for c in mid))

    def test_profile_fallback(self):
        self.assertEqual(list(rgb.profile_colors("nope")), list(rgb.profile_colors("sunset")))

    def test_every_profile_is_valid_hex(self):
        for name, hexes in rgb.PROFILES.items():
            self.assertGreaterEqual(len(hexes), 2, name)
            for value in hexes:
                self.assertEqual(len(value), 7, f"{name}: {value}")
                self.assertEqual(rgb.parse_hex(value, None), rgb.parse_hex(value), f"{name}: {value}")


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.palette = rgb.load_palette()

    def test_every_mode_returns_one_color_per_led(self):
        for mode in layout.RGB_MODES:
            colors = rgb.effect_colors(mode, 1.0, self.palette, "#89b4fa", 100, profile="sunset")
            self.assertEqual(len(colors), len(layout.LEDS), mode)
            for color in colors:
                self.assertEqual(len(color), 3, mode)
                self.assertTrue(all(0 <= c <= 255 for c in color), mode)

    def test_off_is_black(self):
        self.assertTrue(all(c == (0, 0, 0) for c in rgb.effect_colors("off", 0, self.palette, "#fff", 100)))

    def test_brightness_changes_output(self):
        bright = rgb.effect_colors("solid", 0, self.palette, "#808080", 100)
        dim = rgb.effect_colors("solid", 0, self.palette, "#808080", 50)
        self.assertGreater(sum(map(sum, bright)), sum(map(sum, dim)))

    def test_theme_mode_uses_palette_categories(self):
        self.assertEqual(rgb.theme_color_for("Left Shift", self.palette), self.palette["accent"])
        self.assertEqual(rgb.theme_color_for("Enter", self.palette), self.palette["highlight"])
        # Letters and punctuation are muted; everything else takes the
        # selection tint.
        self.assertEqual(rgb.theme_color_for("A", self.palette), self.palette["muted"])
        self.assertEqual(rgb.theme_color_for("/", self.palette), self.palette["muted"])
        self.assertEqual(rgb.theme_color_for("Num Lock", self.palette), self.palette["selection"])

    def test_key_overrides_apply_by_position(self):
        colors = rgb.effect_colors("off", 0, self.palette, "#fff", 100)
        out = rgb.apply_key_overrides(colors, {"A": "#ff0000", "Nope": "#00ff00"})
        self.assertEqual(out[layout.LEDS.index("A")], (255, 0, 0))
        self.assertEqual(len(out), len(colors))

    def test_overrides_ignore_invalid_hex(self):
        colors = rgb.effect_colors("off", 0, self.palette, "#fff", 100)
        out = rgb.apply_key_overrides(colors, {"A": "not-a-color"})
        self.assertEqual(out[layout.LEDS.index("A")], (0, 0, 0))

    def test_reactive_ages_brighten_then_fade(self):
        fresh = rgb.effect_colors("reactive", 0, self.palette, "#fff", 100, reactive_keys={"A": 0.0})
        old = rgb.effect_colors("reactive", 0, self.palette, "#fff", 100, reactive_keys={"A": 0.9})
        self.assertNotEqual(fresh[layout.LEDS.index("A")], old[layout.LEDS.index("A")])


class LayoutTests(unittest.TestCase):
    def test_every_led_has_coordinates(self):
        self.assertEqual(set(layout.XY), set(layout.LEDS))

    def test_keycodes_point_at_real_leds(self):
        for code, name in layout.KEYCODE_TO_LED.items():
            self.assertIn(name, layout.LEDS, f"keycode {code}")

    def test_mode_lists_are_consistent(self):
        self.assertIn("gradient", layout.RGB_MODES)
        self.assertIn("clear", layout.OLED_PAGES)
        self.assertIn("volume", layout.WHEEL_MODES)
        self.assertEqual(len(set(layout.LEDS)), len(layout.LEDS))

    def test_sentinel_does_not_shift_effects(self):
        self.assertEqual(layout.MAX_X, 20.0)
        self.assertEqual(layout.XY["Num Lock"], (20.0, 3.0))


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "apex", "config.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_when_missing(self):
        cfg = config.load(self.path)
        self.assertEqual(cfg["rgb"]["mode"], "theme")
        self.assertTrue(cfg["wheel"]["grab_pointer"])

    def test_merge_is_deep_and_keeps_defaults(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"rgb": {"mode": "wave"}}, fh)
        cfg = config.load(self.path)
        self.assertEqual(cfg["rgb"]["mode"], "wave")
        self.assertEqual(cfg["rgb"]["brightness"], config.DEFAULT["rgb"]["brightness"])
        self.assertEqual(cfg["oled"]["page"], "clock")

    def test_values_are_clamped(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"rgb": {"brightness": 500, "speed": -4}}, fh)
        cfg = config.load(self.path)
        self.assertEqual(cfg["rgb"]["brightness"], 100)
        self.assertEqual(cfg["rgb"]["speed"], 1)

    def test_corrupt_file_falls_back(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertEqual(config.load(self.path)["rgb"]["mode"], "theme")

    def test_roundtrip_is_atomic(self):
        cfg = config.load(self.path)
        cfg["rgb"]["mode"] = "rainbow"
        config.save(cfg, self.path)
        self.assertEqual(config.load(self.path)["rgb"]["mode"], "rainbow")
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_legacy_config_is_migrated_once(self):
        legacy = os.path.join(self.tmp.name, "apex.json")
        with open(legacy, "w", encoding="utf-8") as fh:
            json.dump({"oled": {"page": "logo"}, "rgb": {"brightness": 55}}, fh)
        with mock.patch.object(config, "LEGACY_CONFIG_PATH", legacy):
            config.migrate(self.path)
        self.assertTrue(os.path.exists(self.path))
        self.assertFalse(os.path.exists(legacy))
        self.assertEqual(config.load(self.path)["oled"]["page"], "logo")

    def test_socket_is_namespaced(self):
        self.assertTrue(config.SOCKET_PATH.endswith("sonic-apex.sock"))


class WheelTests(unittest.TestCase):
    def _ev(self, etype, code, value):
        return (etype, code, value)

    def test_relative_wheel(self):
        rel, key, clicked = wheel.decode_wheel([self._ev(wheel.EV_REL, wheel.REL_WHEEL, 2)])
        self.assertEqual((rel, key, clicked), (2, 0, False))

    def test_invert_flips_both_sources(self):
        rel, key, _ = wheel.decode_wheel(
            [self._ev(wheel.EV_REL, wheel.REL_WHEEL, 1),
             self._ev(wheel.EV_KEY, wheel.KEY_VOLUMEUP, 1)],
            invert=True,
        )
        self.assertEqual((rel, key), (-1, -1))

    def test_media_keys_become_steps(self):
        rel, key, _ = wheel.decode_wheel(
            [self._ev(wheel.EV_KEY, wheel.KEY_VOLUMEDOWN, 1),
             self._ev(wheel.EV_KEY, wheel.KEY_VOLUMEDOWN, 0)]
        )
        self.assertEqual((rel, key), (0, -1))

    def test_click_sources(self):
        self.assertTrue(wheel.decode_wheel([self._ev(wheel.EV_KEY, wheel.KEY_MUTE, 1)])[2])
        self.assertTrue(wheel.decode_wheel([self._ev(wheel.EV_KEY, wheel.BTN_MIDDLE, 1)])[2])

    def test_pointer_button_only_when_allowed(self):
        events = [self._ev(wheel.EV_KEY, wheel.BTN_LEFT, 1)]
        self.assertFalse(wheel.decode_wheel(events)[2])
        self.assertTrue(wheel.decode_wheel(events, allow_pointer_buttons=True)[2])

    def test_hires_remainder_carries_over(self):
        decoder = wheel.WheelDecoder()
        # 100 + 100 hi-res units are two notches total, never dropped.
        self.assertEqual(decoder.feed([self._ev(wheel.EV_REL, wheel.REL_WHEEL_HI_RES, 100)])[0], 0)
        self.assertEqual(decoder.feed([self._ev(wheel.EV_REL, wheel.REL_WHEEL_HI_RES, 100)])[0], 1)
        self.assertEqual(decoder.feed([self._ev(wheel.EV_REL, wheel.REL_WHEEL_HI_RES, 20)])[0], 0)

    def test_hires_negative_direction(self):
        decoder = wheel.WheelDecoder()
        self.assertEqual(decoder.feed([self._ev(wheel.EV_REL, wheel.REL_WHEEL_HI_RES, -240)])[0], -2)

    def test_low_res_and_hires_are_not_double_counted(self):
        decoder = wheel.WheelDecoder()
        rel, _, _ = decoder.feed([
            self._ev(wheel.EV_REL, wheel.REL_WHEEL, 1),
            self._ev(wheel.EV_REL, wheel.REL_WHEEL_HI_RES, 120),
        ])
        self.assertEqual(rel, 2)

    def test_read_raises_device_gone_on_eof(self):
        dev = wheel.Evdev.__new__(wheel.Evdev)
        dev.path = "/dev/input/eventX"
        dev.fd = 0
        dev.grabbed = False
        with mock.patch.object(wheel.os, "read", return_value=b""):
            with self.assertRaises(wheel.DeviceGone):
                dev.read()

    def test_read_raises_device_gone_on_oserror(self):
        dev = wheel.Evdev.__new__(wheel.Evdev)
        dev.path = "/dev/input/eventX"
        dev.fd = 0
        dev.grabbed = False
        with mock.patch.object(wheel.os, "read", side_effect=OSError(19, "No such device")):
            with self.assertRaises(wheel.DeviceGone):
                dev.read()

    def test_read_swallows_eagain(self):
        dev = wheel.Evdev.__new__(wheel.Evdev)
        dev.path = "/dev/input/eventX"
        dev.fd = 0
        dev.grabbed = False
        with mock.patch.object(wheel.os, "read", side_effect=BlockingIOError):
            self.assertEqual(dev.read(), [])

    def test_node_roles(self):
        names = {
            "/dev/input/event1": "SteelSeries SteelSeries Apex 7 TKL",
            "/dev/input/event2": "SteelSeries SteelSeries Apex 7 TKL Consumer Control",
            "/dev/input/event3": "SteelSeries SteelSeries Apex 7 TKL Mouse",
            "/dev/input/event4": "Logitech MX Vertical",
        }
        with mock.patch.object(wheel.glob, "glob", return_value=sorted(names)), \
             mock.patch.object(wheel, "_device_name", side_effect=lambda p: names[p]):
            nodes = wheel.apex_event_nodes()
        self.assertEqual(nodes["keys"], ["/dev/input/event1"])
        self.assertEqual(nodes["wheel"], ["/dev/input/event2"])
        self.assertEqual(nodes["pointer"], ["/dev/input/event3"])


class OledTests(unittest.TestCase):
    def test_report_shape(self):
        from PIL import Image

        report = oled.image_to_report(Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 0))
        self.assertEqual(len(report), 1 + 640 + 1)
        self.assertEqual(report[0], oled.OLED_REPORT_ID)
        self.assertEqual(report[-1], 0x00)

    def test_bits_are_msb_first(self):
        from PIL import Image

        im = Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 0)
        im.putpixel((0, 0), 255)
        self.assertEqual(oled.image_to_report(im)[1], 0x80)
        im = Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 0)
        im.putpixel((1, 0), 255)
        self.assertEqual(oled.image_to_report(im)[1], 0x40)
        im = Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 0)
        im.putpixel((7, 0), 255)
        self.assertEqual(oled.image_to_report(im)[1], 0x01)

    def test_threshold_at_127(self):
        from PIL import Image

        im = Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 127)
        self.assertEqual(oled.image_to_report(im)[1], 0x00)
        im = Image.new("L", (oled.OLED_WIDTH, oled.OLED_HEIGHT), 128)
        self.assertEqual(oled.image_to_report(im)[1], 0xFF)

    def test_resize_from_arbitrary_size(self):
        from PIL import Image

        report = oled.image_to_report(Image.new("L", (400, 90), 255))
        self.assertEqual(len(report), 642)

    def test_ioctl_size_encodes_length(self):
        expected = (3 << 30) | (642 << 16) | (0x48 << 8) | 0x06
        self.assertEqual(oled.hidios_feature(642), expected)
        self.assertEqual(oled.hidios_feature(642) & 0xFFFF, 0x4806)

    def test_missing_device_message(self):
        with mock.patch.object(oled, "find_oled_hidraw", return_value=None), \
             mock.patch.object(oled, "_cached_path", None), \
             mock.patch.object(oled, "_fd", None):
            with self.assertRaises(FileNotFoundError) as ctx:
                oled.send_report(b"\x61")
        self.assertIn("hidraw", str(ctx.exception))


class RenderTests(unittest.TestCase):
    def test_all_pages_render_at_oled_size(self):
        for page in layout.OLED_PAGES:
            frame = render.render(page, {"t": 12.0, "text": "hello", "title": "Track", "artist": "Artist",
                                         "workspace": "2", "window": "term", "playing": True})
            self.assertEqual(frame.size, (oled.OLED_WIDTH, oled.OLED_HEIGHT), page)
            self.assertEqual(frame.mode, "L", page)

    def test_text_page_scrolls(self):
        short = render.text_page("hi", t=0)
        long = render.text_page("x" * 60, t=0)
        self.assertNotEqual(short.tobytes(), long.tobytes())

    def test_image_page_missing_file(self):
        frame = render.image_page("/nonexistent/logo.png")
        self.assertEqual(frame.size, (oled.OLED_WIDTH, oled.OLED_HEIGHT))

    def test_image_cache_invalidates_on_mtime(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "logo.png")
            Image.new("L", (32, 32), 0).save(path)
            first = render.image_page(path).tobytes()
            Image.new("L", (32, 32), 255).save(path)
            os.utime(path, (0, 0))
            render._IMAGE_CACHE["key"] = ("stale",)
            self.assertNotEqual(first, render.image_page(path).tobytes())


class SocketLifecycleTests(unittest.TestCase):
    """The socket file can be removed by plugin reloads or a stale instance."""

    def setUp(self):
        from apex import daemon

        self.mod = daemon
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "apex.sock")
        self.patch = mock.patch.object(daemon.cfgmod, "SOCKET_PATH", self.path)
        self.patch.start()
        with mock.patch.object(daemon.cfgmod, "load", return_value=config._merge(config.DEFAULT, {})):
            self.d = daemon.Daemon()

    def tearDown(self):
        self.d.shutdown()
        self.patch.stop()
        self.tmp.cleanup()

    def test_refuses_to_replace_a_live_socket(self):
        other = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        other.bind(self.path)
        other.listen(1)
        try:
            with self.assertRaises(SystemExit) as ctx:
                self.d._listen()
            self.assertEqual(ctx.exception.code, 0)
        finally:
            other.close()

    def test_replaces_a_stale_socket(self):
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(self.path)
        stale.close()  # socket file remains, nobody listening
        self.assertTrue(os.path.exists(self.path))
        self.d._listen()
        self.assertIsNotNone(self.d.server)
        self.assertTrue(os.path.exists(self.path))

    def test_rebinds_when_the_socket_file_disappears(self):
        self.d._listen()
        os.unlink(self.path)
        self.d._check_socket()
        self.assertTrue(os.path.exists(self.path))

    def test_rebind_accepts_connections(self):
        self.d._listen()
        os.unlink(self.path)
        self.d._check_socket()
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(2)
            client.connect(self.path)  # the loop is not running here; connect is enough
        finally:
            client.close()


class DaemonTests(unittest.TestCase):
    def setUp(self):
        from apex import daemon

        self.mod = daemon
        with mock.patch.object(daemon.cfgmod, "load", return_value=config._merge(config.DEFAULT, {})):
            self.d = daemon.Daemon()

    def tearDown(self):
        self.d.shutdown()

    def test_status_shape_without_hardware(self):
        self.d.openrgb = None
        data = self.d.status()
        self.assertTrue(data["ok"])
        self.assertIn("rgb", data)
        self.assertIn("wheel", data)
        self.assertFalse(data["openrgb"])

    def test_unknown_command(self):
        self.assertFalse(self.d.handle({"cmd": "nope"})["ok"])

    def test_rgb_rejects_unknown_mode(self):
        reply = self.d.handle({"cmd": "rgb", "mode": "disco"})
        self.assertFalse(reply["ok"])

    def test_oled_rejects_unknown_page(self):
        reply = self.d.handle({"cmd": "oled", "page": "nope"})
        self.assertFalse(reply["ok"])

    def test_wheel_rejects_unknown_mode(self):
        reply = self.d.handle({"cmd": "wheel", "mode": "nope"})
        self.assertFalse(reply["ok"])

    def test_rgb_clamps_and_persists(self):
        calls = []
        with mock.patch.object(self.mod.cfgmod, "save", side_effect=lambda cfg: calls.append(cfg)), \
             mock.patch.object(self.d, "_push_rgb"):
            self.d.handle({"cmd": "rgb", "brightness": 500, "speed": 0})
        self.assertEqual(self.d.cfg["rgb"]["brightness"], 100)
        self.assertEqual(self.d.cfg["rgb"]["speed"], 1)
        self.assertTrue(calls)

    def test_cycle_oled_wraps(self):
        self.d.cfg["oled"]["page"] = "clock"
        pages = self.d.cfg["oled"]["pages"]
        for _ in range(len(pages)):
            self.d._cycle_oled(1)
        self.assertEqual(self.d.cfg["oled"]["page"], "clock")

    def test_cycle_rgb_skips_off_and_wraps(self):
        modes = [m for m in layout.RGB_MODES if m != "off"]
        self.d.cfg["rgb"]["mode"] = modes[-1]
        self.d._cycle_rgb(1)
        self.assertEqual(self.d.cfg["rgb"]["mode"], modes[0])
        self.d.cfg["rgb"]["mode"] = modes[0]
        self.d._cycle_rgb(-1)
        self.assertEqual(self.d.cfg["rgb"]["mode"], modes[-1])

    def test_wheel_steps_are_batched(self):
        with mock.patch.object(self.mod, "_run") as run:
            self.d._wheel_steps("volume", 3)
        run.assert_called_once()
        self.assertEqual(run.call_args[0][0][-1], "+3")

    def test_wheel_steps_negative(self):
        with mock.patch.object(self.mod, "_run") as run:
            self.d._wheel_steps("volume", -2)
        self.assertEqual(run.call_args[0][0][-1], "-2")

    def test_workspace_dispatch_is_one_call(self):
        with mock.patch.object(self.mod.hypr, "dispatch") as dispatch:
            self.d._wheel_steps("workspace", 3)
        dispatch.assert_called_once_with("workspace e+3")

    def test_pointer_grab_follows_config(self):
        devs = [mock.Mock() for _ in range(2)]
        self.d.wheel_devs = devs[:1]
        self.d.pointer_devs = devs[1:]
        self.d.cfg["wheel"]["mode"] = "workspace"
        self.d.cfg["wheel"]["grab_pointer"] = False
        self.d._apply_wheel_grab()
        devs[0].set_grab.assert_called_with(True)
        devs[1].set_grab.assert_called_with(False)

    def test_pointer_grab_disabled_in_volume_mode(self):
        dev = mock.Mock()
        self.d.pointer_devs = [dev]
        self.d.wheel_devs = []
        self.d.cfg["wheel"]["mode"] = "volume"
        self.d._apply_wheel_grab()
        dev.set_grab.assert_called_with(False)

    def test_reply_handles_partial_writes(self):
        a, b = socket.socketpair()
        try:
            a.setblocking(False)
            b.setblocking(False)
            payload = {"ok": True, "data": "x" * 4000}
            self.d._reply(a, payload)
            data = b""
            while not data.endswith(b"\n"):
                data += b.recv(65536)
            self.assertEqual(json.loads(data), payload)
        finally:
            a.close()
            b.close()

    def test_oversized_request_drops_client(self):
        a, b = socket.socketpair()
        try:
            a.setblocking(False)
            self.d.clients.append(a)
            self.d.buf[a] = b"x" * (self.mod.MAX_CLIENT_BUFFER + 1)
            self.d._on_client(a)
            self.assertNotIn(a, self.d.clients)
        finally:
            a.close()
            b.close()

    def test_invalid_json_gets_error(self):
        a, b = socket.socketpair()
        try:
            a.setblocking(False)
            b.setblocking(False)
            self.d.clients.append(a)
            self.d.buf[a] = b""
            b.sendall(b"not json\n")
            self.d._on_client(a)
            reply = json.loads(b.recv(4096))
            self.assertFalse(reply["ok"])
        finally:
            a.close()
            b.close()

    def test_static_rgb_frames_are_not_resent(self):
        client = mock.Mock()
        client.device = (0, "SteelSeries Apex 7 TKL")
        self.d.openrgb = client
        self.d.cfg["rgb"]["mode"] = "solid"
        with mock.patch.object(self.mod.rgbmod, "effect_colors",
                               return_value=[(1, 2, 3)] * len(layout.LEDS)):
            self.d._push_rgb(force=True)
            self.d._push_rgb()
            self.d._push_rgb()
        self.assertEqual(client.set_colors.call_count, 1)

    def test_dropped_connection_is_retried_later(self):
        self.d.openrgb = None
        self.d.rgb_retry_at = float("inf")
        self.d.cfg["rgb"]["mode"] = "solid"
        self.d._push_rgb()
        self.assertIsNone(self.d.openrgb)

    def test_static_mode_skips_recomputation(self):
        client = mock.Mock()
        client.device = (0, "SteelSeries Apex 7 TKL")
        self.d.openrgb = client
        self.d.cfg["rgb"]["mode"] = "theme"
        self.d.last_colors = ((1, 2, 3),) * len(layout.LEDS)
        with mock.patch.object(self.mod.rgbmod, "effect_colors") as effect:
            self.d._push_rgb()
            self.d._push_rgb()
        effect.assert_not_called()
        client.set_colors.assert_not_called()

    def test_animated_mode_recomputes_every_frame(self):
        client = mock.Mock()
        client.device = (0, "SteelSeries Apex 7 TKL")
        self.d.openrgb = client
        self.d.cfg["rgb"]["mode"] = "wave"
        self.d.last_colors = ((0, 0, 0),) * len(layout.LEDS)
        with mock.patch.object(self.mod.rgbmod, "effect_colors",
                               return_value=[(9, 9, 9)] * len(layout.LEDS)) as effect:
            self.d._push_rgb()
            self.d._push_rgb()
        self.assertEqual(effect.call_count, 2)

    def test_reactive_keypress_wakes_static_mode(self):
        client = mock.Mock()
        client.device = (0, "SteelSeries Apex 7 TKL")
        self.d.openrgb = client
        self.d.cfg["rgb"]["mode"] = "theme"
        self.d.last_colors = ((1, 2, 3),) * len(layout.LEDS)
        self.d.reactive = {"A": __import__("time").monotonic()}
        with mock.patch.object(self.mod.rgbmod, "effect_colors",
                               return_value=[(5, 5, 5)] * len(layout.LEDS)) as effect:
            self.d._push_rgb()
        self.assertEqual(effect.call_count, 1)


class CliTests(unittest.TestCase):
    def test_modes_json_matches_layout(self):
        from apex import cli

        out = io.StringIO()
        with mock.patch.object(sys, "stdout", out):
            cli.cmd_modes(None)
        data = json.loads(out.getvalue())
        self.assertEqual(data["rgbModes"], list(layout.RGB_MODES))
        self.assertEqual(data["oledPages"], list(layout.OLED_PAGES))
        self.assertEqual(data["profiles"], list(rgb.PROFILES))

    def test_local_rgb_reports_openrgb_failure_cleanly(self):
        from apex import cli

        cfg = config._merge(config.DEFAULT, {})
        with mock.patch.object(rgb, "OpenRGB", side_effect=ConnectionRefusedError(111, "refused")):
            with self.assertRaises(SystemExit) as ctx:
                cli._run_local(cli._local_rgb, {"mode": "wave"})
        self.assertIn("OpenRGB", str(ctx.exception))
        self.assertIsNotNone(cfg)

    def test_local_rgb_clamps_values(self):
        from apex import cli

        cfg = config._merge(config.DEFAULT, {})
        client = mock.Mock()
        client.device = (0, "SteelSeries Apex 7 TKL")
        with mock.patch.object(rgb, "OpenRGB", return_value=client), \
             mock.patch.object(cli.cfgmod, "save"):
            with mock.patch("sys.stdout", io.StringIO()):
                cli._local_rgb(cfg, {"brightness": 900, "speed": 0})
        self.assertEqual(cfg["rgb"]["brightness"], 100)
        self.assertEqual(cfg["rgb"]["speed"], 1)
        client.set_colors.assert_called_once()

    def test_bad_key_override_is_rejected(self):
        from apex import cli

        args = cli.build_parser().parse_args(["rgb", "-k", "Nope=#ffffff"])
        with self.assertRaises(SystemExit):
            cli.cmd_rgb(args)


if __name__ == "__main__":
    unittest.main()
