# local_server.py
# Local OpenAI-compatible Whisper API server. Started by `whisper-local --serve`.
# Implements the minimal subset of the OpenAI audio API that real-world tools
# (Cursor, Open WebUI, n8n, the openai Python SDK) actually call:
#
#   POST /v1/audio/transcriptions  — multipart upload, returns {text} or text
#   GET  /v1/models                — minimal model listing
#   GET  /health                   — liveness probe for tools that ping first
#
# Built on stdlib http.server so we don't add Flask/FastAPI as a hard dep.
# The multipart parser is hand-rolled to keep dependencies tight.

import io
import json
import logging
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

# Bound to loopback by default — this is a *local* tool and binding to 0.0.0.0
# would expose your Whisper model to the network. Override via --serve-host
# only if you understand the implications (e.g. a trusted LAN service).
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 7777

# Hard cap on request body size. Even bound to loopback, a buggy or hostile
# local client could send a huge Content-Length and exhaust memory, so we
# refuse anything larger than this before reading the body. 500 MB is far
# beyond any realistic audio upload (an hour of 16 kHz mono WAV is ~115 MB).
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


# Public entry point. Builds the Whisper engine once at startup (warm cache,
# fast subsequent transcriptions), then enters the http.server forever loop.
# Returns 1 on init/bind failure, 0 on graceful Ctrl+C shutdown.
def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    print("\n🌐 Whisper Local — local OpenAI-compatible API server")
    print("─" * 60)

    try:
        engine = _build_engine()
    except Exception as e:
        print(f"❌ Could not initialise Whisper engine: {e}")
        return 1

    handler_cls = _make_handler(engine)
    try:
        httpd = ThreadingHTTPServer((host, port), handler_cls)
    except OSError as e:
        print(f"❌ Could not bind {host}:{port} — {e}")
        return 1

    print(f"✅ Listening on http://{host}:{port}")
    print(f"   POST /v1/audio/transcriptions   — OpenAI-compatible Whisper endpoint")
    print(f"   GET  /v1/models                 — list available models")
    print(f"   GET  /health                    — liveness check")
    print("\n   Press Ctrl+C to stop.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n   Shutting down server…")
        httpd.shutdown()
    return 0


# Constructs the Whisper engine from the user's saved config. Reuses the same
# config + backend selection logic as the dictation app, so --serve always uses
# the same model the user chose for dictation. Disables VAD silence-timeout
# (server requests are bounded by the uploaded file, not silence).
def _build_engine():
    from .config_manager import ConfigManager
    from .model_registry import ModelRegistry
    from .voice_activity_detection import VadManager
    from .whisper_engine import WhisperEngine

    cm = ConfigManager(quiet=True)
    whisper_cfg = cm.get_whisper_config()
    vad_cfg = cm.get_vad_config()
    registry = ModelRegistry(
        whisper_models_config=whisper_cfg.get('models', {}),
        streaming_models_config={},
    )
    vad_manager = VadManager(
        vad_precheck_enabled=False, vad_realtime_enabled=False,
        vad_onset_threshold=vad_cfg.get('vad_onset_threshold', 0.5),
        vad_offset_threshold=vad_cfg.get('vad_offset_threshold', 0.5),
        vad_min_speech_duration=vad_cfg.get('vad_min_speech_duration', 0.1),
        vad_silence_timeout_seconds=999.0,
    )

    backend = whisper_cfg.get('backend', 'faster_whisper')
    if backend == 'whisper_cpp':
        from .whisper_engine_cpp import WhisperEngineCpp
        engine = WhisperEngineCpp(
            model_key=whisper_cfg['model'], device=whisper_cfg['device'],
            compute_type=whisper_cfg['compute_type'],
            language=whisper_cfg.get('language', 'auto'),
            beam_size=whisper_cfg.get('beam_size', 5),
            initial_prompt=whisper_cfg.get('initial_prompt', ''),
            hotwords=whisper_cfg.get('hotwords', []),
            task=whisper_cfg.get('task', 'transcribe'),
            vad_manager=vad_manager, model_registry=registry,
        )
    else:
        engine = WhisperEngine(
            model_key=whisper_cfg['model'], device=whisper_cfg['device'],
            compute_type=whisper_cfg['compute_type'],
            language=whisper_cfg.get('language', 'auto'),
            beam_size=whisper_cfg.get('beam_size', 5),
            initial_prompt=whisper_cfg.get('initial_prompt', ''),
            hotwords=whisper_cfg.get('hotwords', []),
            task=whisper_cfg.get('task', 'transcribe'),
            vad_manager=vad_manager, model_registry=registry,
        )
    print(f"   Backend = {backend}  ·  model = {whisper_cfg['model']}  ·  device = {whisper_cfg['device']}")
    return engine


# Factory that returns a per-server BaseHTTPRequestHandler subclass bound to
# our engine. We use a factory (not module-level globals) so multiple servers
# could in principle coexist with different configs.
def _make_handler(engine):

    # Single lock across requests — Whisper inference is single-threaded per
    # model instance, and serialising here gives predictable latency. If you
    # need parallel throughput, run multiple servers on different ports.
    transcribe_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):

        def log_message(self, fmt, *args):
            logger.debug(f"[server] {self.address_string()} {fmt % args}")

        def do_GET(self):
            if self.path.startswith('/health'):
                self._json(200, {'status': 'ok'})
            elif self.path.startswith('/v1/models'):
                self._json(200, {
                    'object': 'list',
                    'data': [{'id': 'whisper-1', 'object': 'model', 'owned_by': 'whisper-local'}],
                })
            else:
                self._json(404, {'error': {'message': 'Not found', 'type': 'not_found'}})

        def do_POST(self):
            if not self.path.startswith('/v1/audio/transcriptions'):
                self._json(404, {'error': {'message': 'Not found', 'type': 'not_found'}})
                return

            try:
                fields = _parse_multipart(self)
            except Exception as e:
                self._json(400, {'error': {'message': f'Bad multipart: {e}', 'type': 'invalid_request_error'}})
                return

            audio_bytes = fields.get('file', {}).get('data')
            if not audio_bytes:
                self._json(400, {'error': {'message': "Missing 'file' field", 'type': 'invalid_request_error'}})
                return

            response_format = (fields.get('response_format', {}).get('value') or 'json').lower()
            language = fields.get('language', {}).get('value')
            prompt = fields.get('prompt', {}).get('value') or ''

            try:
                audio_array = _decode_audio(audio_bytes)
            except Exception as e:
                self._json(400, {'error': {'message': f'Could not decode audio: {e}', 'type': 'invalid_request_error'}})
                return

            with transcribe_lock:
                old_lang = engine.language
                old_prompt = engine.initial_prompt
                try:
                    if language and language != 'auto':
                        engine.language = language
                    if prompt:
                        engine.initial_prompt = prompt
                    text = engine.transcribe_audio(audio_array) or ''
                finally:
                    engine.language = old_lang
                    engine.initial_prompt = old_prompt

            if response_format == 'text':
                self._text(200, text)
            else:
                self._json(200, {'text': text})

        def _json(self, status, payload):
            body = json.dumps(payload).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _text(self, status, body):
            data = (body or '').encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


# Hand-rolled multipart/form-data parser. The OpenAI Whisper API uploads always
# look like a few small text fields + one binary `file` field, so we don't need
# a streaming parser. Returns {field_name: {'value': str, 'data': bytes}}.
def _parse_multipart(handler):
    ctype = handler.headers.get('Content-Type', '')
    if 'multipart/form-data' not in ctype:
        raise ValueError('Expected multipart/form-data')

    boundary = None
    for part in ctype.split(';'):
        part = part.strip()
        if part.lower().startswith('boundary='):
            boundary = part.split('=', 1)[1].strip().strip('"')
            break
    if not boundary:
        raise ValueError('No boundary in Content-Type')

    length = int(handler.headers.get('Content-Length', '0'))
    if length > MAX_UPLOAD_BYTES:
        raise ValueError(
            f'Payload too large: {length} bytes exceeds the {MAX_UPLOAD_BYTES}-byte limit'
        )
    raw = handler.rfile.read(length)
    sep = b'--' + boundary.encode('latin-1')
    fields = {}

    for chunk in raw.split(sep):
        chunk = chunk.strip(b'\r\n')
        if not chunk or chunk == b'--':
            continue
        try:
            header_blob, _, body = chunk.partition(b'\r\n\r\n')
            headers = {}
            for line in header_blob.split(b'\r\n'):
                if b':' in line:
                    k, v = line.split(b':', 1)
                    headers[k.strip().lower().decode('latin-1', 'replace')] = v.strip().decode('latin-1', 'replace')
            disp = headers.get('content-disposition', '')
            name = None
            for piece in disp.split(';'):
                piece = piece.strip()
                if piece.startswith('name='):
                    name = piece.split('=', 1)[1].strip().strip('"')
                    break
            if not name:
                continue
            # Strip ONLY the trailing CRLF that separates the body from the next
            # boundary. Do NOT strip trailing '-' — split(sep) already isolated
            # this part, and the closing "--" lives in its own trailing chunk.
            # Stripping '-' here silently truncated binary audio ending in 0x2D.
            body = body[:-2] if body.endswith(b'\r\n') else body
            entry = {'value': body.decode('utf-8', 'replace'), 'data': body}
            fields[name] = entry
        except Exception:
            continue
    return fields


# Decode the uploaded audio bytes to a 16 kHz mono float32 numpy array (the
# format Whisper expects). Prefers `soundfile` (handles wav/flac/ogg/etc.), falls
# back to stdlib `wave` for plain WAV when soundfile isn't installed.
def _decode_audio(data: bytes):
    import numpy as np
    try:
        import soundfile as sf
        with io.BytesIO(data) as buf:
            audio, sr = sf.read(buf, dtype='float32', always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            try:
                import soxr
                audio = soxr.resample(audio, sr, 16000).astype(np.float32)
            except Exception:
                pass
        return audio.astype(np.float32)
    except ImportError:
        return _decode_wav_fallback(data)


# Pure-stdlib WAV decoder used when soundfile (libsndfile) isn't available.
# Handles 16-bit and 32-bit PCM mono/stereo WAVs — the realistic 99% case.
def _decode_wav_fallback(data: bytes):
    import numpy as np
    import wave
    with io.BytesIO(data) as buf:
        with wave.open(buf, 'rb') as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
    if sample_width == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)
    if sr != 16000:
        try:
            import soxr
            audio = soxr.resample(audio, sr, 16000).astype(np.float32)
        except Exception:
            pass
    return audio
