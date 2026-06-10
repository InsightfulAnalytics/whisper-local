# Whisper Local — Code Audit & Improvement Backlog

**Last updated:** 2026-06-10
**Audited version:** 0.10.0
**Method:** Four parallel subsystem reviews (core pipeline, UI, utility/feature modules, packaging/docs) + manual verification of the highest-severity findings.

> This is a living document. Each issue has a stable ID (e.g. `SRV-1`) so commits and PRs can reference it. When you fix one, change its **Status** to `FIXED (<commit>)` rather than deleting it, so history stays readable.

---

## How to read this

- **Severity** reflects real-world user/security impact for *this* app (a local, opt-in, privacy-first desktop tool), not raw CVSS. I deliberately down-rated several agent-flagged "critical" items that are only reachable by local processes or require unusual user configuration.
- **Verified** = I read the code and confirmed the issue first-hand. **Reported** = surfaced by a review agent, plausible, not yet hand-verified.
- Line numbers are as of the audit date; they drift as the file changes.

---

## Priority summary

| ID | Severity | Area | One-liner | Status |
|----|----------|------|-----------|--------|
| SRV-1 | High | local_server | `rstrip(b'-')` corrupts binary audio uploads | OPEN (verified) |
| SRV-2 | Medium | local_server | Unbounded `Content-Length` read → local OOM | OPEN (verified) |
| PRIV-1 | High | bundle_logs | Diagnostic zip doesn't redact hotwords / Ollama endpoint / prompts | OPEN (verified) |
| SPAWN-1 | High | startup | Windowless (`pythonw`) launch double-spawns a 2nd instance | OPEN (verified, root cause unknown) |
| VC-1 | Medium | voice_commands | `${clipboard}` expanded before risky-command check; no shell-escaping | OPEN (reported) |
| UI-1 | Medium | history_window | Singleton `_instance` never reset on close | OPEN (verified) |
| LOG-1 | Medium | transcript_log / stats | Concurrent appends + rotation have no lock → rare corruption/loss | OPEN (verified) |
| CI-1 | Medium | CI | Tests run only on Ubuntu; Windows is the primary platform | OPEN (verified) |
| UI-2 | Low | dictionary | Add-word dialog leaks a daemon thread + Tk root per open | OPEN (reported) |
| UI-3 | Low | settings_ui | Search filter re-packs rows with hardcoded geometry | OPEN (verified) |
| REC-1 | Low | audio_recorder | `is_recording` read/written across threads without lock | OPEN (verified) |
| VAD-1 | Low | vad | One short-lived thread spawned per VAD event | OPEN (reported) |
| DOC-1 | Low | docs | `project-index.md` missing ~10 newer modules | OPEN (verified) |
| DOC-2 | Low | CITATION.cff | Version says 0.9.0, project is 0.10.0 | OPEN (verified) |
| DOC-3 | Low | README | "all 40 should pass" — actual count is 53 | OPEN (verified) |

---

## High severity

### SRV-1 — Multipart parser corrupts binary audio `local_server.py:247`
**Verified.** `body = body.rstrip(b'\r\n').rstrip(b'-')` strips *any* trailing `0x2D` ("-") bytes from every field body, including the binary `file` part. Audio whose final bytes are `0x2D` get silently truncated, so the OpenAI-compatible `--serve` endpoint can mis-transcribe or fail on otherwise valid uploads. The `rstrip(b'-')` was presumably meant to handle the closing `--` boundary, but `raw.split(sep)` already separates parts — the trailing-boundary dashes live in their own trailing chunk, not in a field body.
**Fix:** drop `.rstrip(b'-')`; keep only `.rstrip(b'\r\n')`. Add a regression test that round-trips a WAV ending in `0x2D` through `_parse_multipart` + `_decode_audio`.

### PRIV-1 — Diagnostic bundle leaks config secrets `bundle_logs.py:_redact / ~line 71`
**Verified.** `_redact()` only masks usernames in paths and email addresses. The bundle includes `user_settings.yaml` verbatim otherwise, which can contain: `whisper.hotwords` (people put names, codewords, sometimes secrets here), `postprocess.ollama.endpoint` (may embed `user:pass@host` or `?token=`), custom model paths, and `initial_prompt`. Bundles are explicitly meant to be attached to public GitHub issues, so this is a real privacy-first-tool regression.
**Fix:** add redaction rules for `hotwords:`, `endpoint:`, `initial_prompt:` (and consider an allowlist approach — only bundle known-safe keys). Mention in the bundle's `about.txt` exactly which fields were scrubbed.

### SPAWN-1 — Windowless launch double-spawns a second instance (startup)
**Verified during this session.** Launching via `pythonw.exe whisper-local.py` *or* `pythonw.exe -m whisper_key.main` reliably produces two processes: the launched one (parent) spawns a child running the same entrypoint under the **system** Python (`...\Programs\Python\Python312\pythonw.exe`), and the child takes the lock. The canonical `whisper-local.cmd` (console, system python) does **not** reproduce it — exactly one instance. Root cause **not yet identified**: it is not the `.py` file association (reproduces with `-m`), not `instance_manager` (it only SIGTERMs + locks, never spawns), and not `multiprocessing` (that would use the venv `sys.executable`, but the child is system python). Something resolves an interpreter via PATH/registry and re-execs only under the no-console condition.
**Impact:** two instances briefly (or persistently) contend for global hotkeys → "hotkey already registered" + double-trigger. Only affects windowless autostart; the shipped `.cmd` launcher is safe.
**Next step:** instrument startup — log `sys.executable`, `sys.argv`, `os.getpid()`, parent pid at the very top of `main()`; reproduce under `pythonw`; bisect by disabling subsystems (tray, sherpa-onnx streaming, ten-vad, playsound3) to find which import/init re-execs. Suspect a dependency calling `freeze_support()`/relaunch or a console-acquisition shim.

---

## Medium severity

### SRV-2 — Unbounded request body read `local_server.py:222-223`
**Verified.** `length = int(headers['Content-Length']); raw = rfile.read(length)` with no cap. A local process (the server binds loopback only, so not remote) can send a huge `Content-Length` and exhaust memory. Lower severity than a public service, but `--serve` is meant to sit running in the background.
**Fix:** reject `length > MAX_UPLOAD` (e.g. 500 MB) with HTTP 413 before reading.

### VC-1 — Voice-command clipboard expansion precedes safety check `voice_commands.py` (reported, ~line 160 vs 232)
**Reported, not hand-verified.** `${clipboard}` / `${selection}` templates appear to be expanded into the `run:` string before the risky-pattern regex runs, and substitution is raw (no shell-escaping). A user with a `run:` command containing `${clipboard}` who pastes shell metacharacters could slip past the confirm dialog if the regex doesn't match the injected payload. Requires user-authored `run:` command + `shell=True`.
**Fix:** `shlex.quote()` clipboard/selection before substitution; run the risky-pattern check on the final expanded string; consider defaulting `run:` commands to confirm-always.
**Verify first:** confirm the actual expansion/check ordering in the current file before acting.

### UI-1 — History window singleton never cleared `history_window.py:~155`
**Verified.** `_instance` is set on open but there's no `WM_DELETE_WINDOW` handler resetting it to `None` (cheat_sheet.py does this correctly — copy that pattern). After close+reopen, the guard calls `winfo_exists()` on a destroyed root.
**Fix:** add `root.protocol("WM_DELETE_WINDOW", lambda: (_clear_ref(), root.destroy()))` mirroring `cheat_sheet.py`.

### LOG-1 — Transcript/stats writes + rotation unsynchronized `transcript_log.py:~38,73 / stats.py:~49`
**Verified (no lock present).** Append writes and the read-truncate-rewrite rotation share no lock. Back-to-back deliveries (continuous mode, rapid commands) can interleave a line (load silently skips malformed JSON → data loss) or lose entries appended during a rotation window. Low frequency in practice.
**Fix:** module-level `threading.Lock` around both append and rotate.

### CI-1 — No Windows/macOS CI `.github/workflows/test.yml`
**Verified.** `runs-on: ubuntu-latest` only. Windows is the primary platform; platform-specific code (hotkeys, WASAPI host matching, clipboard, permissions) is never exercised in CI.
**Fix:** matrix `[ubuntu-latest, windows-latest, macos-latest]`. The smoke suite already imports cleanly without the heavy ML stack on Linux; verify the same on Windows (it should, given local runs pass).

---

## Low severity

### UI-2 — Add-word dialog thread/root leak `dictionary.py:~182` (reported)
Each `show_add_word_dialog()` spawns a fresh daemon thread + Tk root with no singleton; repeated opens accumulate. Apply the cheat_sheet singleton pattern or ensure clean mainloop exit.

### UI-3 — Settings search re-packs with hardcoded geometry `settings_ui.py:~185-215` (verified)
On filter-show, rows are re-`pack()`ed with literal `padx/pady` instead of their saved `pack_info()`. Works today because all rows share the same geometry; will silently misplace rows if any row's packing ever differs. Cache `pack_info()` before `pack_forget()`.

### REC-1 — `is_recording` cross-thread without lock `audio_recorder.py` (verified)
Read in the audio callback thread, written from main/VAD threads. In CPython a bool assignment is atomic so this is mostly benign today, but the flag gates buffering/VAD and could mis-sequence on a stop/start boundary. Consider a lock or `threading.Event`. Low priority.

### VAD-1 — Thread per VAD event `voice_activity_detection.py:~228` (reported)
A new daemon thread is spawned for each dispatched event. Under rapid state flips this is wasteful; prefer a single dispatcher thread + queue. Verify the actual dispatch code before changing.

### DOC-1 — `project-index.md` stale (verified)
Missing entries for: `selftest`, `local_server`, `bundle_logs`, `cheat_sheet`, `first_run`, `settings_ui`, `history_window`, `transcript_log`, `update_check`, `noise_suppression`, `setup_wizard`, `streaming_manager`, `terminal_ui`. CLAUDE.md @-includes this file, so keeping it current directly improves future automated work.

### DOC-2 — CITATION.cff version drift (verified)
`version: 0.9.0` → should be `0.10.0`. Consider a release checklist (or a `bump` step) that updates pyproject, CITATION.cff, and CHANGELOG together.

### DOC-3 — README test count (verified)
README says "all 40 should pass"; the suite is now **53**. Either drop the number or wire it to reality.

---

## Audited and found CLEAN

Recorded so future audits don't re-tread:

- **State machine** (`state_manager`): `can_start_recording`/`get_current_state` correctly locked; `_transcription_pipeline` resets `is_processing` in `finally`; early-return paths hide/flash the overlay.
- **Hotkey listener**: `keys_armed` correctly prevents double-trigger; PTT vs toggle paths sound.
- **Audio trimming/resampling/preroll**: long-pause + trailing-silence algorithms correct; preroll deque trimmed when idle (no unbounded growth); WASAPI resample-on-stop logic correct.
- **USB disconnect recovery**: retry loop + default-device fallback correct.
- **Whisper engines** (faster-whisper + cpp): kwargs built correctly; model-load errors logged and re-raised.
- **update_check**: opt-in, disabled by default, sends only a version string in the UA header, once/day rate-limited. Privacy claim holds.
- **Privacy pledge overall**: the only network touchpoints are HuggingFace model download (first run), opt-in GPU install, opt-in update check, and user-local Ollama (`localhost`). No undisclosed calls. **Verified by grep across `src/`.**
- **level_overlay**: correct cross-thread pattern (`_call` → `root.after`).
- **system_tray**: launches settings/history/cheat-sheet/doctor as subprocesses — the safest way to avoid multi-Tk-root conflicts.
- **Packaging**: `package-data` includes all five `*.defaults.yaml`, assets, platform assets, and the bundled `portaudio.dll`. Entry points (`whisper-local`, `wl`) correct.
- **README feature/flag claims**: all 21 CLI flags exist; every feature bullet maps to real code; hotkey table matches `config.defaults.yaml`.
- **Utility modules** found clean: `selftest`, `transforms`, `noise_suppression`, `text_postprocess`, `app_rules`, `profiles`, `settings_io`, `vocab_import`, `audit_log`, `doctor`.

---

## Cross-cutting recommendation: the multi-Tk-root architecture

The app can have several `Tk()` roots alive at once, each with its own `mainloop` on its own daemon thread (overlay always-on + any of: first-run, fallback, cheat-sheet, dictionary, history). Tkinter tolerates this *only* as long as the roots never touch each other and each stays on its creating thread. It works today but is fragile. The tray already dodges this by launching the big windows (`--settings`, `--history`) as **subprocesses** — that's the robust pattern. Worth considering: route *all* user-facing windows through the subprocess path, leaving only the always-on overlay as an in-process Tk root. Tracked as an architectural note, not a bug.

---

## Suggested fix order (next session)

1. **PRIV-1** + **SRV-1** — small, self-contained, and they touch the privacy/quality story the project sells. Add tests.
2. **DOC-2 / DOC-3 / DOC-1** — trivial, makes the repo look maintained.
3. **CI-1** — add the OS matrix; catches platform regressions for free thereafter.
4. **UI-1** + **LOG-1** — small correctness fixes with clear patterns to copy.
5. **SRV-2**, **VC-1** — hardening; verify VC-1's code path first.
6. **SPAWN-1** — the interesting one; needs the instrumentation/bisect described above. Only block windowless autostart on it; the `.cmd` launcher ships fine.

## Product ideas (not bugs) — see also README "Why this exists"

- Single-`.exe` distribution (PyInstaller/pyapp is scaffolded) + `winget` / Homebrew manifests — biggest reach unlock.
- Demo GIF in the README (highest single discoverability win; the recorder script exists in `tools/`).
- Real streaming delivery (partial words to cursor) — `streaming_recognizer.py` scaffolding exists but isn't wired to delivery.
- Resolve SPAWN-1 so a clean windowless autostart can be the documented default (no console flash).
