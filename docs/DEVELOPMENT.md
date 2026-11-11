# Develop and test the plugin

Run `./tests/run` from the repository root (requires Node.js 22+ and Python 3
with Pillow; no npm install needed). It runs three layers:

- `scripts/check.mjs` — template structure, links, CI policy
- `node --test` — manifest/payload/version contracts
- `python3 -m unittest discover -s tests` — colour maths, config migration,
  event decoding, OLED framing, daemon request handling

The Python suite needs no hardware: device access is mocked or bypassed.
On the target Omarchy machine run `omarchy plugin validate .` and record the
installed `omarchy-version`.

Portable checks validate a deliberately narrow structural subset; the
installed host's validator is authoritative.

Live checks to perform before releasing:

- horizontal and vertical bar layouts
- disable/re-enable via `omarchy plugin disable|enable sonic.apex`
- shell reload and `omarchy-shell shell rescanPlugins`
- monitor connect/disconnect and theme changes
- `apexctl` daemon start/stop/restart under the user systemd service
- removal: `omarchy plugin remove sonic.apex --yes` must not leave the
  `apexctl` service running or orphaned hooks behind

Use your current Omarchy plugin development/linking workflow or Plugin
Workbench after inspecting its current commands. The included
`.omarchy-workbench.json` proposes checks; it does not grant trust or execute
them automatically.

Before a public release, document the exact verified install command and the
installed host version in README.md and docs/ACCEPTANCE.json.
