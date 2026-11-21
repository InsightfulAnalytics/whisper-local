# gpu.py (Linux)
# GPU check for first-run onboarding. NVIDIA only: ctranslate2's Linux wheels
# are CUDA builds, and they need CUDA 12's cuBLAS, which the nvidia-cublas-cu12
# wheel supplies (whisper_engine preloads it from site-packages).

import ctypes
import logging
import subprocess

logger = logging.getLogger(__name__)


def detect_and_print(configured_device):
    gpu_name = _detect_nvidia_gpu()
    if not gpu_name:
        return (None, None, False)

    _status("🖥️ System check...")
    _status(f"   ✓ Detected {gpu_name}")

    ct2_works = _test_ct2_cuda()
    if ct2_works:
        _status("   ✓ GPU acceleration available")
    else:
        _status("   ✗ CUDA 12 cuBLAS not found: install nvidia-cublas-cu12 into the app's environment")

    return ('nvidia', gpu_name, ct2_works)


def _status(message: str):
    print(message)
    logger.debug(message.strip())


def _detect_nvidia_gpu():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                capture_output=True, text=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().splitlines()[0].strip()
    return None


# ctranslate2 sees the device through the driver alone; inference also needs
# libcublas.so.12, so check both (importing whisper_engine runs the preload).
def _test_ct2_cuda() -> bool:
    try:
        from ... import whisper_engine  # noqa: F401
        import ctranslate2
        if ctranslate2.get_cuda_device_count() < 1:
            return False
        ctypes.CDLL('libcublas.so.12')
        return True
    except Exception as e:
        logger.debug(f"CUDA check failed: {e}")
        return False
