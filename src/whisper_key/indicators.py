# indicators.py
# Fans each recording-indicator call (show_recording, show_processing, hide,
# flash_success, ...) out to every indicator in use: the floating level pill
# and the window glow. StateManager drives them all through one handle, and an
# indicator without a given method (the glow has no set_position) is skipped.

import logging

logger = logging.getLogger(__name__)


class RecordingIndicators:
    def __init__(self, members):
        self.members = list(members)

    def __bool__(self):
        return bool(self.members)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        def call_each(*args, **kwargs):
            for member in self.members:
                method = getattr(member, name, None)
                if not callable(method):
                    continue
                try:
                    method(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"{type(member).__name__}.{name} failed: {e}")
        return call_each
