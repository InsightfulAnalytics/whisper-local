Builds `whisper-local.exe` using [pyapp](https://github.com/ofek/pyapp) (Rust wrapper that bootstraps Python + pip install at first launch).

## One-time setup

```powershell
powershell.exe -ExecutionPolicy Bypass -File pyapp-build\setup-build-env.ps1
```

The setup script:
- Checks for Rust (offers to install via rustup if missing — one-time ~600 MB)
- Downloads + extracts the latest pyapp source to `pyapp-build\pyapp-source\`
- Creates `pyapp-build\build-config.json` from defaults

Re-open the terminal after installing Rust so `cargo` lands on PATH.

## Build

```powershell
powershell.exe -ExecutionPolicy Bypass -File pyapp-build\build-pyapp.ps1
```

`-Clean` flag forces full Rust rebuild.

Produces two executables in `dist\`:
- `whisper-local.exe` — console (visible terminal)
- `whisper-local-hideable.exe` — GUI subsystem (for `console.start_hidden`/minimize-to-tray)

## How it works

At first launch, `whisper-local.exe` runs the embedded pyapp logic:
1. Creates a private venv under `%LOCALAPPDATA%\pyapp\data\whisper-local\<hash>\<version>\`
2. Runs `pip install whisper-local==<your version>` into that venv
3. Spawns the actual Python entry point from that venv

So the user never needs Python installed system-wide. They just double-click the exe.

## Two distribution flows

**A. CI release build (what users get):** `.github/workflows/release.yml` builds
the wheel and embeds it via `PYAPP_PROJECT_PATH` — the exe is fully
self-contained and never touches PyPI. This is the only flow that ships.

**B. Bundled local wheel (for local test builds):**
- Run setup with `-UseLocalWheel`: `setup-build-env.ps1 -UseLocalWheel`
- It builds a local wheel and prints the `PYAPP_PROJECT_PATH` env var to set
- Run build-pyapp.ps1 with that env var set
- The resulting exe contains the wheel — works without PyPI

> ⚠️ Don't build with bare `PYAPP_PROJECT_NAME` (no `PYAPP_PROJECT_PATH`): that
> makes the exe `pip install whisper-local` from PyPI at first launch — and the
> PyPI name belongs to the upstream fork parent, so users would get the wrong
> build. Always embed the wheel.

## Troubleshooting

**`cargo: command not found`**: re-open the terminal after `rustup-init`.

**First launch installs the wrong version / fails**: the exe was built without
an embedded wheel (see warning above) — rebuild with the local-wheel flow.

**Slow first launch (~30s)**: normal — pyapp is downloading deps. Subsequent launches reuse the venv.
