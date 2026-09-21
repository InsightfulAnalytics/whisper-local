# doctor.py
# `whisper-local --doctor` health check. Walks runtime, dependencies, config,
# audio devices, GPU/precision, Whisper model cache, hotkeys, post-process/Ollama,
# transforms, and recent log errors, printing a per-section report.
# Exit 0 = clean, 1 = issues.

import importlib
import os
import platform
import sys
from pathlib import Path

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

OK = f"{GREEN}[OK]{RESET}  "
WARN = f"{YELLOW}[!]{RESET}   "
FAIL = f"{RED}[X]{RESET}   "
INFO = f"{DIM}[i]{RESET}   "

REQUIRED_PACKAGES = [
    "faster_whisper", "ctranslate2", "numpy", "soxr", "sounddevice",
    "pyperclip", "ruamel.yaml", "pystray", "PIL", "playsound3", "ten_vad",
]


class Check:
    def __init__(self, name):
        self.name = name
        self.status = None
        self.detail = ""

    def ok(self, detail=""):
        self.status = OK
        self.detail = detail
        return self

    def warn(self, detail=""):
        self.status = WARN
        self.detail = detail
        return self

    def fail(self, detail=""):
        self.status = FAIL
        self.detail = detail
        return self

    def info(self, detail=""):
        self.status = INFO
        self.detail = detail
        return self

    def print(self):
        line = f"{self.status}{self.name}"
        if self.detail:
            line += f"  {DIM}{self.detail}{RESET}"
        print(line)


def run_doctor() -> int:
    print(f"\n{BOLD}Whisper Local — Doctor{RESET}\n{'=' * 24}\n")

    failures = 0
    failures += _section_runtime()
    failures += _section_packages()
    failures += _section_config()
    failures += _section_audio()
    failures += _section_gpu()
    failures += _section_model()
    failures += _section_hotkeys()
    failures += _section_postprocess_and_rules()
    failures += _section_logs()

    print()
    if failures == 0:
        print(f"{GREEN}{BOLD}All checks passed.{RESET}\n")
        return 0
    print(f"{RED}{BOLD}{failures} issue(s) found.{RESET}  Review the [X] lines above.\n")
    return 1


def _section_runtime() -> int:
    print(f"{BOLD}Runtime{RESET}")
    failures = 0

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        Check("Python version").ok(py_version).print()
    else:
        Check("Python version").fail(f"{py_version} (need ≥3.11)").print()
        failures += 1

    Check("Platform").info(f"{platform.system()} {platform.release()}").print()

    # Too-old msvcp140.dll = silent hard crash at model load (see platform/windows/app.py)
    if sys.platform == "win32":
        try:
            from .platform import app as platform_app
            detail, warning = platform_app.native_runtime_status()
            if warning:
                Check("VC++ runtime").fail(warning).print()
                failures += 1
            else:
                Check("VC++ runtime").ok(detail).print()
        except Exception as e:
            Check("VC++ runtime").fail(str(e)).print()
            failures += 1

    try:
        from .utils import get_version
        Check("Whisper Local version").ok(get_version()).print()
    except Exception as e:
        Check("Whisper Local version").fail(str(e)).print()
        failures += 1

    print()
    return failures


def _section_packages() -> int:
    print(f"{BOLD}Dependencies{RESET}")
    failures = 0

    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            Check(pkg).ok().print()
        except ImportError as e:
            Check(pkg).fail(str(e)).print()
            failures += 1

    if sys.platform == "win32":
        for pkg in ("win32api", "global_hotkeys"):
            try:
                importlib.import_module(pkg)
                Check(pkg).ok().print()
            except ImportError as e:
                Check(pkg).fail(str(e)).print()
                failures += 1

    print()
    return failures


def _section_config() -> int:
    print(f"{BOLD}Configuration{RESET}")
    failures = 0

    try:
        from .utils import get_user_app_data_path
        config_dir = Path(get_user_app_data_path())
        Check("Config directory").ok(str(config_dir)).print()

        if not os.access(config_dir, os.W_OK):
            Check("Config directory writable").fail("not writable").print()
            failures += 1
        else:
            Check("Config directory writable").ok().print()
    except Exception as e:
        Check("Config directory").fail(str(e)).print()
        return failures + 1

    user_settings = config_dir / "user_settings.yaml"
    failures += _check_yaml_parses("user_settings.yaml", user_settings, required=False)

    commands_yaml = config_dir / "commands.yaml"
    failures += _check_yaml_parses("commands.yaml", commands_yaml, required=False, count_key="commands")

    try:
        from .config_manager import ConfigManager
        cfg = ConfigManager(quiet=True)
        Check("Effective config loads").ok().print()
        whisper_cfg = cfg.get_whisper_config()
        Check("Selected model").info(
            f"{whisper_cfg.get('model', '?')} on {whisper_cfg.get('device', '?')} "
            f"({whisper_cfg.get('compute_type', '?')})").print()
        hotkey_cfg = cfg.get_hotkey_config()
        Check("Recording mode").info(hotkey_cfg.get('recording_mode', 'toggle')).print()
        Check("Recording hotkey").info(hotkey_cfg.get('recording_hotkey', '?')).print()
    except Exception as e:
        Check("Effective config loads").fail(str(e)).print()
        failures += 1

    print()
    return failures


def _check_yaml_parses(label: str, path: Path, required: bool, count_key: str = None) -> int:
    if not path.exists():
        if required:
            Check(label).fail(f"missing at {path}").print()
            return 1
        Check(label).info("not present (defaults will be used)").print()
        return 0
    try:
        from ruamel.yaml import YAML
        with open(path, encoding="utf-8") as f:
            data = YAML().load(f)
        detail = ""
        if count_key and isinstance(data, dict) and isinstance(data.get(count_key), list):
            detail = f"{len(data[count_key])} entries"
        Check(label).ok(detail).print()
        return 0
    except Exception as e:
        Check(label).fail(str(e)).print()
        return 1


def _section_audio() -> int:
    print(f"{BOLD}Audio{RESET}")
    failures = 0

    try:
        import sounddevice as sd
        from .config_manager import ConfigManager
        cfg = ConfigManager(quiet=True).get_audio_config()
        configured_host = cfg.get('host')

        # sd.query_devices(kind='input') returns the OS default, which on Windows is
        # the MME copy of the mic. The app opens the configured host's default
        # instead, so probing the OS default reports the wrong device and the wrong
        # sample rate. Resolve the same way the app does.
        os_default = sd.query_devices(kind='input')
        os_host = sd.query_hostapis(os_default['hostapi'])['name']

        device_index = _resolve_host_default_input(configured_host) if configured_host else None
        if device_index is None:
            in_use = os_default
            Check("Default input device").ok(f"{in_use.get('name', '?')}  (OS default)").print()
            Check("Host API").info(f"{os_host}  (auto-selected)").print()
        else:
            in_use = sd.query_devices(device_index)
            Check("Default input device").ok(
                f"{in_use.get('name', '?')}  (device {device_index})").print()
            Check("Host API (configured)").info(
                f"{configured_host}  (OS default host: {os_host})").print()
        Check("Sample rate").info(f"{int(in_use.get('default_samplerate', 0))} Hz").print()

        # Windows endpoint DSP is tuned for call intelligibility, not for speech
        # recognition, and it sits upstream of anything this app can change.
        detail, affects_in_use = _windows_mic_enhancements_note(in_use.get('name', ''))
        if detail:
            check = Check("Mic enhancements")
            (check.warn(detail) if affects_in_use else check.info(detail)).print()
    except Exception as e:
        Check("Audio device probe").fail(str(e)).print()
        failures += 1

    print()
    return failures


# Mirrors StateManager._get_default_device_for_host. The app opens the configured
# host API's default input, so that is the device --doctor must report on.
def _resolve_host_default_input(host_name: str):
    try:
        import sounddevice as sd

        target_index = None
        target_host = None
        for idx, host in enumerate(sd.query_hostapis()):
            # Substring match: config.defaults.yaml documents bare "WASAPI" as legal,
            # while the host reports itself as "Windows WASAPI".
            if host_name.lower() in host['name'].lower() or host['name'].lower() in host_name.lower():
                target_index = idx
                target_host = host
                break
        if target_host is None:
            return None

        default_input = target_host.get('default_input_device', -1)
        if default_input is not None and default_input >= 0:
            if sd.query_devices(default_input).get('max_input_channels', 0) > 0:
                return default_input

        for idx, device in enumerate(sd.query_devices()):
            if device['hostapi'] == target_index and device.get('max_input_channels', 0) > 0:
                return idx
    except Exception:
        return None
    return None


# Windows endpoint DSP ("Audio enhancements") sits between the microphone and the
# app. Vendor voice-comms chains are tuned for call intelligibility, not for ASR,
# and can suppress exactly the low-energy speech Whisper needs.
#
# The toggle writes PKEY_AudioEndpoint_Disable_SysFx = 1. Two traps, both of which
# produced a false "enhancements are on" here before this was measured against the
# actual signal: the value is written under the endpoint's FxProperties subkey and
# NOT under Properties, and the endpoint list is full of devices that are unplugged
# or absent, so anything that ignores DeviceState reports on dead hardware.
# Absent in both subkeys means "cannot tell", not "enabled": say so rather than
# crying wolf.
_PKEY_DISABLE_SYSFX = "{1da5d803-d492-4edd-8c23-e0c0ffee7f0e},5"
_PKEY_FRIENDLY_NAME = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"
_DEVICE_STATE_ACTIVE = 1


def _read_sysfx_flag(root, endpoint):
    """Returns 1 (disabled), 0 (enabled) or None (not recorded)."""
    import winreg

    for sub in ("FxProperties", "Properties"):
        try:
            with winreg.OpenKey(root, endpoint + "\\" + sub) as props:
                try:
                    return int(winreg.QueryValueEx(props, _PKEY_DISABLE_SYSFX)[0])
                except FileNotFoundError:
                    continue
        except OSError:
            continue
    return None


def _windows_mic_enhancements_note(in_use_name: str = "") -> tuple:
    """Returns (detail, is_warning). Empty detail means "nothing useful to say"."""
    if platform.system() != "Windows":
        return "", False
    try:
        import winreg

        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
        active = []
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            for i in range(winreg.QueryInfoKey(root)[0]):
                endpoint = winreg.EnumKey(root, i)
                try:
                    with winreg.OpenKey(root, endpoint) as key:
                        if int(winreg.QueryValueEx(key, "DeviceState")[0]) != _DEVICE_STATE_ACTIVE:
                            continue
                except OSError:
                    continue

                name = endpoint[:8]
                try:
                    with winreg.OpenKey(root, endpoint + r"\Properties") as props:
                        name = str(winreg.QueryValueEx(props, _PKEY_FRIENDLY_NAME)[0])
                except OSError:
                    pass
                active.append((name, _read_sysfx_flag(root, endpoint)))

        if not active:
            return "", False

        # Endpoint friendly names are short ("Microphone Array") while sounddevice
        # reports the full device string, so match by containment either way.
        lowered = (in_use_name or "").lower()
        mine = [(n, f) for n, f in active if n and (n.lower() in lowered or lowered in n.lower())]
        subject = mine or active
        label = "the mic in use" if mine else f"{len(active)} active endpoint(s)"

        if any(flag == 0 for _, flag in subject):
            on = sorted({n for n, f in subject if f == 0})
            return (f"ON for {', '.join(on)}. "
                    f"Settings > Sound > Input > Audio enhancements", True)
        if all(flag == 1 for _, flag in subject):
            return f"off for {label}", False
        return (f"not recorded for {label}; Windows has not written the flag, "
                f"so this cannot be read from the registry"), False
    except Exception:
        return "", False


def _section_gpu() -> int:
    print(f"{BOLD}GPU{RESET}")
    failures = 0

    try:
        from .config_manager import ConfigManager
        whisper_cfg = ConfigManager(quiet=True).get_whisper_config()
    except Exception as e:
        Check("GPU config").fail(str(e)).print()
        print()
        return 1

    device = whisper_cfg.get('device', 'cpu')
    compute_type = whisper_cfg.get('compute_type', '?')

    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
    except Exception as e:
        Check("CTranslate2 CUDA probe").fail(str(e)).print()
        print()
        return 1

    if device != 'cuda':
        Check("Device").info(f"{device} (CUDA devices visible: {cuda_count})").print()
        if cuda_count:
            Check("Unused GPU").warn(
                f"{cuda_count} CUDA device(s) present but device is '{device}'").print()
        print()
        return 0

    if cuda_count:
        Check("CUDA devices").ok(str(cuda_count)).print()
    else:
        Check("CUDA devices").fail(
            "device is 'cuda' but CTranslate2 sees none; transcription will fall back to CPU").print()
        failures += 1

    # A requested compute_type is resolved against what the device supports, so the
    # requested value alone does not tell you what actually runs.
    try:
        supported = sorted(ctranslate2.get_supported_compute_types(device if cuda_count else 'cpu'))
        Check("Compute type").info(f"{compute_type}  (supported: {', '.join(supported)})").print()
        if compute_type not in supported:
            Check("Compute type supported").warn(
                f"'{compute_type}' is not in the supported set; it will be substituted").print()
    except Exception as e:
        Check("Compute type probe").warn(str(e)).print()

    print()
    return failures


def _section_model() -> int:
    print(f"{BOLD}Whisper model cache{RESET}")
    failures = 0

    try:
        from .config_manager import ConfigManager
        from .model_registry import ModelRegistry
        cfg = ConfigManager(quiet=True)
        whisper_cfg = cfg.get_whisper_config()
        backend = whisper_cfg.get('backend', 'faster_whisper')
        Check("Whisper backend").info(backend).print()
        if backend == 'whisper_cpp':
            try:
                import pywhispercpp  # noqa
                Check("pywhispercpp installed").ok(getattr(pywhispercpp, '__version__', '?')).print()
            except ImportError:
                Check("pywhispercpp installed").fail("missing — run: pip install pywhispercpp").print()
                failures += 1
        streaming_cfg = cfg.get_streaming_config()
        registry = ModelRegistry(
            whisper_models_config=whisper_cfg.get('models', {}),
            streaming_models_config=streaming_cfg.get('models', {}),
        )
        model_key = whisper_cfg.get('model', 'tiny')
        cached = False
        for getter in ('is_cached', 'is_model_cached', 'get_cached_models'):
            if hasattr(registry, getter):
                try:
                    result = getattr(registry, getter)(model_key) if getter != 'get_cached_models' else getattr(registry, getter)()
                    cached = bool(result) if getter != 'get_cached_models' else (model_key in (result or []))
                    break
                except TypeError:
                    continue
        if cached:
            Check(f"Model '{model_key}' cached").ok().print()
        else:
            Check(f"Model '{model_key}' cache").info("will download on first use").print()
    except Exception as e:
        Check("Model cache check").warn(str(e)).print()

    print()
    return failures


def _section_hotkeys() -> int:
    print(f"{BOLD}Hotkeys{RESET}")
    failures = 0

    try:
        from .platform import hotkeys  # noqa
        Check("Hotkey backend importable").ok().print()
    except Exception as e:
        Check("Hotkey backend importable").fail(str(e)).print()
        failures += 1

    if sys.platform == "win32":
        try:
            from .platform.windows import keyboard  # noqa
            Check("Keyboard simulation backend").ok("ctypes SendInput").print()
        except Exception as e:
            Check("Keyboard simulation backend").fail(str(e)).print()
            failures += 1

    print()
    return failures


def _section_postprocess_and_rules() -> int:
    print(f"{BOLD}Post-process & app rules{RESET}")
    failures = 0

    try:
        from .config_manager import ConfigManager
        cfg = ConfigManager(quiet=True)
        post_cfg = cfg.get_postprocess_config()
        if post_cfg.get('strip_filler_words') or post_cfg.get('capitalize_first') or post_cfg.get('ensure_punctuation'):
            enabled = [k for k in ('strip_filler_words', 'capitalize_first', 'ensure_punctuation') if post_cfg.get(k)]
            Check("Text filters").ok(", ".join(enabled)).print()
        else:
            Check("Text filters").info("none enabled").print()

        llm_cfg = post_cfg.get('llm') or {}
        if llm_cfg.get('enabled'):
            from .text_postprocess import _provider
            if _provider(llm_cfg) == 'claude':
                failures += _probe_claude(llm_cfg)
            else:
                failures += _probe_ollama(llm_cfg)
        else:
            Check("LLM post-edit").info("disabled").print()
    except Exception as e:
        Check("Post-process config").warn(str(e)).print()

    try:
        from pathlib import Path
        from .utils import get_user_app_data_path
        rules_path = Path(get_user_app_data_path()) / "app_rules.yaml"
        if rules_path.exists():
            from ruamel.yaml import YAML
            with open(rules_path, encoding="utf-8") as f:
                data = YAML().load(f) or {}
            count = len((data.get('rules') or []))
            Check("Per-app rules").ok(f"{count} rules in app_rules.yaml").print()
        else:
            Check("Per-app rules").info("not yet created").print()
    except Exception as e:
        Check("Per-app rules").warn(str(e)).print()

    print()
    return failures


def _probe_ollama(cfg: dict) -> int:
    import json
    import urllib.error
    import urllib.request
    endpoint = cfg.get('endpoint', 'http://localhost:11434').rstrip('/')
    timeout = float(cfg.get('timeout', 5))
    try:
        with urllib.request.urlopen(f"{endpoint}/api/tags", timeout=timeout) as resp:
            data = json.loads(resp.read())
        names = [m.get('name', '') for m in data.get('models', [])]
        target = cfg.get('model', 'llama3.2')
        if any(target in n for n in names):
            Check("Ollama post-edit").ok(f"{endpoint} reachable, model '{target}' available").print()
            return 0
        Check("Ollama post-edit").warn(f"{endpoint} reachable but '{target}' not pulled").print()
        return 1
    except (urllib.error.URLError, OSError) as e:
        Check("Ollama post-edit").fail(f"unreachable at {endpoint} ({e})").print()
        return 1

# Claude reachability. Costs a real (sub-cent) API call on purpose: a key that
# parses but is revoked, or a blocked network, only shows up on a live request.
def _probe_claude(cfg: dict) -> int:
    import os
    key_from_config = bool(cfg.get('claude_api_key'))
    api_key = str(cfg.get('claude_api_key') or os.environ.get('ANTHROPIC_API_KEY') or '').strip()
    model = cfg.get('claude_model') or 'claude-haiku-4-5'
    if not api_key:
        Check("Claude post-edit").fail(
            "no API key (set postprocess.llm.claude_api_key or ANTHROPIC_API_KEY)").print()
        return 1
    try:
        import anthropic
    except ImportError:
        Check("Claude post-edit").fail(
            'anthropic not installed (pip install "whisper-local[claude]")').print()
        return 1
    source = "config" if key_from_config else "ANTHROPIC_API_KEY"
    try:
        client = anthropic.Anthropic(api_key=api_key,
                                     timeout=float(cfg.get('claude_timeout', 20)),
                                     max_retries=0)
        client.messages.create(model=model, max_tokens=1,
                               messages=[{"role": "user", "content": "ping"}])
        Check("Claude post-edit").ok(f"{model} reachable, key from {source}").print()
        return 0
    except Exception as e:
        Check("Claude post-edit").fail(f"{model} call failed ({e})").print()
        return 1



def _section_logs() -> int:
    print(f"{BOLD}Recent log activity{RESET}")
    failures = 0

    try:
        from .utils import get_user_app_data_path
        log_path = Path(get_user_app_data_path()) / "app.log"
        if not log_path.exists():
            Check("app.log").info("not yet created").print()
            print()
            return 0

        size_kb = log_path.stat().st_size / 1024
        Check("app.log size").info(f"{size_kb:.1f} KB").print()

        recent_errors = _scan_recent_errors(log_path)
        if recent_errors:
            Check(f"Recent errors (last 200 lines): {len(recent_errors)}").warn().print()
            for line in recent_errors[-3:]:
                print(f"   {DIM}{line.strip()[:140]}{RESET}")
        else:
            Check("No recent ERROR/CRITICAL in log").ok().print()
    except Exception as e:
        Check("Log scan").warn(str(e)).print()

    print()
    return failures


def _scan_recent_errors(log_path: Path):
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-200:]
    except OSError:
        return []
    return [line for line in tail if " ERROR " in line or " CRITICAL " in line]
