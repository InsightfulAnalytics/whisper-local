# Package initialisation for Whisper Local.
#
# Exactly one thing happens here, and it has to happen before any other module
# gets the chance to print: making stdout and stderr able to carry the non-ASCII
# status glyphs used throughout the console output. Doing it at package level
# rather than in main() means it also covers the entry points that never reach
# main - the test suite, --serve, and anything importing a single module.

from .utils import ensure_utf8_console

ensure_utf8_console()
