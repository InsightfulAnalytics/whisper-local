import logging
import os
import signal
from typing import Optional, TYPE_CHECKING
from pathlib import Path

from .utils import open_file
from .platform import permissions, icons, console

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None
    Image = None

if TYPE_CHECKING:
    from .state_manager import StateManager
    from .config_manager import ConfigManager

class SystemTray:
    def __init__(self,
                 state_manager: 'StateManager',
                 tray_config: dict = None,
                 config_manager: Optional['ConfigManager'] = None,
                 model_registry = None,
                 console_config: dict = None):

        self.state_manager = state_manager
        self.tray_config = tray_config or {}
        self.config_manager = config_manager
        self.model_registry = model_registry
        self.console_config = console_config or {}
        self.logger = logging.getLogger(__name__)
               
        self.icon = None  # pystray object, holds menu, state, etc.
        self.is_running = False
        self.current_state = "idle"
        self.available = True
        
        if self._check_tray_availability():
            self._load_icons_to_cache()
    
    def _check_tray_availability(self) -> bool:
        if not self.tray_config['enabled']:
            self.logger.warning("   ✗ System tray disabled in configuration")
            self.available = False

        elif not TRAY_AVAILABLE:
            self.logger.warning("   ✗ System tray not available - pystray or Pillow not installed")
            self.available = False

        return self.available

    def _load_icons_to_cache(self):
        try:
            self.icons = icons.get_tray_icons()
        except Exception as e:
            self.logger.error(f"Failed to load tray icons: {e}")
            self.icons = {
                "idle": self._create_fallback_icon("idle"),
                "recording": self._create_fallback_icon("recording"),
                "processing": self._create_fallback_icon("processing"),
            }
        
    def _create_fallback_icon(self, state: str) -> Image.Image:
        colors = {
            'idle': (128, 128, 128),      # Gray
            'recording': (34, 139, 34),   # Green  
            'processing': (255, 165, 0)   # Orange
        }
        
        color = colors.get(state, (128, 128, 128))  # Default to gray
        icon = Image.new('RGBA', (16, 16), color + (255,))

        return icon
    
    def _build_model_menu_items(self, current_model: str, is_model_loading: bool) -> list:
        items = []

        if not self.model_registry:
            return items

        def make_model_selector(model_key):
            return lambda icon, item: self._select_model(model_key)

        def make_is_current(model_key):
            return lambda item: model_key == current_model

        def model_selection_enabled(item):
            return not is_model_loading

        first_group = True
        for group in self.model_registry.get_groups_ordered():
            models = self.model_registry.get_models_by_group(group)
            if not models:
                continue

            if not first_group:
                items.append(pystray.Menu.SEPARATOR)
            first_group = False

            for model in models:
                items.append(pystray.MenuItem(
                    model.label,
                    make_model_selector(model.key),
                    radio=True,
                    checked=make_is_current(model.key),
                    enabled=model_selection_enabled
                ))

        return items

    LANGUAGES = [
        ('auto', 'Auto-detect'), ('en', 'English'), ('es', 'Spanish'),
        ('fr', 'French'), ('de', 'German'), ('it', 'Italian'),
        ('pt', 'Portuguese'), ('nl', 'Dutch'), ('pl', 'Polish'),
        ('ru', 'Russian'), ('ja', 'Japanese'), ('zh', 'Chinese'),
        ('ko', 'Korean'), ('hi', 'Hindi'), ('ar', 'Arabic'),
    ]

    def _build_language_menu(self):
        try:
            current = self.state_manager.get_current_language()
        except Exception:
            current = 'auto'

        def make_setter(code):
            return lambda icon, item: self.state_manager.set_language(code)

        def make_is_current(code):
            return lambda item: current == code

        return [
            pystray.MenuItem(label, make_setter(code), radio=True, checked=make_is_current(code))
            for code, label in self.LANGUAGES
        ]

    OVERLAY_POSITIONS = [
        ('bottom-center', 'Bottom Center'),
        ('bottom-right', 'Bottom Right'),
        ('bottom-left', 'Bottom Left'),
        ('top-center', 'Top Center'),
        ('top-right', 'Top Right'),
        ('top-left', 'Top Left'),
    ]

    def _build_overlay_menu(self):
        try:
            current = self.state_manager.get_overlay_position()
        except Exception:
            current = 'bottom-center'

        def make_setter(pos):
            return lambda icon, item: self.state_manager.set_overlay_position(pos)

        def make_is_current(pos):
            return lambda item: current == pos

        return [
            pystray.MenuItem(label, make_setter(pos), radio=True, checked=make_is_current(pos))
            for pos, label in self.OVERLAY_POSITIONS
        ]

    def _build_transforms_menu(self):
        try:
            transforms = self.state_manager.list_transforms()
        except Exception:
            return []
        if not transforms:
            return []

        def make_activator(name):
            return lambda icon, item: self.state_manager.apply_transform(name)

        items = []
        for t in transforms:
            name = t.get('name') or '?'
            hotkey = t.get('hotkey')
            label = name.title()
            if hotkey:
                label = f"{label}  ({hotkey.upper()})"
            items.append(pystray.MenuItem(label, make_activator(name)))
        return items

    def _build_profile_menu(self):
        try:
            profiles = self.state_manager.list_profiles()
            active = self.state_manager.get_active_profile()
        except Exception:
            return []
        if not profiles:
            return []

        def make_activator(name):
            return lambda icon, item: self.state_manager.activate_profile(name)

        def make_is_active(name):
            return lambda item: active == name

        return [
            pystray.MenuItem(name.title(), make_activator(name),
                             radio=True, checked=make_is_active(name))
            for name in profiles
        ]

    def _build_recent_transcriptions_menu(self):
        try:
            recent = self.state_manager.get_recent_transcriptions()
        except Exception:
            return []
        if not recent:
            return []

        def make_recopy(idx):
            return lambda icon, item: self.state_manager.recopy_recent_transcription(idx)

        items = []
        for i, text in enumerate(recent):
            label = text if len(text) <= 50 else text[:47] + "..."
            items.append(pystray.MenuItem(label, make_recopy(i)))
        return items

    def _create_menu(self):
        try:
            app_state = self.state_manager.get_application_state()
            is_model_loading = app_state.get('model_loading', False)

            auto_paste_enabled = self.config_manager.get_setting('clipboard', 'auto_paste')
            current_model = self.config_manager.get_setting('whisper', 'model')

            available_hosts = self.state_manager.get_available_audio_hosts()
            current_host = self.state_manager.get_current_audio_host()

            def is_current_host(host_name):
                return lambda item: current_host == host_name

            def switch_host(host_name):
                return lambda icon, item: self._select_audio_host(host_name)

            audio_host_items = []
            if available_hosts:
                for host in available_hosts:
                    host_name = host['name']
                    audio_host_items.append(
                        pystray.MenuItem(
                            host_name,
                            switch_host(host_name),
                            radio=True,
                            checked=is_current_host(host_name)
                        )
                    )

            available_devices = self.state_manager.get_available_audio_devices(current_host)
            current_device = self.state_manager.get_current_audio_device_id()

            def is_current_device(dev_id):
                return lambda item: current_device == dev_id

            def switch_device(dev_id, dev_name):
                return lambda icon, item: self._select_audio_device(dev_id, dev_name)

            audio_device_items = []

            if available_devices:
                for device in available_devices:
                    device_id = device['id']
                    device_name = device['name']

                    audio_device_items.append(
                        pystray.MenuItem(
                            device_name,
                            switch_device(device_id, device['name']),
                            radio=True,
                            checked=is_current_device(device_id)
                        )
                    )

            model_sub_menu_items = self._build_model_menu_items(current_model, is_model_loading)

            voice_commands_enabled = self.config_manager.get_setting('voice_commands', 'enabled')

            menu_items = []

            if console.owns_console():
                menu_items.append(pystray.MenuItem("Show Console", self._show_console, default=True))
                menu_items.append(pystray.Menu.SEPARATOR)

            menu_items += [
                pystray.MenuItem("Settings...", self._open_settings_window),
                pystray.MenuItem("Transcript history...", self._open_history_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Open log file...", self._open_log_file),
                pystray.MenuItem("Open model cache...", self._open_model_cache),
                pystray.MenuItem("Run diagnostics...", self._run_doctor_in_window),
                pystray.MenuItem("View stats...", self._run_stats_in_window),
                pystray.MenuItem("Add word to dictionary...", self._open_add_word_dialog),
                pystray.MenuItem("Edit hotwords / settings...", self._open_config_file),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Open config folder...", self._open_config_folder),
                pystray.MenuItem("Open settings file...", self._open_config_file),
                pystray.MenuItem("Open commands file...", self._open_commands_file) if voice_commands_enabled else None,
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Audio Host",
                    pystray.Menu(*audio_host_items)
                ) if audio_host_items else None,
                pystray.MenuItem(
                    f"Audio Source",
                    pystray.Menu(*audio_device_items)
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Auto-paste", lambda icon, item: self._set_transcription_mode(True), radio=True, checked=lambda item: auto_paste_enabled),
                pystray.MenuItem("Copy to clipboard", lambda icon, item: self._set_transcription_mode(False), radio=True, checked=lambda item: not auto_paste_enabled),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f"Model: {current_model.title()}", pystray.Menu(*model_sub_menu_items)),
                pystray.MenuItem(
                    f"Language: {self.state_manager.get_current_language()}",
                    pystray.Menu(*self._build_language_menu())
                ),
            ]

            profile_items = self._build_profile_menu()
            if profile_items:
                active_profile = self.state_manager.get_active_profile() or "—"
                menu_items.append(pystray.MenuItem(
                    f"Profile: {active_profile.title()}",
                    pystray.Menu(*profile_items)
                ))

            menu_items.append(pystray.MenuItem(
                "Overlay position",
                pystray.Menu(*self._build_overlay_menu())
            ))

            transform_items = self._build_transforms_menu()
            if transform_items:
                transform_items = list(transform_items) + [
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Edit transforms.yaml...", self._open_transforms_file),
                    pystray.MenuItem("Reload from file", self._reload_transforms),
                ]
                menu_items.append(pystray.MenuItem(
                    "Transforms",
                    pystray.Menu(*transform_items)
                ))

            recent_items = self._build_recent_transcriptions_menu()
            if recent_items:
                menu_items.append(pystray.Menu.SEPARATOR)
                menu_items.append(pystray.MenuItem("Recent", pystray.Menu(*recent_items)))

            menu_items.extend([
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._quit_application_from_tray)
            ])

            menu = pystray.Menu(*[item for item in menu_items if item is not None])

            return menu 
                
        except Exception as e:
            self.logger.error(f"Error in _create_menu: {e}")
            raise

    def _open_config_folder(self, icon=None, item=None):
        try:
            config_dir = os.path.dirname(self.config_manager.user_settings_path)
            open_file(config_dir)
        except Exception as e:
            self.logger.error(f"Failed to open config folder: {e}")

    def _open_config_file(self, icon=None, item=None):
        try:
            open_file(self.config_manager.user_settings_path)
        except Exception as e:
            self.logger.error(f"Failed to open config file: {e}")

    def _open_commands_file(self, icon=None, item=None):
        try:
            commands_path = os.path.join(
                os.path.dirname(self.config_manager.user_settings_path),
                "commands.yaml"
            )
            open_file(commands_path)
        except Exception as e:
            self.logger.error(f"Failed to open commands file: {e}")

    def _open_log_file(self, icon=None, item=None):
        try:
            log_path = self.config_manager.get_log_file_path()
            open_file(log_path)
        except Exception as e:
            self.logger.error(f"Failed to open log file: {e}")

    def _open_model_cache(self, icon=None, item=None):
        try:
            cache_path = self.model_registry.get_hf_cache_path()
            os.makedirs(cache_path, exist_ok=True)
            open_file(cache_path)
        except Exception as e:
            self.logger.error(f"Failed to open model cache: {e}")

    def _set_transcription_mode(self, auto_paste: bool):
        if auto_paste:
            if not permissions.check_accessibility_permission():
                if not permissions.handle_missing_permission(self.config_manager):
                    return
                auto_paste = False

        self.state_manager.update_transcription_mode(auto_paste)
        self.icon.menu = self._create_menu()

    def _select_model(self, model_key: str):
        try:
            success = self.state_manager.request_model_change(model_key)

            if success:
                self.config_manager.update_user_setting('whisper', 'model', model_key)
                self.icon.menu = self._create_menu()
            else:
                self.logger.warning(f"Request to change model to {model_key} was not accepted")

        except Exception as e:
            self.logger.error(f"Error selecting model {model_key}: {e}")

    def _select_audio_host(self, host_name: str):
        try:
            success = self.state_manager.set_audio_host(host_name)
            if success:
                self.icon.menu = self._create_menu()
            else:
                self.logger.warning(f"Request to change audio host to {host_name} was not accepted")
        except Exception as e:
            self.logger.error(f"Error selecting audio host {host_name}: {e}")

    def _select_audio_device(self, device_id: int, device_name: str):
        success = self.state_manager.request_audio_device_change(device_id, device_name)

        if success:
            self.config_manager.update_user_setting('audio', 'input_device', device_id)
            self.icon.menu = self._create_menu()
        else:
            self.logger.warning(f"Request to change audio device to {device_id} was not accepted")

    def _show_console(self, icon=None, item=None):
        console.show()

    def apply_console_settings(self):
        if not console.owns_console() or not self.available:
            return
        if self.console_config.get('start_hidden', False):
            console.hide()
        console.start_minimize_monitor(console.hide)

    def _quit_application_from_tray(self, icon=None, item=None):
        os.kill(os.getpid(), signal.SIGINT)

    def _run_doctor_in_window(self, icon=None, item=None):
        self._run_module_in_window('--doctor')

    def _run_stats_in_window(self, icon=None, item=None):
        self._run_module_in_window('--stats')

    def _open_settings_window(self, icon=None, item=None):
        self._run_module_in_window('--settings')

    def _open_history_window(self, icon=None, item=None):
        self._run_module_in_window('--history')

    def _open_add_word_dialog(self, icon=None, item=None):
        try:
            from .dictionary import show_add_word_dialog
            show_add_word_dialog()
        except Exception as e:
            self.logger.error(f"Failed to show add-word dialog: {e}")

    def _open_transforms_file(self, icon=None, item=None):
        try:
            from pathlib import Path
            from .utils import get_user_app_data_path
            path = Path(get_user_app_data_path()) / 'transforms.yaml'
            open_file(str(path))
        except Exception as e:
            self.logger.error(f"Failed to open transforms.yaml: {e}")

    def _reload_transforms(self, icon=None, item=None):
        try:
            changed = self.state_manager.reload_transforms()
            if not changed:
                self.notify("No changes to transforms.yaml")
        except Exception as e:
            self.logger.error(f"Failed to reload transforms: {e}")

    def _run_module_in_window(self, flag: str):
        import subprocess
        import sys
        try:
            subprocess.Popen(
                [sys.executable, '-m', 'whisper_key.main', flag],
                creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0)
            )
        except Exception as e:
            self.logger.error(f"Failed to launch {flag}: {e}")
    
    def notify(self, message: str, title: str = "Whisper Local"):
        if not TRAY_AVAILABLE or not self.is_running or not self.icon:
            return
        try:
            self.icon.notify(message, title)
        except Exception as e:
            self.logger.debug(f"Tray notify failed: {e}")

    def update_state(self, new_state: str):
        if not TRAY_AVAILABLE or not self.is_running:
            return

        self.current_state = new_state

        try:
            self.icon.icon = self.icons[new_state]
            self.icon.menu = self._create_menu()
        except Exception as e:
            self.logger.error(f"Failed to update tray icon: {e}")

        if new_state == "recording":
            self._start_level_monitor()
        else:
            self._stop_level_monitor()
            try:
                self.icon.title = self.tray_config.get('tooltip', 'Whisper Local')
            except Exception:
                pass

    def _start_level_monitor(self):
        import threading
        prev_thread = getattr(self, '_level_thread', None)
        if prev_thread and prev_thread.is_alive():
            prev_stop = getattr(self, '_level_stop', None)
            if prev_stop:
                prev_stop.set()
            prev_thread.join(timeout=0.3)
        self._level_stop = threading.Event()

        def loop():
            import time
            while not self._level_stop.is_set():
                try:
                    level = self.state_manager.audio_recorder.get_current_level()
                except Exception:
                    level = 0.0
                bars = self._level_bars(level)
                try:
                    if self.icon:
                        self.icon.title = f"Whisper Local · 🎤 {bars}"
                except Exception:
                    pass
                self._level_stop.wait(0.15)

        self._level_thread = threading.Thread(target=loop, daemon=True, name="tray-level")
        self._level_thread.start()

    def _stop_level_monitor(self):
        stop = getattr(self, '_level_stop', None)
        if stop:
            stop.set()

    def _level_bars(self, level: float) -> str:
        bins = ['░░░░░░', '█░░░░░', '██░░░░', '███░░░', '████░░', '█████░', '██████']
        scaled = min(int(level * 60), len(bins) - 1)
        return bins[scaled]

    def refresh_menu(self):
        if not self.icon:
            return

        try:
            self.icon.menu = self._create_menu()
        except Exception as e:
            self.logger.error(f"Failed to refresh tray menu: {e}")
    
    def start(self):
        if not self.available:
            return False

        if self.is_running:
            self.logger.warning("System tray is already running")
            return True

        try:
            idle_icon = self.icons.get("idle")
            menu = self._create_menu()

            self.icon = pystray.Icon(
                name="whisper-local",
                icon=idle_icon,
                title="Whisper Local",
                menu=menu
            )

            self.icon.run_detached()

            self.is_running = True
            print("   ✓ System tray icon is running...")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}")
            return False
    
    def stop(self):
        if not self.is_running:
            return

        try:
            self.icon.stop()
            self.is_running = False

        except Exception as e:
            self.logger.error(f"Error stopping system tray: {e}")
