# noise_suppression.py
# Optional spectral-gating noise reduction applied to recorded audio before it
# reaches Whisper. Wraps the `noisereduce` library, which is itself a wrapper
# around librosa's spectral subtraction. Off by default — enable via
# `audio.noise_suppression.enabled: true` and `pip install noisereduce`.
# Falls back to passthrough silently when the library isn't installed.

import logging

import numpy as np

logger = logging.getLogger(__name__)


# Returns the noise-reduced array on success, the original array on any failure
# (missing library, processing error, etc.). Never raises — noise reduction is
# strictly opt-in polish, never required for correct transcription.
def apply_noise_reduction(audio: np.ndarray, sample_rate: int, strength: float = 0.75) -> np.ndarray:
    try:
        import noisereduce as nr
        flat = audio.flatten()
        reduced = nr.reduce_noise(y=flat, sr=sample_rate, prop_decrease=float(strength))
        return reduced.reshape(audio.shape).astype(np.float32)
    except ImportError:
        logger.debug("noisereduce not installed; skipping. Install: pip install noisereduce")
        return audio
    except Exception as e:
        logger.warning(f"Noise reduction failed: {e}")
        return audio
