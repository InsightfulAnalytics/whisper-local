# Distribution Guide

How Whisper Local gets into users' hands, and how to ship a new release.
Written for someone new to this — every step is spelled out.

There are three distribution channels, in order of how many people they reach:

1. **Standalone `.exe`** (Windows, no Python needed) — built automatically in CI.
2. **PyPI** (`pip install whisper-local`) — built automatically in CI.
3. **Package managers** (winget on Windows, Homebrew on macOS) — manual, after a release.

---

## The one command that does almost everything

Releases are driven by **git tags**. When you push a tag like `v0.10.1`, GitHub
Actions (`.github/workflows/release.yml`) automatically:

1. Runs the test suite.
2. Builds the Python wheel + sdist.
3. Builds `whisper-local.exe` (standalone Windows app) from that wheel.
4. Publishes the wheel to PyPI *(once you've done the one-time PyPI setup below)*.
5. Creates a **GitHub Release** with the `.exe`, its `.sha256`, the wheel, and
   auto-generated release notes.

So the release flow is just:

```bash
# 1. Bump the version in BOTH pyproject.toml and CITATION.cff (a test enforces they match)
# 2. Update CHANGELOG.md (move [Unreleased] items under the new version)
# 3. Commit, then tag and push:
git commit -am "release: v0.10.1"
git tag v0.10.1
git push origin master --tags
```

Watch it run at `https://github.com/drajb/whisper-local/actions`.

> Tip: there's a `/bump` skill in this repo that automates the version bump + tag + push.

---

## One-time setup: PyPI Trusted Publishing

The `publish-pypi` job uses PyPI's "trusted publishing" (no API tokens to leak).
You do this **once**:

1. Create an account at <https://pypi.org>.
2. Go to <https://pypi.org/manage/account/publishing/> → **Add a pending publisher**:
   - PyPI project name: `whisper-local`
   - Owner: `drajb`
   - Repository: `whisper-local`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
3. In GitHub: repo **Settings → Environments → New environment** named `pypi`.

That's it. The next tag push publishes to PyPI automatically.

> The `.exe` build does **not** depend on this — it embeds the local wheel, so
> standalone builds work even before PyPI is set up.

---

## Channel 1 — Standalone `.exe` (automatic)

Nothing to do: every release attaches `whisper-local.exe`. Users download and
double-click it. Under the hood it's [pyapp](https://ofek.dev/pyapp): a tiny Rust
launcher that, on first run, downloads a private CPython and pip-installs the
embedded wheel. First launch is slow (it's bootstrapping); subsequent launches
are instant.

**Local build (optional, for testing or a custom icon):**
The `pyapp-build/` folder has a PowerShell script that builds locally and can
embed the app icon (CI skips the icon for simplicity). See `pyapp-build/CLAUDE.md`.

```powershell
cd pyapp-build
./setup-build-env.ps1 -UseLocalWheel   # downloads Rust + pyapp, builds a wheel
./build-pyapp.ps1                       # produces dist/whisper-local.exe
```

**Code signing (future):** the `.exe` is unsigned, so Windows SmartScreen will
warn on first run ("More info → Run anyway"). Signing needs a paid certificate;
it's noted here as a future polish item, not a blocker.

---

## Channel 2 — PyPI (automatic)

Once trusted publishing is set up, every tag publishes. Users then:

```bash
pip install whisper-local      # or: pip install 'whisper-local[whispercpp]' for the cpp backend
```

To test a release on TestPyPI first, see `docs/publishing-to-pypi.md`.

---

## Channel 3a — winget (Windows package manager)

After a release exists (so the `.exe` URL and its SHA256 are live):

1. Install the helper: `winget install wingetcreate`.
2. Run:
   ```
   wingetcreate new https://github.com/drajb/whisper-local/releases/download/v0.10.1/whisper-local.exe
   ```
   It will prompt for metadata and auto-compute the SHA256. Use
   `PackageIdentifier: drajb.WhisperLocal`, installer type `portable`.
3. It opens a PR against [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).
   Once merged, users can `winget install drajb.WhisperLocal`.

A reference manifest is in `packaging/winget/whisper-local.installer.yaml`
(the SHA256 there is a placeholder — `wingetcreate` fills the real one in).

---

## Channel 3b — Homebrew (macOS package manager)

Whisper Local's dependency tree is too heavy to vendor for homebrew-core, so use
a **personal tap** (your own mini Homebrew repo):

1. Create a public GitHub repo named `homebrew-tap` under your account.
2. Copy `packaging/homebrew/whisper-local.rb` into it as `Formula/whisper-local.rb`.
3. Fill in `<VERSION>` and `<SDIST_SHA256>` (get the sha with
   `curl -sL <pypi-sdist-url> | shasum -a 256`).
4. Commit + push. Users then:
   ```bash
   brew tap drajb/tap
   brew install whisper-local
   ```

The formula installs the PyPI package into an isolated virtualenv so it never
touches the user's system Python.

---

## Release checklist (copy/paste)

```
[ ] Version bumped in pyproject.toml AND CITATION.cff (must match — test enforces it)
[ ] CHANGELOG.md updated (move [Unreleased] → new version with date)
[ ] Smoke tests green locally: python -m unittest tests.test_smoke
[ ] git tag vX.Y.Z && git push origin master --tags
[ ] Actions run is green (test → build → build-exe → publish-pypi → github-release)
[ ] GitHub Release has whisper-local.exe + .sha256 + wheel
[ ] (optional) winget: wingetcreate update / new
[ ] (optional) homebrew: bump Formula/whisper-local.rb in the tap
```

---

## Reach, honestly ranked

- **PyPI** — zero extra effort once set up; reaches every Python user.
- **`.exe`** — zero extra effort; reaches non-Python Windows users (the biggest group).
- **winget** — ~15 min per release; great discoverability for Windows power users.
- **Homebrew tap** — ~15 min per release; the expected install path for Mac devs.

Do PyPI + `.exe` first (they're free and automatic). Add winget/Homebrew once the
project has traction and you're tagging releases regularly.
