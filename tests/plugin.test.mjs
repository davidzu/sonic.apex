import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {root, readJSON} from '../scripts/template.mjs';

test('manifest identity matches project identity', () => {
  const c = readJSON(path.join(root, '.template/project.json'));
  const m = readJSON(path.join(root, 'manifest.json'));
  assert.equal(m.id, c.id);
  assert.equal(m.schemaVersion, 1);
  assert.equal(m.license, 'MIT');
});

test('runtime payloads referenced by the panel exist', () => {
  for (const f of ['bin/apexctl', 'bin/apex/daemon.py', 'bin/apex/cli.py',
                   'hooks/apexctl', 'hooks/apply-keyboard-rgb',
                   'systemd/apexctl.service', 'udev/99-steelseries-apex.rules']) {
    assert.ok(fs.existsSync(path.join(root, f)), `missing ${f}`);
  }
});

test('hooks and cli are executable', () => {
  for (const f of ['bin/apexctl', 'hooks/apexctl', 'hooks/apply-keyboard-rgb']) {
    const st = fs.statSync(path.join(root, f));
    assert.ok(st.mode & 0o111, `${f} is not executable`);
  }
});

test('no runtime payload references stale plugin paths', () => {
  const tree = fs.readdirSync(path.join(root, 'hooks'));
  for (const f of tree) {
    const text = fs.readFileSync(path.join(root, 'hooks', f), 'utf8');
    assert.ok(!/plugins\/[A-Za-z0-9_.-]+\/systemd/.test(text.replace(/sonic\.apex/g, 'SONIC_APEX')), `${f} hardcodes a foreign plugin path`);
  }
});
