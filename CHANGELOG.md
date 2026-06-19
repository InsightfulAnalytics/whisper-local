# Changelog

History inherited from upstream [`whisper-key-local`](https://github.com/PinW/whisper-key-local). Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.11.0]

### Added
- **Start on login (autostart)** — opt-in, built in. New `autostart` module (Windows
  `HKCU\...\Run` via stdlib `winreg`; macOS LaunchAgent). Enable via the tray
  **Start on login** checkbox, the first-run welcome checkbox, or
  `whisper-local --enable-autostart` / `--disable-autostart`. Launches windowless
  (no console flash). Off until you choose it.

### Changed
- **Default Whisper model is now `base`** (was `tiny`) — noticeably more accurate out
  of the box and still real-time on CPU (~141 MB first download).
- **Default recording mode is now `push_to_talk`** (was `toggle`) — hold the hotkey to
  talk, release to transcribe. This matches the onboarding/setup-wizard guidance
  (previously the welcome screens said "hold" while the default was toggle).

## [0.10.0]

### Added
- **Local OpenAI-compatible API server** (`whisper-local --serve`) — exposes `POST /v1/audio/transcriptions` on `localhost:7777`. Drop-in for Cursor, Open WebUI, VS Code Continue, n8n, anything that speaks the OpenAI Whisper API. Fully offline.
- **`--selftest` command** — automated sanity check: audio capture, model load, end-to-end transcription, clipboard round-trip. Catches 90% of first-launch issues in one command.
- **`--cheat-sheet` command** — opens a window showing your **currently configured** hotkeys, including transform hotkeys. Reachable from the tray (**Hotkey cheat sheet...**).
- **`--bundle-logs` command** — creates a redacted zip of recent logs + `--doctor` output + crash dumps. Attach to bug reports. Reachable from the tray (**Bundle logs for bug report...**).
- **First-run welcome window** — appears once on first launch with 3 short tips (tray icon location, hotkey hint, troubleshooting commands). Privacy assurance baked in.
- **Audio device disconnect recovery** — if a USB mic is unplugged mid-recording, the app falls back to default input and resumes silently (up to 3 retries).
- **Silent-mic detection** — if the recording is essentially zero amplitude, the app warns the user (mic muted / unplugged / OS permission denied).
- **Settings UI search box** — filter settings across all tabs with live highlighting. Ctrl+F focuses search.
- **Settings UI Reset / Backup / Restore buttons** — one-click reset to defaults, plus Backup… and Restore… file pickers wired to `--export-settings` / `--import-settings`.
- **Settings UI** — 4-tab Tkinter window covering all common settings; no YAML editing required.
- **Transcript history window** (`--history`) — searchable browser of every past transcription with preview pane and click-to-copy.
- **Persistent transcript journal** — every successful delivery is appended to `transcripts.jsonl` (last 2000 entries, auto-rotates).
- **Noise suppression** (`audio.noise_suppression.enabled`) — opt-in spectral gating via `noisereduce`; install with `pip install 'whisper-local[noise]'`.
- **Opt-in update notifications** (`update_check.enabled`) — daily GitHub release check; no audio or transcript data is ever transmitted.
- **Release pipeline** (`.github/workflows/release.yml`) — tag-triggered CI: tests → build wheel → publish to PyPI → create GitHub Release with the wheel attached.
- **Community setup** — `CODE_OF_CONDUCT.md`, `SECURITY.md`, `AUTHORS.md`, `CITATION.cff`, issue/PR templates, Dependabot, `.editorconfig`.
- **Docs** — `docs/troubleshooting.md` and `docs/faq.md` for the most common questions and symptom→fix table.

### Changed
- Repositioned README for open-source / privacy-first audience; expanded SEO and comparison tables (Wispr Flow, Dragon, Otter, WSR).
- LICENSE credits both Pin Wang (upstream author) and Rohit Burani (fork maintainer).

## [0.9.0] - 2026-05-11 (drajb/whisper-local fork)

### Added
- **Floating level overlay** — Wispr Flow–style pill at the screen edge that vibrates with your voice, shows the live streaming transcript, morphs to "Transcribing…" during processing, and flashes green/red on success/failure. Configurable position (6 presets), click-through by default.
- **Notepad fallback** — if the foreground window is the desktop / Start Menu / no text field, the transcript opens in Notepad instead of disappearing.
- **Always-clipboard safety net** — every transcript is copied to the clipboard *before* any paste routing; you can always `Ctrl+V` anywhere as a recovery.
- **Dedicated rephrase hotkey** — `Ctrl+Shift+Win` selects, records instruction, sends to Ollama, pastes the rewrite back. No voice-command-mode detour.
- **Pause-all hotkey** — `Ctrl+Alt+Win` disables all Whisper Local hotkeys (except itself) until pressed again.
- **Smart Whisper prompt from selection** — opt-in `whisper.prompt_from_selection`: at recording start, the active selection seeds Whisper's `initial_prompt` for that recording.
- **Translation profile** — Whisper `task=translate`: speak any language, get English.
- **Continuous mode** — `audio.continuous_mode`: auto-restart recording after each delivery (Esc exits).
- **Auto-pause media** — `audio.pause_media_on_record`: sends system play/pause on recording start so Spotify/YouTube go quiet.
- **Voice command macros** — `then:` chain in `commands.yaml`, with a `delay: <seconds>` step for pacing.
- **Vocab import** — `whisper-local --import-vocab FOLDER` scans text files, ranks proper nouns / jargon by frequency, merges top 50 into `whisper.hotwords`.
- **Transcript export** — `whisper-local --export-transcripts FILE.{txt,md,csv}`.
- **Daily summary toast** — first launch of the day shows yesterday's word count and minutes saved.
- **Audit log** — opt-in `audit.enabled`: append-only `audit.log` of timestamp + event + app + char-count (no transcript text).
- **AI rephrase voice commands** — select text, say "make this concise" / "make this professional" / "fix grammar"; the selection is sent to local Ollama and the response replaces it.
- **Inline voice formatting** — say "comma", "period", "new line", "new paragraph", "question mark", "open quote", "dash" etc. mid-sentence to insert punctuation/structure.
- **Voice command DSL upgrade** — `match_regex:` patterns, `${selection}` / `${clipboard}` template vars, per-command `confirm:` flag.
- **Risky-shell confirmation** — voice commands matching dangerous patterns (`rm -r`, `format`, `shutdown`, redirects, `sudo`, etc.) now prompt before executing.
- **Setup wizard** — `whisper-local --setup` walks model selection (hardware-aware), recording mode, and microphone.
- **Stats dashboard** — `whisper-local --stats` and tray item show transcription history, words, minutes saved vs typing.
- **Multi-language quick-switch** — tray submenu of 15 languages, hot-swaps `whisper.language`.
- **Whisper warmup** — model runs a 1-second zeros transcription right after load so the first real recording skips JIT.
- **Auto-trim trailing silence** — VAD-style RMS scan trims the tail of each recording, removing Whisper's silence-induced hallucinations.
- **Tray mic level meter** — animated 6-bar level inside the tray icon's tooltip while recording.
- **Per-profile Whisper `initial_prompt`** — each profile primes Whisper for its context (code identifiers, chat tone, markdown notes).
- **Pre-roll audio buffer** — `sd.InputStream` is opened once at startup and runs continuously. A 500ms ring buffer is prepended to every recording, eliminating first-word clipping on push-to-talk launches. `latency='low'` for smaller PortAudio buffers.
- **Restart-on-second-launch** — launching while an instance is running now terminates the existing process via PID file + SIGTERM and takes over the lock instead of refusing to start.
- **`whisper-local --doctor`** — structured health check across runtime, dependencies, config, audio, model cache, hotkeys, and recent log errors.
- **Recent transcriptions menu** — last 10 transcriptions kept in a deque and exposed via `Recent` submenu in the system tray; click any to copy back to clipboard.
- **Hot-reload commands.yaml** — the file's mtime is checked before each match; edits take effect on the next transcription with no restart.
- **Tray notifications on failure** — empty transcription / no audio captured surface as a tray toast instead of silently dropping.
- **Crash reports** — uncaught exceptions write a timestamped report to `%APPDATA%\whisperkey\crashes\` with the traceback and last 50 log lines.
- **Log rotation** — `app.log` rotates at 5MB with 3 backups (was unbounded).
- **Smoke test suite** — `python -m unittest tests.test_smoke` covers package metadata, instance-manager wiring, hotkey utilities, asset path resolution, and YAML safety properties.
- **Personal launcher** — `whisper-local.cmd` plus Start Menu and Startup-folder shortcuts.

### Changed
- Rebrand from `whisper-key-local` → `whisper-local`. CLI: `whisper-local` / `wl`. Display name: "Whisper Local". Repo URL: `drajb/whisper-local`.
- Audio host matcher now does substring matching, so `audio.host: WASAPI` correctly resolves to "Windows WASAPI" instead of falling back to MME.
- Auto-updater removed entirely (network call + pip install path).
- Risky `reg add` voice commands removed from defaults.
- GitHub Actions workflows for Claude review removed (no longer wired to a secret).

### Fixed
- Defensive `os.path.isdir` checks around DLL search dirs in `platform/windows/gpu.py` (skips non-existent entries from `PATH`).

---

## [0.8.1] - 2026-04-18

### Added
- **Push-to-talk mode** - New `hotkey.recording_mode` config: hold the recording hotkey to record, release to stop and transcribe (#45)
- **Console window management** - Two exe variants:
  - `whisper-key.exe` - runs in Windows Terminal with full color (same as before)
  - `whisper-key-hideable.exe` - conhost with hide-to-tray support (`console.start_hidden` config option) (#50)

### Fixed
- Stop key requiring two presses in toggle mode (#54)

## [0.8.0] - 2026-03-17

### Added
- **GPU onboarding** - Detects your GPU on first launch and offers one-press install of CUDA or ROCm runtime libraries. Supports NVIDIA, AMD RDNA 2+, and RDNA 1 (manual setup) (#44)
- **Auto-update** - Checks PyPI for new versions on startup with option to update in-place (#43)
- **GPU and runtime detection** - Shows GPU model and runtime status on startup (#41)
- **Overlay config** - Config updates now merge cleanly without overwriting user comments or structure (#40)
- `initial_prompt` config option to bias Whisper transcription toward expected content (#39)
- `log_transcriptions` config option (default: off) for privacy

### Changed
- **Replaced PyInstaller with pyapp** - Windows exe is now a single `whisper-key.exe` that bootstraps its own Python environment. No more zip extraction or separate AMD variant (#42)
- Updated README for new install flow

### Removed
- PyInstaller build system and related runtime hooks

## [0.7.1] - 2026-03-08

### Added
- **Transcription complete sound** - Optional audio notification when transcription finishes (`audio_feedback.transcription_complete_enabled`) (#35)
- **Custom hotwords** - Bias transcription toward specific words/phrases via `whisper.hotwords` config (#34)
- **Open model cache** shortcut in system tray menu
- CONTRIBUTING.md with PR guidelines

### Fixed
- **Portable exe crash on startup** - `commands.defaults.yaml` was not bundled in PyInstaller build, causing `[WinError 2]` crash when voice commands initialize (#37)
- Startup error handler now logs full traceback for better crash diagnostics

## [0.7.0] - 2026-02-27

### Added
- **Voice command mode** - Dedicated hotkey (`Alt+Win` / `Fn+Command`) records speech and matches against user-defined trigger phrases in `commands.yaml` (#33)
  - `run` action — execute shell commands (e.g., "open notepad" → `notepad.exe`)
  - `hotkey` action — send keyboard shortcuts (e.g., "undo" → `Ctrl+Z`)
  - `type` action — deliver pre-written text (e.g., "my email" → `user@example.com`)
  - Case-insensitive substring matching with longest-trigger-first priority
  - Auto-send support — press `Alt` to stop and send ENTER after type commands
- **Commands file shortcuts** in system tray menu for quick editing
- Terminal tab title set to "Whisper Key" on startup

### Changed
- **Hotkey config refactored** — replaced `stop_with_modifier` toggle with explicit `stop_key` and `auto_send_key` settings
- Recording hotkey is now start-only (no longer toggles)
- Cleaner console messages: one-line-per-hotkey format, indented recording output
- Renamed `documentation/` folder to `docs/`
- macOS config path moved to `~/.whisperkey`
- Updated GPU setup guide: simplified ROCm instructions, updated wheel versions

### Fixed
- ROCm runtime hook now finds pip-installed HIP SDK

## [0.6.3] - 2026-02-17

### Added
- **Direct text injection** - New `type` delivery method using native ctypes `SendInput` with `KEYEVENTF_UNICODE`, bypassing clipboard entirely (Windows only) (#21)
- **Configurable delivery method** - Choose between `paste` (clipboard + Ctrl+V) and `type` (direct key injection) via `clipboard.delivery_method`
- **Pre-paste delay** - `paste_pre_paste_delay` setting (50ms default) fixes intermittent empty paste caused by Windows Clipboard History service contention (#21)
- **Scaling auto-enter delay** - Type mode delay before Enter now scales with text length: `type_auto_enter_delay + chars/100 * type_auto_enter_delay_per_100_chars`
- **Real-time speech preview** - Experimental streaming transcription using sherpa-onnx (enable with `streaming.streaming_enabled: true`; downloads a small ~20MB model on first use)
- **Application icon** - PyInstaller exe now has a proper app icon
- **`wk` CLI alias** - Short command alias for `whisper-key`

### Fixed
- **Auto-paste empty text bug** - Clipboard race condition where Windows Clipboard History service contests clipboard between copy and paste, causing target app to receive nothing (#21)

### Changed
- Replaced pyautogui with native ctypes `SendInput` for keyboard simulation on Windows (smaller dependency footprint, atomic key injection)
- Restructured clipboard config: `paste_*` prefix for paste-mode settings, `type_*` for type-mode settings, `macos_*` for macOS-only
- Delivery method validation moved into platform keyboard modules
- Default `paste_clipboard_restore_delay` set to 0.5s

### Removed
- **pyautogui** dependency — replaced by native ctypes

## [0.6.2] - 2026-02-09

### Added
- **AMD GPU portable exe** - Separate ROCm build variant for AMD RX 5000+ GPUs
- **CPU/GPU mode display** - Shows device mode and compute type on startup
- **Distil-whisper models** - Added distil-medium.en and distil-small.en to default config

### Fixed
- **Model load crash** - Bundled correct MSVCP140.dll instead of PyInstaller's incompatible version (#22)
- **Tray icon path** - Fixed icon resolution for PyInstaller builds using `resolve_asset_path()`

### Changed
- Updated GPU setup guide with pip, pipx, and portable exe instructions for AMD GPUs
- Updated README with AMD GPU download variant

## [0.6.1] - 2026-02-04

### Added
- **macOS support** - Full platform abstraction layer with native integration for hotkeys (NSEvent), keyboard simulation (Quartz CGEvent), and system tray (#23)
  - Fn key modifier support for hotkeys
  - Accessibility permission prompt for auto-paste
  - Platform-specific default hotkeys: fn+ctrl (record), shift (cancel), cmd+v (paste)
- `--test` flag for running a separate test instance alongside the main app
- CUDA setup instructions in config file comments (cuDNN no longer required)

### Changed
- Reduced console verbosity by removing config update messages
- ten-vad is now a standard PyPI dependency (no separate install step needed)
- Updated README with macOS installation and usage instructions

### Fixed
- UTF-8 stdout encoding for special characters on Windows
- Audio feedback sounds going silent after idle periods on Windows (switched to winmm backend)
- PyPI package missing platform-specific tray icons
- PyInstaller build: ten_vad path and Windows platform assets

### Dependencies
- **ten-vad**: Now `>=1.0.6` (was git-only)
- **pyobjc-framework-Quartz**: Added for macOS (keyboard simulation)
- **pyobjc-framework-ApplicationServices**: Added for macOS (Accessibility permissions)

## [0.5.3] - 2026-01-19

### Fixed
- PyInstaller crash with ctranslate2 4.6.3 due to bundled MSVCP140.dll version mismatch

### Changed
- Replaced scipy with soxr for audio resampling (smaller bundle size)

### Dependencies
- **scipy**: Removed - no longer required
- **soxr**: Added `>=0.5.0` for high-quality audio resampling

## [0.5.2] - 2026-01-16

### Fixed
- Single-key hotkeys (e.g., F13) causing "hotkey already registered" error when `stop_with_modifier_enabled` was true (#14)

## [0.5.1] - 2026-01-16

### Fixed
- User settings file was showing "DO NOT EDIT THIS FILE" header from the defaults template

### Added
- Configurable paste hotkey setting (`clipboard.paste_hotkey`) - workaround for Claude Code changing CTRL+V to CTRL+SHIFT+V (possibly a bug)
- Console messages when opening log file and settings from system tray

## [0.5.0] - 2026-01-15

### Added
- **Custom local model support** - Load any Whisper model from a local folder or HuggingFace path (#10)
- **New models**: large-v3-turbo and distil-large-v3.5
- **View Log** shortcut in system tray menu (#9)
- **Advanced Settings** shortcut in system tray menu

### Changed
- Config key renamed from `whisper.model_size` to `whisper.model`
- Model menu in system tray now built dynamically with grouped separators
- Updated model download sizes to reflect actual faster-whisper downloads

### Fixed
- Cache detection for non-Systran models (e.g., large-v3-turbo showed "Downloading..." when already cached)
- Config section headers duplicating on save

### Dependencies
- **faster-whisper**: `>=1.1.1` → `>=1.2.1`
  Required for distil-large-v3.5 support
- **ctranslate2**: Added explicit `>=4.6.3` requirement
  May fix GPU crashes on systems without cuDNN installed (#15)

## [0.4.0] - 2026-01-14

### Added
- Audio source selection from system tray menu (WASAPI devices)
- WASAPI loopback support with bundled custom PortAudio DLL for recording system audio
- Version display in startup message

### Fixed
- WASAPI devices that don't support 16kHz now work via automatic resampling
- WASAPI stream reopen race condition with OS-level cleanup delay
- User feedback when audio device switch fails

## [0.3.0] - 2025-08-19

### Added
- Complete PyPI package distribution support with robust asset resolution
- Audio recording duration display
- Cancel recording hotkey with distinct sound feedback

### Changed
- Unified version tracking from pyproject.toml
- Centralized user data directory with proper app.log location handling
- Enhanced release script to include git push and use version-specific changelog notes
- Updated README with new install instructions

### Fixed
- Various typos and documentation inconsistencies

## [0.2.0] - 2025-08-15

### Added
- Max recording duration with callback-based duration limiting for audio capture
- Intelligent hotkey conflict detection with automatic resolution
- Global exception handling with stderr redirection to app.log
- VAD configuration reorganization into dedicated Voice Activity Detection section
- Instance Manager component (renamed from single_instance.py for consistency)

### Changed
- Massive code reduction: 50% reduction across 11 core files (4,200 → 2,087 lines)
- Complete removal of redundant docstrings and beginner-friendly comments
- Simplified component interfaces and eliminated circular dependencies
- Enhanced build script with improved Start Menu compatibility and asset path resolution
- Updated automation workflow to focus on real issues over defensive programming
- Exception handling standardization across all components
- Import reorganization following PEP 8 standards
- Magic number extraction to named constants
- Component interface simplification with better separation of concerns

### Fixed
- Critical race conditions in transcription pipeline and pending model changes
- Bare except clause that could mask critical exceptions
- Inconsistent OptionalComponent usage in SystemTray type annotations

### Removed
- Entire test suite to focus on shipping over ceremony
- Defensive programming patterns and unnecessary validation
- Windows API clipboard fallback complexity
- Complex model loading progress tracking
- Redundant configuration options and unused settings
- Dead code and unused functions throughout codebase

## [0.1.3] - 2025-08-11

### Added
- Comprehensive CHANGELOG.md for project releases
- Version bump command for Claude AI assistant

### Changed
- Updated build instructions and removed redundant builder.py

### Fixed
- Single instance detector exit error in built executable

## [0.1.2] - 2025-08-11

### Added
- Single-instance detection with mutex to prevent multiple app instances
- TEN VAD (Voice Activity Detection) pre-check system with advanced post-processing
- Audio feedback component for recording events
- PyInstaller packaging system for Windows executable distribution
- Auto-enter hotkey functionality with configurable modifiers
- Stop-with-modifier hotkey functionality
- Alternative keycode checker tool for hotkey configuration
- Context manager for consistent error handling across components

### Changed
- Default Whisper model changed from `tiny` to `base` for better accuracy
- Default hotkeys updated to CTRL+WIN+SPACE (record) and CTRL+WIN+SHIFT+SPACE (stop)
- Renamed `auto_enter_delay` to `key_simulation_delay` for clarity
- Simplified clipboard copy operation for better performance
- Default console logging level set to warning for regular users
- Disabled UPX compression in PyInstaller to reduce antivirus false positives
- Improved system tray model selection to show actual model names
- Streamlined user feedback messages around clipboard actions and startup

### Fixed
- CTRL+C unresponsiveness by adding proper hotkey listener cleanup during shutdown
- Windows key support in hotkey detection
- Auto-enter hotkey now respects auto-paste setting
- Config validation now persists properly to user settings file
- YAML structure corruption by using clean config template
- Unicode logging errors on Windows
- Executable Start Menu launch bug with working directory
- Module imports after directory refactor

### Removed
- `suppress_warnings` config option and related code
- Redundant system tray print statements
- Duplicate "Ready to paste" message

## [0.1.1] - 2025-07-15

### Added
- Complete working whisper speech-to-text application
- Comprehensive configuration system with YAML support
- Interactive key helper utility for hotkey configuration
- Auto-paste feature with Windows API integration
- System tray icon functionality with visual recording status
- User settings system with system tray controls
- Clipboard preservation feature
- Model selection submenu in system tray
- English-specific model options
- Async model loading with responsive system tray
- Tool to clear application log file
- Tool to clear model cache

### Changed
- Refactored project structure and updated documentation
- Renamed main.py to whisper-key.py for better clarity
- Renamed log file from whisper_app.log to app.log
- Updated to use faster-whisper framework
- Improved model download messaging with cache detection

### Fixed
- Module imports and directory structure issues
- System tray menu organization and cleanup

## [0.1.0] - 2025-06-01

### Added
- Initial project setup
- Core speech-to-text functionality
- Basic hotkey detection
- Audio recording capabilities
- Clipboard integration