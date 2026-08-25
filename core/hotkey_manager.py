"""
Velodictum - Multi-Key Combination Hotkey Manager & Registry
Supports single keys and multi-key combinations of up to 3 keys simultaneously
(e.g., 'ctrl+alt+space', 'ctrl+alt+z', 'ctrl+shift+d', 'f8', 'caps_lock') with strict debouncing
and multi-action registration.
"""
import threading
import time
from typing import Callable, Dict, List, Optional, Set
from pynput import keyboard


class HotkeyBinding:
    def __init__(
        self,
        name: str,
        combo_str: str,
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
        mode: str = "press_once",  # "push_to_talk", "toggle", "press_once"
    ):
        self.name = name
        self.combo_str = combo_str.lower().strip()
        self.target_keys = HotkeyManager.parse_combo(self.combo_str)
        self.on_press = on_press
        self.on_release = on_release
        self.mode = mode
        self.is_active = False
        self.last_trigger_time = 0.0


class HotkeyManager:
    def __init__(
        self,
        hotkey_name: str = "f8",
        mode: str = "push_to_talk",
        on_start_recording: Optional[Callable[[], None]] = None,
        on_stop_recording: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: Set[str] = set()
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._lock = threading.Lock()
        self.on_cancel = on_cancel

        # Primary dictation binding (backward-compatible)
        self.primary_name = "primary_dictate"
        self.register_hotkey(
            name=self.primary_name,
            combo_str=hotkey_name,
            on_press=on_start_recording,
            on_release=on_stop_recording,
            mode=mode,
        )

    @property
    def hotkey_name(self) -> str:
        with self._lock:
            binding = self._bindings.get(self.primary_name)
            return binding.combo_str if binding else "f8"

    @hotkey_name.setter
    def hotkey_name(self, value: str):
        self.set_hotkey(value)

    @property
    def mode(self) -> str:
        with self._lock:
            binding = self._bindings.get(self.primary_name)
            return binding.mode if binding else "push_to_talk"

    @mode.setter
    def mode(self, value: str):
        with self._lock:
            if self.primary_name in self._bindings:
                self._bindings[self.primary_name].mode = value

    @property
    def on_start_recording(self):
        with self._lock:
            binding = self._bindings.get(self.primary_name)
            return binding.on_press if binding else None

    @on_start_recording.setter
    def on_start_recording(self, val):
        with self._lock:
            if self.primary_name in self._bindings:
                self._bindings[self.primary_name].on_press = val

    @property
    def on_stop_recording(self):
        with self._lock:
            binding = self._bindings.get(self.primary_name)
            return binding.on_release if binding else None

    @on_stop_recording.setter
    def on_stop_recording(self, val):
        with self._lock:
            if self.primary_name in self._bindings:
                self._bindings[self.primary_name].on_release = val

    def register_hotkey(
        self,
        name: str,
        combo_str: str,
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
        mode: str = "press_once",
    ):
        """Register or update a named hotkey binding."""
        with self._lock:
            binding = HotkeyBinding(
                name=name,
                combo_str=combo_str,
                on_press=on_press,
                on_release=on_release,
                mode=mode,
            )
            self._bindings[name] = binding

    def unregister_hotkey(self, name: str):
        """Unregister a named hotkey binding."""
        with self._lock:
            self._bindings.pop(name, None)

    def reset_all_states(self):
        """Reset active state and pressed keys on all registered bindings."""
        with self._lock:
            self._pressed_keys.clear()
            for b in self._bindings.values():
                b.is_active = False

    def set_hotkey(self, hotkey_str: str):
        """Update primary dictation hotkey combination on the fly."""
        with self._lock:
            if self.primary_name in self._bindings:
                b = self._bindings[self.primary_name]
                b.combo_str = hotkey_str.lower().strip()
                b.target_keys = self.parse_combo(b.combo_str)
                b.is_active = False

    def set_hotkey_combo(self, name: str, hotkey_str: str):
        """Update a specific named hotkey combination on the fly."""
        with self._lock:
            if name in self._bindings:
                b = self._bindings[name]
                b.combo_str = hotkey_str.lower().strip()
                b.target_keys = self.parse_combo(b.combo_str)
                b.is_active = False

    @staticmethod
    def parse_combo(combo_str: str) -> List[str]:
        """Split combo string like 'ctrl+shift+space' into normalized list."""
        raw_parts = [p.strip().lower() for p in combo_str.replace(" ", "+").split("+") if p.strip()]
        normalized = []
        for p in raw_parts:
            if p in ("control", "strg"):
                normalized.append("ctrl")
            elif p in ("alternate", "option"):
                normalized.append("alt")
            elif p in ("windows", "super", "win"):
                normalized.append("cmd")
            else:
                normalized.append(p)
        return normalized if normalized else ["f8"]

    @staticmethod
    def canonical_key_name(key) -> str:
        """Convert pynput Key object to standard canonical string."""
        if hasattr(key, "name") and key.name is not None:
            name = key.name.lower()
            if name in ("ctrl_l", "ctrl_r"):
                return "ctrl"
            if name in ("alt_l", "alt_r", "alt_gr"):
                return "alt"
            if name in ("shift_l", "shift_r"):
                return "shift"
            if name in ("cmd_l", "cmd_r"):
                return "cmd"
            if name == "space":
                return "space"
            return name

        vk = getattr(key, "vk", None)
        if vk is not None:
            if 65 <= vk <= 90:
                return chr(vk).lower()
            if 48 <= vk <= 57:
                return chr(vk)
            if 96 <= vk <= 105:
                return str(vk - 96)
            if 112 <= vk <= 123:
                return f"f{vk - 111}"
            if vk == 32:
                return "space"
            if vk == 13:
                return "enter"
            if vk == 27:
                return "esc"
            if vk == 9:
                return "tab"
            if vk == 8:
                return "backspace"
            if vk == 20:
                return "caps_lock"

        char = getattr(key, "char", None)
        if char is not None:
            # Handle ASCII control characters produced when Ctrl is pressed (Ctrl+A=1..Ctrl+Z=26)
            if len(char) == 1 and 1 <= ord(char) <= 26:
                return chr(ord(char) + 96)
            return char.lower()

        return str(key).lower()

    def _is_combo_match(self, target_keys: List[str]) -> bool:
        if not target_keys:
            return False
        return all(k in self._pressed_keys for k in target_keys)

    def _on_press(self, key):
        canonical = self.canonical_key_name(key)

        # Immediate Escape key cancellation
        if canonical in ("esc", "key.esc") and self.on_cancel:
            threading.Thread(target=self.on_cancel, daemon=True).start()

        with self._lock:
            self._pressed_keys.add(canonical)
            now = time.perf_counter()

            for binding in list(self._bindings.values()):
                if self._is_combo_match(binding.target_keys):
                    if binding.mode == "push_to_talk":
                        if not binding.is_active or (now - binding.last_trigger_time > 0.12):
                            binding.is_active = True
                            binding.last_trigger_time = now
                            if binding.on_press:
                                threading.Thread(target=binding.on_press, daemon=True).start()

                    elif binding.mode == "toggle":
                        if now - binding.last_trigger_time > 0.15:
                            binding.last_trigger_time = now
                            if not binding.is_active:
                                binding.is_active = True
                                if binding.on_press:
                                    threading.Thread(target=binding.on_press, daemon=True).start()
                            else:
                                binding.is_active = False
                                if binding.on_release:
                                    threading.Thread(target=binding.on_release, daemon=True).start()

                    elif binding.mode == "press_once":
                        if not binding.is_active or (now - binding.last_trigger_time > 0.18):
                            binding.is_active = True
                            binding.last_trigger_time = now
                            if binding.on_press:
                                threading.Thread(target=binding.on_press, daemon=True).start()

    def _on_release(self, key):
        canonical = self.canonical_key_name(key)
        with self._lock:
            self._pressed_keys.discard(canonical)
            now = time.perf_counter()

            for binding in list(self._bindings.values()):
                if not self._is_combo_match(binding.target_keys):
                    if binding.mode == "push_to_talk":
                        if binding.is_active:
                            binding.is_active = False
                            binding.last_trigger_time = now
                            if binding.on_release:
                                threading.Thread(target=binding.on_release, daemon=True).start()
                    elif binding.mode == "press_once":
                        binding.is_active = False

    def start(self):
        """Start listening for global key events."""
        if self._listener is None:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

    def stop(self):
        """Stop listening for global key events."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
