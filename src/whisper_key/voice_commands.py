import logging
import os
import re
import shutil
import subprocess
from typing import Optional

from ruamel.yaml import YAML

from .utils import resolve_asset_path, get_user_app_data_path
from .platform import keyboard


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
            action_count = sum(1 for key in ('run', 'hotkey', 'type') if key in cmd)

            if not trigger:
                self.logger.warning(f"Command {i}: missing trigger, skipping")
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
            if trigger and trigger in normalized:
                return command

        return None

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
            self._execute_shell(command['run'], trigger)
        elif 'hotkey' in command:
            self._send_hotkey(command['hotkey'], trigger)
        elif 'type' in command:
            self._deliver_text(command['type'], trigger, use_auto_enter)

    def _execute_shell(self, run_str: str, trigger: str):
        try:
            subprocess.Popen(run_str, shell=True)
            self.logger.info(f"Executed command '{trigger}': {run_str}")
            print(f"   Executed: {trigger}")
        except Exception as e:
            self.logger.error(f"Failed to execute command '{trigger}': {e}")
            print(f"   Failed to execute command: {e}")

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
