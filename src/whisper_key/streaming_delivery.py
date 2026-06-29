# streaming_delivery.py
# Commit-on-endpoint streaming delivery (opt-in: streaming.deliver_to_cursor).
#
# When real-time streaming is on, finalized phrases (post-endpoint) are typed to
# the cursor AS the user speaks — the "feels like Wispr Flow" effect — instead of
# waiting for the full Whisper pass at stop. Only FINALIZED segments are delivered
# (never the revising partials), so the document never sees a word typed then
# corrected.
#
# Delivery happens on a dedicated worker thread fed by a queue: the audio callback
# (which produces segments) must never block on keyboard/clipboard I/O, and
# segments must be typed in the order they finalized. stop() drains and joins, so
# the caller knows all text has landed before it sends Enter or records history.

import logging
import queue
import threading

logger = logging.getLogger(__name__)


class StreamingDelivery:
    def __init__(self, deliver_fn):
        # deliver_fn(segment_text) performs the actual cursor insertion
        # (wraps ClipboardManager). Called only on the worker thread.
        self._deliver_fn = deliver_fn
        self._queue: "queue.Queue | None" = None
        self._worker = None
        self._delivered_text = ''
        self._submitted_any = False
        self._had_failure = False
        self._active = False
        # Serializes the _active flag + queue ops between the audio thread
        # (submit_final) and the main thread (stop), so a phrase finalized at the
        # exact stop instant can't be enqueued after the stop sentinel and dropped.
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            self._queue = queue.Queue()
            self._delivered_text = ''
            self._submitted_any = False
            self._had_failure = False
            self._active = True
        self._worker = threading.Thread(target=self._run, daemon=True, name='streaming-delivery')
        self._worker.start()

    def _run(self):
        while True:
            item = self._queue.get()
            if item is None:  # sentinel → drain complete, exit
                break
            try:
                self._deliver_fn(item)
                with self._lock:
                    self._delivered_text += item
            except Exception:
                logger.exception("Streaming segment delivery failed")
                with self._lock:
                    self._had_failure = True

    # Enqueue a finalized phrase for delivery. Fast + non-blocking: safe to call
    # from the audio callback thread. Tracks submission synchronously so the
    # pipeline can decide (at stop) whether streaming handled this recording.
    def submit_final(self, text: str):
        segment = (text or '').strip()
        if not segment:
            return
        with self._lock:
            if not self._active or self._queue is None:
                return
            self._submitted_any = True
            self._queue.put(segment + ' ')

    @property
    def submitted_any(self) -> bool:
        with self._lock:
            return self._submitted_any

    # True if any segment's delivery raised. The pipeline warns the user rather
    # than re-running Whisper (which would duplicate the text already typed).
    @property
    def had_failure(self) -> bool:
        with self._lock:
            return self._had_failure

    # Stop accepting segments, wait for the worker to deliver everything queued,
    # and return the full delivered text (for history/stats). Idempotent.
    def stop(self) -> str:
        with self._lock:
            if not self._active:
                return self._delivered_text.strip()
            self._active = False
            if self._queue is not None:
                self._queue.put(None)
        if self._worker is not None:
            self._worker.join(timeout=5.0)
        with self._lock:
            return self._delivered_text.strip()
