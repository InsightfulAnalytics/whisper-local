import logging
import shutil
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

from .platform import foreground
from .utils import get_user_app_data_path, resolve_asset_path

USER_FILE = "app_rules.yaml"
DEFAULTS_FILE = "app_rules.defaults.yaml"


class AppRules:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rules: list = []
        self._mtime = 0.0
        self._path: Optional[Path] = None
        self._load()

    def _load(self):
        user_path = Path(get_user_app_data_path()) / USER_FILE
        if not user_path.exists():
            defaults = Path(resolve_asset_path(DEFAULTS_FILE))
            if defaults.exists():
                shutil.copy2(defaults, user_path)

        if not user_path.exists():
            return

        self._path = user_path
        self._reload_from_disk()

    def _reload_from_disk(self):
        if not self._path:
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = YAML().load(f) or {}
            self.rules = data.get("rules", []) or []
            self._mtime = self._path.stat().st_mtime
        except Exception as e:
            self.logger.error(f"Failed to load {self._path}: {e}")

    def _reload_if_changed(self):
        if not self._path:
            return
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return
        if mtime > self._mtime:
            self.logger.info(f"Reloading {self._path}")
            self._reload_from_disk()

    def match_for_foreground(self) -> Optional[dict]:
        self._reload_if_changed()
        if not self.rules:
            return None
        info = foreground.get_foreground_app()
        if not info:
            return None
        exe = info.get('exe', '').lower()
        title = info.get('title', '').lower()
        if not exe and not title:
            return None
        for rule in self.rules:
            if self._matches(rule, exe, title):
                return rule
        return None

    def _matches(self, rule: dict, exe: str, title: str) -> bool:
        patterns = rule.get('match')
        if isinstance(patterns, str):
            patterns = [patterns]
        if not patterns:
            return False
        for pattern in patterns:
            p = str(pattern).lower()
            if p and (p in exe or p in title):
                return True
        return False
