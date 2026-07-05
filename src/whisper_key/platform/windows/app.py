import msvcrt
import os


# ctranslate2 wheels are built with MSVC 17.10+, whose std::mutex layout needs
# msvcp140.dll >= 14.40. Older runtimes (common on aging Windows 10 installs)
# access-violate the whole process at model load with NO Python traceback —
# the console just vanishes (Event Viewer: MSVCP140.dll, 0xc0000005). Checking
# the DLL version up front is the only way to give the user an actionable
# message instead of a disappearing window. Root-caused from a field crash
# on 2026-07-06 (msvcp140.dll 14.29 vs required 14.40+).
_MSVC_MIN_VERSION = (14, 40)
_VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


# Returns (detail, warning): human-readable runtime version, plus an
# actionable warning string when the runtime is missing/too old (else None).
def native_runtime_status():
    dll_path = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'),
                            'System32', 'msvcp140.dll')
    try:
        if not os.path.exists(dll_path):
            return ("msvcp140.dll missing",
                    "The Microsoft Visual C++ runtime (msvcp140.dll) is not installed. "
                    f"The Whisper engine cannot run without it. Fix: install {_VC_REDIST_URL} "
                    "and relaunch.")
        import win32api
        info = win32api.GetFileVersionInfo(dll_path, '\\')
        major = info['FileVersionMS'] >> 16
        minor = info['FileVersionMS'] & 0xFFFF
        detail = f"msvcp140.dll {major}.{minor}"
        if (major, minor) < _MSVC_MIN_VERSION:
            need = f"{_MSVC_MIN_VERSION[0]}.{_MSVC_MIN_VERSION[1]}"
            return (detail,
                    f"Your Microsoft Visual C++ runtime is too old ({detail}; need >= {need}). "
                    "Loading the Whisper engine will CRASH the app with no error message. "
                    f"Fix: install {_VC_REDIST_URL} (2 minutes, needs admin) and relaunch.")
        return (detail, None)
    except Exception:
        # Diagnostics must never block startup — assume OK when unreadable.
        return ("msvcp140.dll (version unreadable)", None)


def setup():
    pass

def run_event_loop(shutdown_event):
    while not shutdown_event.wait(timeout=0.1):
        pass

def getch():
    return msvcrt.getwch()
