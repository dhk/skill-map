# Publishing a plugin to PyPI

This repo hosts more than one Claude Code plugin under `plugins/`. Each one
that ships a `pipx run <name>`-style installer (see
[`plugins/skill-doctor`](../../plugins/skill-doctor) for the reference
implementation) gets its own PyPI package, published by tag push, using one
shared reusable workflow so the release logic only exists once.

## The pattern

- **`publish-pypi-package.yml`** — reusable (`workflow_call`). Builds the
  package at a given directory with `uv build` and publishes it via
  [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
  (OIDC — no API token stored as a secret).
- **`publish-<plugin>.yml`** — one thin trigger workflow per package. Just a
  tag filter and a `uses:` call into the reusable workflow above.

Tags are prefixed per package (`skill-doctor-vX.Y.Z`, not `vX.Y.Z`) so
multiple packages in this monorepo can cut releases independently without
colliding on tag names.

## Adding pip-publishing to a new plugin

1. **Package it** the way `plugins/skill-doctor` does:
   - `pyproject.toml` with `[project.scripts]` naming the entry point
     *exactly* the PyPI package name, so `pipx run <name>` resolves it
     without `--spec`.
   - Bundle whatever the plugin needs to place on disk (skill Markdown,
     config, etc.) as wheel data via `[tool.hatch.build.targets.wheel.force-include]`
     — the installer should never need `git clone` at runtime.
   - The installer's `main()` should be idempotent and safe to re-run: write
     an ownership marker file so a re-run (i.e. an update) can overwrite its
     own prior install, but refuse to clobber a directory it didn't create
     (see `src/skill_doctor_installer/cli.py`).

2. **Add the trigger workflow** — copy `publish-skill-doctor.yml`, rename it,
   and change two things: the tag prefix and `package-dir`:
   ```yaml
   on:
     push:
       tags:
         - '<plugin>-v*'
   jobs:
     publish:
       uses: ./.github/workflows/publish-pypi-package.yml
       with:
         package-dir: plugins/<plugin>
   ```

3. **Claim the PyPI project name once, by hand.** Trusted Publishing attaches
   to an *existing* PyPI project — it can't create the first release. From
   the package directory: `uv build && uv publish` (or `twine upload
   dist/*`), authenticated with your own PyPI account.

4. **Add a trusted publisher** on the project's PyPI settings page, pointing
   at `dhk/skill-map`, the new workflow's filename, and environment `pypi`.

5. From then on, bump the version (keep it in lockstep across
   `pyproject.toml`, `plugin.json`, and the skill's own frontmatter — see
   `SKILL-DOCTOR.md`'s "Pin a version" section) and push a tag:
   ```bash
   git tag skill-doctor-v1.0.1
   git push origin skill-doctor-v1.0.1
   ```
   The tag push is the entire release process from that point on.

## Verifying before you trust it

The workflow only ever reads `${{ inputs.package-dir }}` and writes to PyPI
via the official `pypa/gh-action-pypi-publish` action — it never touches
GitHub secrets or any other part of the repo. Read
[`publish-pypi-package.yml`](publish-pypi-package.yml) directly; it's ~30
lines.
