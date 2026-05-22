import logging

import numpy as np

logger = logging.getLogger(__name__)


def apply_noise_reduction(audio: np.ndarray, sample_rate: int, strength: float = 0.75) -> np.ndarray:
    try:
        import noisereduce as nr
        flat = audio.flatten()
        reduced = nr.reduce_noise(y=flat, sr=sample_rate, prop_decrease=float(strength))
        return reduced.reshape(audio.shape).astype(np.float32)
    except ImportError:
        logger.debug("noisereduce not installed; skipping. Install: pip install 'whisper-local[noise]'")
        return audio
    except Exception as e:
        logger.warning(f"Noise reduction failed: {e}")
        return audio
