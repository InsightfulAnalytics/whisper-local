import logging

logger = logging.getLogger(__name__)


def get_foreground_app() -> dict:
    try:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if not app:
            return {}
        return {
            'exe': (app.bundleIdentifier() or '').lower(),
            'path': str(app.bundleURL().path()) if app.bundleURL() else '',
            'title': app.localizedName() or '',
        }
    except Exception as e:
        logger.debug(f"Foreground app probe failed: {e}")
        return {}
