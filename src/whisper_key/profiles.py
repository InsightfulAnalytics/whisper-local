from pathlib import Path
from typing import Dict, List, Optional

from ruamel.yaml import YAML

from .utils import get_user_app_data_path, resolve_asset_path

PROFILES_FILE = "profiles.yaml"
PROFILES_DEFAULTS = "profiles.defaults.yaml"


class ProfileManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.profiles: Dict[str, dict] = {}
        self.active: Optional[str] = None
        self._load()

    def _load(self):
        user_path = Path(get_user_app_data_path()) / PROFILES_FILE
        if not user_path.exists():
            defaults = Path(resolve_asset_path(PROFILES_DEFAULTS))
            if defaults.exists():
                user_path.write_text(defaults.read_text(encoding="utf-8"), encoding="utf-8")

        if not user_path.exists():
            return

        try:
            with open(user_path, encoding="utf-8") as f:
                data = YAML().load(f) or {}
        except Exception:
            return

        self.profiles = data.get("profiles", {}) or {}
        self.active = data.get("active") or None

    def list_profiles(self) -> List[str]:
        return list(self.profiles.keys())

    def get_active(self) -> Optional[str]:
        return self.active

    def apply(self, name: str) -> bool:
        if name not in self.profiles:
            return False
        overrides = self.profiles[name].get("overrides", {})
        for section, values in overrides.items():
            if not isinstance(values, dict):
                continue
            for key, value in values.items():
                self.config_manager.update_user_setting(section, key, value)
        self.active = name
        self._persist_active()
        return True

    def _persist_active(self):
        path = Path(get_user_app_data_path()) / PROFILES_FILE
        if not path.exists():
            return
        try:
            yaml = YAML()
            with open(path, encoding="utf-8") as f:
                data = yaml.load(f) or {}
            data["active"] = self.active
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f)
        except Exception:
            pass
