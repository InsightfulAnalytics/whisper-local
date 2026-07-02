# Whisper Local — Code Audit & Improvement Backlog

**Last updated:** 2026-06-13
**Audited versions:** 0.10.0 (Round 1, below) and 0.11.x (Round 2, next section)
**Method:** Parallel subsystem reviews + manual verification of every finding before fixing.

> This is a living document. Each issue has a stable ID (e.g. `SRV-1`) so commits and PRs can reference it. When you fix one, change its **Status** to `FIXED (<commit>)` rather than deleting it, so history stays readable.

---

## Round 3 (0.14.x) — security-focused sweep (2026-07)

Agent security sweep + hand-verified. Four confirmed, all fixed with tests.

- **SEC-1 (Med, data loss)** `settings_ui` "Reset to defaults" deleted `user_settings.yaml`,
  wiping `whisper.hotwords` despite the dialog promising the dictionary survives. Now
  preserves hotwords across the reset (`reset_settings_preserving_hotwords`). +test.
- **SEC-2 (Med, privacy)** `bundle_logs` masked the Ollama endpoint only in
  user_settings.yaml, but `doctor.txt` (same public-issue zip) printed it verbatim —
  reopening PRIV-1 for `user:pass@`/`?token=` endpoints. Added URL-credential + secret-
  query-param scrubbing to the general `_redact()` (covers doctor.txt AND logs). +test.
- **SEC-3 (Low)** `--serve` accepted a negative `Content-Length`, bypassing the SRV-2
  cap (`read(-1)` drains the socket). Now rejects `< 0`. +test. Loopback-only.
- **SEC-4 (Low)** `inline_formatting_absorb_punctuation` with the built-in English cue
  words glued words ("hello,world") and ate `new paragraph`/`new line` breaks. Fixed:
  built-in punctuation replacements bake a trailing space; absorb class excludes
  newlines (`[ \t,.]*`). +test.

Everything else re-verified CLEAN (subprocess/shell, full network inventory, YAML
loaders, streaming worker lifecycle, autostart writes, VC-1/SRV-1/PRIV-1/LOG-1/R2 fixes).

---

## Round 2 (0.11.x) — intensive word-by-word review

Six parallel reviewers swept the whole repo; every claimed bug was hand-verified in the
code before fixing (many agent "findings" were over-reported and dropped).

### Fixed (confirmed, with tests where applicable)
- **R2-1 (Med, race)** `audio_recorder.py` — pre-roll `deque` had no lock; `list(deque)`
  during a concurrent callback append could raise `RuntimeError: deque mutated during
  iteration`. Added `_buffer_lock` around append/trim and every snapshot+clear.
- **R2-2 (Med)** `voice_activity_detection.py` — realtime `process_chunk` fed a full chunk
  to TEN VAD, which asserts exactly 256 samples; off-by-a-few chunks from non-48 kHz mics
  silently killed the silence-timeout. Now slices/pads to 256 like the pre-check path.
- **R2-3 (Med)** `settings_ui._coerce` — coerced ALL numeric-looking strings to int/float,
  corrupting free-text settings (`initial_prompt`, hotkeys, ollama model/endpoint). Now
  type-aware (only known numeric paths). +test.
- **R2-4 (Med)** `update_check._is_newer` — `int("0-dev")` threw on source installs,
  permanently disabling update checks; now strips pre-release/build suffix + pads. +test.
- **R2-5 (Low)** `whisper_engine.py` — `old_model_key` could be unbound in the async-load
  error path (UnboundLocalError masking the real error); captured before any callback.
- **R2-6 (Low)** `level_overlay.py` — mode switches stacked multiple self-rescheduling
  `after()` animation loops; now cancels the prior loop first.
- **R2-7 (Low)** `autostart.py` — macOS plist now XML-escaped; `toggle()` returns achieved
  state, not intended.
- **R2-8 (Low)** `platform/windows/console.py` — `show()` did `SW_HIDE` then `SW_RESTORE`
  (copy-paste from `hide()`), causing a flicker; removed the stray hide.
- **R2-9 (Med, config)** `profiles.defaults.yaml` — `dictation`/`notes` pinned `model:tiny`,
  silently downgrading the new `base` default; now `base`. +test.
- **R2-10 (Low)** `utils.beautify_hotkey` no-op `.replace('+','+')` removed.
- **R2-11 (Low, consistency)** `main.py` / `hotkey_listener.py` `recording_mode` code
  fallback was still `toggle`; now `push_to_talk` to match the shipped default.
- **R2-12 (docs)** `faq.md` autostart answer rewritten to the built-in feature;
  `project-index.md` gained the missing module rows; six modules got header comments.

### Deferred (real but intentionally not changed this pass — risk > reward)
- **R2-D1** Transcription runs synchronously on the hotkey/release thread
  (`state_manager.stop_recording` → `_transcription_pipeline`). Moving it to a worker
  thread is a real architecture change (re-entrancy, the `is_processing` guard, cancel
  semantics) and the current design works; left as a deliberate design note.
- **R2-D2** Cross-thread Tk access + singleton spawn race in `history_window` /
  `cheat_sheet` / `dictionary` (caller thread calls `winfo_exists/lift/focus_force` on
  another thread's root; lock released before the root is assigned). Real but
  low-frequency; the correct fix (marshal via `root.after` + reserve sentinel under lock)
  touches working code in 3 files — scheduled, not done blind.
- **R2-D3** `platform/windows/gpu.py:_test_ct2_gpu` ignores its `ct2_variant` arg and
  hardcodes `device='cuda'`. Flagged as an AMD-demotion bug, but CTranslate2's ROCm build
  also uses the `'cuda'` device string, so this is likely correct — left unchanged pending
  confirmation on real AMD hardware rather than acting on an unverified claim.
- **R2-D4** `text_postprocess` filler-word stripping removes "like"/"you know"
  unconditionally (opt-in, off by default) — destructive but by-design; documented risk.

---

## How to read this

- **Severity** reflects real-world user/security impact for *this* app (a local, opt-in, privacy-first desktop tool), not raw CVSS. I deliberately down-rated several agent-flagged "critical" items that are only reachable by local processes or require unusual user configuration.
- **Verified** = I read the code and confirmed the issue first-hand. **Reported** = surfaced by a review agent, plausible, not yet hand-verified.
- Line numbers are as of the audit date; they drift as the file changes.

---

## Priority summary

| ID | Severity | Area | One-liner | Status |
|----|----------|------|-----------|--------|
| SRV-1 | High | local_server | `rstrip(b'-')` corrupts binary audio uploads | **FIXED** (2026-06-11) |
| SRV-2 | Medium | local_server | Unbounded `Content-Length` read → local OOM | **FIXED** (2026-06-11) |
| PRIV-1 | High | bundle_logs | Diagnostic zip doesn't redact hotwords / Ollama endpoint / prompts | **FIXED** (2026-06-11) |
| SPAWN-1 | High→None | startup | Windowless (`pythonw`) "double-spawn" | **NOT A BUG** (2026-06-11) |
| VC-1 | Medium | voice_commands | `${clipboard}` expanded before risky-command check; no shell-escaping | **FIXED** (2026-06-11) |
| UI-1 | Medium | history_window | Singleton `_instance` never reset on close | **FIXED** (2026-06-11) |
| LOG-1 | Medium | transcript_log / stats | Concurrent appends + rotation have no lock → rare corruption/loss | **FIXED** (2026-06-11) |
| CI-1 | Medium | CI | Tests run only on Ubuntu; Windows is the primary platform | **FIXED** (2026-06-11) |
| UI-2 | Low | dictionary | Add-word dialog leaks a daemon thread + Tk root per open | **FIXED** (2026-06-11) |
| UI-3 | Low | settings_ui | Search filter re-packs rows with hardcoded geometry | **FIXED** (2026-06-11) |
| REC-1 | Low | audio_recorder | `is_recording` read/written across threads without lock | **WONTFIX** (2026-06-11) |
| VAD-1 | Low | vad | One short-lived thread spawned per VAD event | **WONTFIX** (2026-06-11) |
| DOC-1 | Low | docs | `project-index.md` missing ~10 newer modules | **FIXED** (2026-06-11) |
| DOC-2 | Low | CITATION.cff | Version says 0.9.0, project is 0.10.0 | **FIXED** (2026-06-11) |
| DOC-3 | Low | README | "all 40 should pass" — actual count is 53 | **FIXED** (2026-06-11) |

### Resolution log (2026-06-11)

- **SRV-1** — `local_server._parse_multipart` now strips only the trailing CRLF, never `-`. Regression test `test_parse_multipart_preserves_trailing_dashes`.
- **SRV-2** — added `MAX_UPLOAD_BYTES` (500 MB); oversized `Content-Length` raises before reading. Test `test_oversized_content_length_rejected`.
- **PRIV-1** — `bundle_logs` adds `_redact_yaml` masking `hotwords`, `endpoint`, `initial_prompt` in `user_settings.yaml`; `about.txt` + console note updated. Tests `test_redact_yaml_*`.
- **VC-1** — `_expand_template(shell_safe=True)` `shlex.quote`s clipboard/selection for `run:`; `_execute_shell` now force-confirms any `run:` built from `${...}` content. Test `test_shell_safe_quotes_clipboard`. (Windows `cmd.exe` quoting is imperfect, hence the belt-and-braces forced confirm.)
- **UI-1 / UI-2** — `history_window` and `dictionary` add-word dialog now reset their singleton on close (`WM_DELETE_WINDOW` + `finally`), matching `cheat_sheet`.
- **UI-3** — `settings_ui` snapshots each row's real `pack_info()` at build and forgets-all-then-repacks-in-order on search, preserving geometry + order.
- **LOG-1** — `transcript_log` and `stats` wrap append (+rotate) in a module `threading.Lock`.
- **CI-1** — `test.yml` now runs on `[ubuntu, windows, macos]` via matrix.
- **DOC-1/2/3** — `project-index.md` refreshed with all current modules; `CITATION.cff` → 0.10.0 (now guarded by `test_citation_matches_pyproject`); README test line de-numbered.
- **SPAWN-1 — NOT A BUG.** A `WHISPER_DEBUG_SPAWN=1` startup probe proved `main()` runs **exactly once** under `pythonw`. The "two processes" are the venv `pythonw.exe` *launcher stub* (parent) plus the base interpreter it delegates to (child, which reports `sys.executable` as the venv path via `__PYVENV_LAUNCHER__`) — normal Windows venv-launcher behaviour, one logical instance, one lock, no hotkey conflict. The `.cmd` launcher shows one process because it invokes the base `python` directly. Note: this machine's `.venv/pyvenv.cfg` still points at the pre-rename `whisper-key-local` path — harmless but worth recreating the venv for cleanliness. The probe is retained (env-gated) as a debugging aid.
- **REC-1 / VAD-1 — WONTFIX (by design).** REC-1: `is_recording` is read once per audio callback; a ±1-chunk staleness at a start/stop edge is exactly what the 500 ms pre-roll buffer absorbs — adding a lock to a callback firing every ~10 ms is net-negative for a theoretical race. VAD-1: the VAD state machine fires `SILENCE_TIMEOUT` at most **once** per recording (then idles in `TIMEOUT_TRIGGERED`), so it spawns one detached thread per session, not per event — and that thread is intentional (must not block the audio callback). Both left as-is deliberately.

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

The app can have several `Tk()` roots alive at once, each with its own `mainloop` on its own daemon thread (overlay always-on + any of: first-run, fallback, cheat-sheet, dictionary, history). Tkinter tolerates this *only* as long as the roots never touch each other and each stays on its creating thread. It works today but is fragile. The tray already dodges this by launching the big windows (`--settings`, `--history`) as **subprocesses** — that's the robust pattern.

### Researched & decided (2026-06-11)

Mapped every `tk.Tk()` site and how each is launched. Findings:

- Tray-launched windows (`--settings`, `--history`, `--doctor`, `--stats`, `--selftest`) already run as **separate subprocesses** — no shared-root risk.
- The genuinely in-process roots are the **always-on level overlay** plus transient
  ones (`fallback`, `cheat_sheet`, `dictionary`, `first_run`). `cheat_sheet`,
  `dictionary`, and `history` already have **singleton guards**.
- The only realistic coexistence is **overlay + fallback window**. Each lives entirely
  on its own daemon thread with its own Tcl interpreter and never touches the other's
  widgets, which is why it has shipped without incident. The remaining real defect was
  that `fallback` could **stack multiple windows/roots** on repeated failed deliveries.

**Decision:** the big-bang "single global Tk root + Toplevels with cross-thread event
marshalling" refactor was considered and **deferred** — it's invasive, touches every
window + the audio/VAD threads, and can't be validated without a live desktop Tk
session. Risk ≫ reward for a hazard that hasn't manifested.

**Done instead:** added a singleton guard to `fallback_window` (only one alive at a
time; the transcript is already on the clipboard before `show()`, so skipping a
duplicate loses nothing). This removes the one concrete defect (stacking) and caps
in-process roots at "overlay + at most one transient", which is the safe, proven
configuration. The single-root refactor remains a documented future option if the
window set grows.

---

## Status (2026-06-11)

All 15 findings are resolved — 11 fixed with regression tests, 1 reclassified
NOT-A-BUG (SPAWN-1), 2 deliberate WONTFIX (REC-1, VAD-1), and the rest doc/CI.
See the **Resolution log** above for per-item detail. Smoke suite: 59 tests, green.

Nothing in this audit is outstanding. The architectural note below (multi-Tk-root)
and the product ideas remain as future, non-blocking improvements.

## Product ideas (not bugs) — see also README "Why this exists"

- Single-`.exe` distribution (PyInstaller/pyapp is scaffolded) + `winget` / Homebrew manifests — biggest reach unlock.
- Demo GIF in the README (highest single discoverability win; the recorder script exists in `tools/`).
- Streaming: the live **overlay preview** is now a documented feature (`docs/streaming.md`, opt-in via `streaming.streaming_enabled`). True type-as-you-go to the cursor was researched and intentionally NOT shipped as default — pasting unstable partial tokens corrupts documents. The safe form (commit only finalized/post-endpoint segments, trading Whisper accuracy for latency) is a future opt-in; `streaming_recognizer.is_endpoint()` already exists for it.
- Windowless autostart is viable (SPAWN-1 was a non-bug); a future installer could create a `pythonw` shortcut for a console-free launch. Recreate the venv first so `pyvenv.cfg` reflects the current path.
