import logging
import os
import re
import shutil
import subprocess
from typing import Optional

import pyperclip
from ruamel.yaml import YAML

from .utils import resolve_asset_path, get_user_app_data_path
from .platform import keyboard

RISKY_PATTERNS = re.compile(
    r'\b(rm\s+-r|del\s+/[sq]|format\s+\w:|shutdown|reg\s+delete|sudo|takeown|del\s+/f)\b'
    r'|>(?!\s*null)|\|\s*(out-file|tee)\b',
    flags=re.IGNORECASE,
)


class VoiceCommandManager:
    def __init__(self, enabled=True, clipboard_manager=None, log_transcriptions=False):
        self.enabled = enabled
        self.clipboard_manager = clipboard_manager
        self.log_transcriptions = log_transcriptions
        self.logger = logging.getLogger(__name__)

        if not self.enabled:
            self.logger.info("Voice commands disabled by configuration")
            return

        defaults_path = resolve_asset_path("commands.defaults.yaml")
        user_path = os.path.join(get_user_app_data_path(), "commands.yaml")

        if not os.path.exists(user_path):
            shutil.copy2(defaults_path, user_path)
            self.logger.info(f"Created user commands file from defaults: {user_path}")

        yaml = YAML()
        try:
            with open(user_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
        except Exception as e:
            self.logger.error(f"Failed to parse {user_path}: {e}")
            raise

        self.commands_path = user_path
        self._commands_mtime = self._read_mtime()
        raw_commands = data.get('commands', []) if data else []
        self.commands = self._validate_commands(raw_commands)
        self.commands.sort(key=lambda cmd: len(cmd.get('trigger', '')), reverse=True)
        self.logger.info(f"Loaded {len(self.commands)} voice commands")

    def _validate_commands(self, raw_commands: list) -> list:
        valid = []
        for i, cmd in enumerate(raw_commands):
            trigger = cmd.get('trigger', '')
            has_match = bool(trigger or cmd.get('match_regex'))
            action_count = sum(1 for key in ('run', 'hotkey', 'type') if key in cmd)

            if not has_match:
                self.logger.warning(f"Command {i}: missing trigger and match_regex, skipping")
                continue

            if action_count != 1:
                self.logger.warning(f"Command '{trigger}': needs exactly one of 'run', 'hotkey', or 'type', skipping")
                continue

            valid.append(cmd)
        return valid

    def match_command(self, text: str) -> Optional[dict]:
        self._reload_if_changed()
        normalized = re.sub(r'[^\w\s]', '', text.lower()).strip()

        for command in self.commands:
            trigger = command.get('trigger', '').lower()
            regex_pattern = command.get('match_regex')

            if regex_pattern:
                try:
                    if re.search(regex_pattern, text, flags=re.IGNORECASE):
                        return command
                except re.error as e:
                    self.logger.warning(f"Invalid regex in command '{trigger}': {e}")
                    continue

            if trigger and trigger in normalized:
                return command

        return None

    def _expand_template(self, value: str) -> str:
        if not value or '${' not in value:
            return value
        try:
            clipboard_text = pyperclip.paste() or ''
        except Exception:
            clipboard_text = ''
        value = value.replace('${clipboard}', clipboard_text)
        value = value.replace('${selection}', clipboard_text)
        return value

    def _read_mtime(self) -> float:
        try:
            return os.path.getmtime(self.commands_path)
        except OSError:
            return 0.0

    def _reload_if_changed(self):
        if not getattr(self, 'commands_path', None):
            return
        current_mtime = self._read_mtime()
        if current_mtime <= self._commands_mtime:
            return

        self.logger.info(f"Detected change to {self.commands_path}, reloading commands")
        try:
            yaml = YAML()
            with open(self.commands_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
            raw = data.get('commands', []) if data else []
            new_commands = self._validate_commands(raw)
            new_commands.sort(key=lambda cmd: len(cmd.get('trigger', '')), reverse=True)
            self.commands = new_commands
            self._commands_mtime = current_mtime
            self.logger.info(f"Reloaded {len(self.commands)} voice commands")
            print(f"   🔄 Reloaded {len(self.commands)} voice commands from commands.yaml")
        except Exception as e:
            self.logger.error(f"Failed to reload commands: {e}")
            print(f"   ⚠ Failed to reload commands.yaml: {e}")

    def execute_command(self, command: dict, use_auto_enter: bool = False):
        trigger = command.get('trigger', '')

        if 'run' in command:
            self._execute_shell(self._expand_template(command['run']), trigger,
                                 require_confirm=command.get('confirm', None))
        elif 'hotkey' in command:
            self._send_hotkey(command['hotkey'], trigger)
        elif 'type' in command:
            self._deliver_text(self._expand_template(command['type']), trigger, use_auto_enter)

    def _execute_shell(self, run_str: str, trigger: str, require_confirm: Optional[bool] = None):
        is_risky = bool(RISKY_PATTERNS.search(run_str))
        needs_confirm = require_confirm if require_confirm is not None else is_risky
        if needs_confirm and not self._confirm_risky_command(trigger, run_str):
            self.logger.info(f"User declined risky command '{trigger}'")
            print(f"   ✗ Cancelled: {trigger}")
            return

        try:
            subprocess.Popen(run_str, shell=True)
            self.logger.info(f"Executed command '{trigger}': {run_str}")
            print(f"   Executed: {trigger}")
        except Exception as e:
            self.logger.error(f"Failed to execute command '{trigger}': {e}")
            print(f"   Failed to execute command: {e}")

    def _confirm_risky_command(self, trigger: str, run_str: str) -> bool:
        if os.name == 'nt':
            try:
                import ctypes
                MB_YESNO = 0x4
                MB_ICONWARNING = 0x30
                MB_DEFBUTTON2 = 0x100
                IDYES = 6
                result = ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Voice command '{trigger}' would run:\n\n{run_str}\n\nProceed?",
                    "Whisper Local — Confirm command",
                    MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2,
                )
                return result == IDYES
            except Exception as e:
                self.logger.error(f"Could not show confirm dialog: {e}")
                return False
        return True

    def _send_hotkey(self, hotkey_str: str, trigger: str):
        keys = [k.strip() for k in hotkey_str.lower().split('+')]
        try:
            keyboard.send_hotkey(*keys)
            self.logger.info(f"Sent hotkey '{trigger}': {hotkey_str}")
            print(f"   ✓ Sent hotkey: {trigger} [{hotkey_str}]")
        except Exception as e:
            self.logger.error(f"Failed to send hotkey '{trigger}': {e}")
            print(f"   Failed to send hotkey: {e}")

    def _deliver_text(self, text: str, trigger: str, use_auto_enter: bool = False):
        try:
            if self.clipboard_manager:
                self.clipboard_manager.deliver_transcription(text, use_auto_enter)
                if self.log_transcriptions:
                    self.logger.info(f"Delivered text '{trigger}': {text}")
                else:
                    self.logger.info(f"Delivered text for '{trigger}'")
                print(f"   ✓ Typed: {text}")
            else:
                self.logger.error("No clipboard manager available for type command")
                print(f"   Failed: clipboard manager not available")
        except Exception as e:
            self.logger.error(f"Failed to deliver text '{trigger}': {e}")
            print(f"   Failed to deliver text: {e}")
