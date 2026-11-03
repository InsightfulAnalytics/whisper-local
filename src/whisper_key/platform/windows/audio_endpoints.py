# audio_endpoints.py (Windows)
# A cheap snapshot of which microphones Windows currently treats as active,
# read straight from the registry. The audio recorder polls it to notice a
# microphone being plugged in or removed without reinitialising PortAudio.

import winreg

_CAPTURE_ENDPOINTS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
_DEVICE_STATE_ACTIVE = 0x1
# DeviceState carries unrelated flags in its high bits; presence is the low nibble.
_DEVICE_STATE_MASK = 0xF


# Returns the IDs of all active capture endpoints, or None if the registry
# can't be read (callers then skip change detection rather than fail).
def capture_fingerprint():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _CAPTURE_ENDPOINTS_KEY) as endpoints:
            active_ids = set()
            index = 0
            while True:
                try:
                    endpoint_id = winreg.EnumKey(endpoints, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(endpoints, endpoint_id) as endpoint:
                        state, _ = winreg.QueryValueEx(endpoint, "DeviceState")
                except OSError:
                    continue
                if state & _DEVICE_STATE_MASK == _DEVICE_STATE_ACTIVE:
                    active_ids.add(endpoint_id)
            return frozenset(active_ids)
    except OSError:
        return None
