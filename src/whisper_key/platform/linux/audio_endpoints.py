# audio_endpoints.py (Linux)
# No-op stub. The recorder opens PortAudio's "default" device, which PipeWire
# routes to whichever microphone is current, so a plugged-in microphone is
# picked up without reopening the stream. Stall detection still covers dropouts.


def capture_fingerprint():
    return None
