# Release process

1. Update `version` in `manifest.json` **and** `bin/apex/__init__.py`
   (CI enforces that they agree, and `release.yml` enforces that the tag
   matches them).
2. Run `./tests/run` and `omarchy plugin validate .` on a real Omarchy host;
   record results and the installed `omarchy-version` in docs/ACCEPTANCE.json.
3. Verify the documented install command actually works on a clean clone:

   ```bash
   omarchy plugin add https://github.com/davidzu/sonic.apex.git --enable
   ```

4. Tag and push (`v1.2.0`). The release workflow runs the checks, builds a
   tarball of the installable payload, and publishes the GitHub release with
   generated notes; edit those notes to describe what changed for the user.
5. Confirm the release assets and that `docs/ACCEPTANCE.json` matches what was
   actually tested.
