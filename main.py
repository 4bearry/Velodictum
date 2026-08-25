"""
Velodictum AI - Complete Windows Desktop Application
Push-to-Talk AI Dictation with The Flow Layer, Liquid Glass PyQt6 Dashboard, Floating HUD Pill, and System Tray.
"""
import sys
import os
import ctypes

# Register core package and project root on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.join(_PROJECT_ROOT, "core")
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(1, _PROJECT_ROOT)

# Early Win32 Binary Search Order Hardening (Mitigates DLL Preloading / Hijacking)

if sys.platform == "win32":
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetDllDirectoryW("")
        flags = 0x00001000 | 0x00000200 | 0x00000800  # DEFAULT_DIRS | APPLICATION_DIR | SYSTEM32
        try:
            kernel32.SetDefaultDllDirectories(flags)
        except Exception:
            pass
    except Exception:
        pass


def init_cuda_dll_paths():
    """Ensure NVIDIA CUDA/cuDNN DLL directories and system CUDA paths are registered with Windows."""
    # 1. Check if running inside PyInstaller bundle (_MEIPASS or dist/Velodictum)
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        if os.path.isdir(base_dir):
            try:
                os.add_dll_directory(base_dir)
            except Exception:
                pass
            os.environ["PATH"] = base_dir + os.pathsep + os.environ.get("PATH", "")
        internal_dir = os.path.join(os.path.dirname(sys.executable), "_internal")
        if os.path.isdir(internal_dir):
            try:
                os.add_dll_directory(internal_dir)
            except Exception:
                pass
            os.environ["PATH"] = internal_dir + os.pathsep + os.environ.get("PATH", "")

    # 2. Check site-packages/nvidia modules in venv
    try:
        import site
        site_dirs = []
        if hasattr(site, "getsitepackages"):
            site_dirs.extend(site.getsitepackages())
        if hasattr(site, "getusersitepackages"):
            site_dirs.append(site.getusersitepackages())
        
        py_dir = os.path.dirname(sys.executable)
        site_dirs.append(os.path.join(py_dir, "Lib", "site-packages"))
        site_dirs.append(os.path.join(os.path.dirname(py_dir), "Lib", "site-packages"))

        for s_dir in site_dirs:
            nvidia_dir = os.path.join(s_dir, "nvidia")
            if os.path.isdir(nvidia_dir):
                for root, dirs, files in os.walk(nvidia_dir):
                    if "bin" in dirs or any(f.endswith(".dll") for f in files):
                        bin_path = os.path.join(root, "bin") if "bin" in dirs else root
                        try:
                            os.add_dll_directory(bin_path)
                        except Exception:
                            pass
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass

    # 3. Check system CUDA_PATH environment variable
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        cuda_bin = os.path.join(cuda_path, "bin")
        if os.path.isdir(cuda_bin):
            try:
                os.add_dll_directory(cuda_bin)
            except Exception:
                pass
            os.environ["PATH"] = cuda_bin + os.pathsep + os.environ.get("PATH", "")


init_cuda_dll_paths()

import threading
import time
import winsound
from PyQt6.QtCore import Qt, QTimer


from PyQt6.QtWidgets import QApplication

from window_context import get_active_window_context
from audio_recorder import AudioRecorder
from config import config
from hotkey_manager import HotkeyManager
from stt_engine import WhisperEngine
from text_injector import TextInjector, grab_selected_text_win32
from ai_formatter import AIFormatter
from voice_editor import VoiceEditor
from gui.theme import get_stylesheet, apply_window_backdrop
from gui.assets import create_app_icon
from gui.signals import signals
from gui.floating_hud import FloatingHUD
from gui.dashboard_window import DashboardWindow
from gui.scratchpad_window import ScratchpadWindow
from gui.tray_icon import VelodictumTrayIcon
from sound_effects import play_cue_async
from mobile_bridge_server import MobileBridgeServer
from i18n import tr, get_current_language


class VelodictumCoreApp:
    def __init__(self):
        self.config = config
        self.is_processing = False
        self.is_voice_editing = False
        self._edit_original_text = ""
        self.enable_sound_cues = True

        # 1. Initialize Core Engine Components
        self.recorder = AudioRecorder(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            device=config.audio.input_device,
            on_level_update=self._on_audio_level,
        )

        self.stt = WhisperEngine(
            model_size=config.whisper.model_size,
            device=config.whisper.device,
            compute_type=config.whisper.compute_type,
            language=config.whisper.language,
            beam_size=config.whisper.beam_size,
            vad_filter=config.whisper.vad_filter,
        )

        self.formatter = AIFormatter(
            mode=config.formatting.mode,
            engine=config.formatting.engine,
            api_endpoint=getattr(config.formatting, "api_endpoint", "https://openrouter.ai/api/v1"),
            api_key=config.formatting.api_key,
            model=getattr(config.formatting, "model", "qwen/qwen-2.5-72b-instruct"),
            ollama_url=config.formatting.ollama_url,
            ollama_model=config.formatting.ollama_model,
            tone=getattr(config.formatting, "tone", "default"),
            custom_instructions=getattr(config.formatting, "custom_instructions", ""),
        )

        self.voice_editor = VoiceEditor(self.formatter)

        self.injector = TextInjector(
            auto_paste=config.injection.auto_paste,
            restore_clipboard=config.injection.restore_clipboard,
            restore_delay=config.injection.clipboard_restore_delay,
        )

        self.hotkey = HotkeyManager(
            hotkey_name=config.hotkey.key,
            mode=config.hotkey.mode,
            on_start_recording=self.on_start_recording,
            on_stop_recording=self.on_stop_recording,
            on_cancel=self.cancel_recording,
        )

        # Register Undo Hotkey (Ctrl+Alt+Z)
        undo_key = getattr(config.hotkey, "undo_key", "ctrl+alt+z")
        self.hotkey.register_hotkey(
            name="undo",
            combo_str=undo_key,
            on_press=self.on_undo_hotkey,
            mode="press_once",
        )

        # Register Voice Edit Hotkey (Ctrl+Alt+Space)
        edit_key = getattr(config.hotkey, "edit_key", "ctrl+alt+space")
        self.hotkey.register_hotkey(
            name="voice_edit",
            combo_str=edit_key,
            on_press=self.on_start_voice_edit,
            on_release=self.on_stop_voice_edit,
            mode=getattr(config.hotkey, "mode", "push_to_talk"),
        )

        # Register Scratchpad Hotkey (Ctrl+Shift+D)
        scratchpad_key = getattr(config.hotkey, "scratchpad_key", "ctrl+shift+d")
        self.hotkey.register_hotkey(
            name="scratchpad",
            combo_str=scratchpad_key,
            on_press=self.on_toggle_scratchpad,
            mode="press_once",
        )

        # Mobile LAN Bridge Server
        self.mobile_bridge = MobileBridgeServer(
            port=getattr(config.mobile_bridge, "port", 8765),
            on_audio_received=self._on_mobile_audio_received,
        )

        # Start background Audio Device Hot-Plug Monitor
        from audio_device_monitor import audio_device_monitor
        audio_device_monitor.set_recorder(self.recorder)
        audio_device_monitor.start()

        # Start Smart In-Field Correction & Proper-Noun Detector
        from correction_detector import correction_detector
        correction_detector.start()

        self.enable_sound_cues = getattr(config.system, "sound_cues", True)
        self._recent_transcripts = []

        # Listen to hotkey & mode configuration changes
        signals.mode_changed.connect(self._on_mode_or_hotkey_changed)
        signals.dictation_toggle_requested.connect(self.toggle_recording)
        signals.dictation_cancel_requested.connect(self.cancel_recording)
        signals.mobile_bridge_toggled.connect(self._on_mobile_bridge_toggled)

        self._proc_lock = threading.Lock()

    def _on_mobile_bridge_toggled(self, enabled: bool):
        if enabled:
            self.mobile_bridge.start()
        else:
            self.mobile_bridge.stop()

    def toggle_recording(self):
        """Toggle recording state from UI button or action."""
        if self.is_voice_editing and self.recorder.is_recording:
            self.on_stop_voice_edit()
        elif self.recorder.is_recording:
            self.on_stop_recording()
        else:
            self.on_start_recording()

    def cancel_recording(self):
        """Cancel active recording immediately, discard audio data and notify UI."""
        with self._proc_lock:
            if not self.recorder.is_recording and not self.is_voice_editing:
                # Also reset hotkey state just in case it was left active
                self.hotkey.reset_all_states()
                return

            self.recorder.stop()
            self.is_processing = False
            self.is_voice_editing = False
            self.hotkey.reset_all_states()

            if getattr(config.audio, "auto_ducking", True):
                from audio_ducker import audio_ducker
                audio_ducker.unduck()

            self._play_cue(start=False)
            signals.recording_cancelled.emit()
            print("[Velodictum] Recording cancelled by user (audio discarded, state reset).")

    def _on_mode_or_hotkey_changed(self, mode: str):
        self.hotkey.mode = mode
        if "voice_edit" in self.hotkey._bindings:
            self.hotkey._bindings["voice_edit"].mode = mode
        self.hotkey.set_hotkey(self.config.hotkey.key)
        undo_key = getattr(self.config.hotkey, "undo_key", "ctrl+alt+z")
        self.hotkey.set_hotkey_combo("undo", undo_key)
        edit_key = getattr(self.config.hotkey, "edit_key", "ctrl+alt+space")
        self.hotkey.set_hotkey_combo("voice_edit", edit_key)
        scratchpad_key = getattr(self.config.hotkey, "scratchpad_key", "ctrl+shift+d")
        self.hotkey.set_hotkey_combo("scratchpad", scratchpad_key)

    def on_toggle_scratchpad(self):
        """Toggle floating scratchpad quick memo window."""
        signals.scratchpad_toggle_requested.emit()

    def set_mobile_bridge_enabled(self, enabled: bool):
        """Start or stop mobile bridge server dynamically."""
        config.mobile_bridge.enabled = enabled
        config.save()
        if enabled:
            self.mobile_bridge.start()
        else:
            self.mobile_bridge.stop()

    def _on_mobile_audio_received(self, audio_bytes: bytes) -> str:
        """Handle audio dictation streamed from smartphone over LAN."""
        import tempfile
        import os
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tf:
                tf.write(audio_bytes)
                temp_path = tf.name

            signals.transcription_started.emit()
            self.stt.load()
            segments, info = self.stt._model.transcribe(
                temp_path,
                language=self.config.whisper.language,
                vad_filter=True,
                beam_size=self.config.whisper.beam_size,
            )

            raw_chunks = [s.text.strip() for s in segments if s.text.strip()]
            raw_text = " ".join(raw_chunks).strip()

            if not raw_text:
                signals.transcription_failed.emit(f"{tr('hud_no_speech')} (Mobile)" if get_current_language() == "en" else f"{tr('hud_no_speech')} (Mobil)")
                return ""

            signals.formatting_started.emit()
            win_ctx = get_active_window_context(include_deep_text=True)

            fmt_result = self.formatter.format_text(
                raw_text,
                language=info.language if info else "de",
                window_context=win_ctx,
            )
            final_text = fmt_result["text"]

            # Prepend space if mid-sentence continuation requires it
            if win_ctx.get("needs_leading_space") and not final_text.startswith(" ") and not final_text.startswith((".", ",", "!", "?", ":", ";")):
                final_text = " " + final_text

            send_enter = False
            if fmt_result.get("action") == "send_enter" and getattr(self.config.injection, "send_it_enabled", True):
                send_enter = True

            self.injector.inject(final_text, raw_text=raw_text, send_enter=send_enter)

            payload = {
                "text": final_text,
                "raw_text": raw_text,
                "duration": info.duration if info else 0.0,
                "latency": 0.5,
                "language": info.language if info else "de",
                "probability": 1.0,
                "mode": fmt_result["mode"],
                "engine": fmt_result["engine"],
                "action": fmt_result.get("action"),
            }
            signals.transcription_completed.emit(payload)
            return final_text
        except Exception as e:
            signals.transcription_failed.emit(f"{tr('hud_error')} (Mobile): {e}")
            return ""
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _play_cue(self, start: bool):
        if getattr(config.system, "sound_cues", True):
            play_cue_async(start=start)

    def _on_audio_level(self, rms: float):
        try:
            signals.audio_level_updated.emit(rms)
        except (RuntimeError, AttributeError):
            pass

    def on_undo_hotkey(self):
        """Revert the last text injection in the active window."""
        res = self.injector.revert_last_injection(mode="undo")
        signals.injection_reverted.emit(res)

    def on_start_voice_edit(self):
        """Grab selected text via Ctrl+C and start recording transformation instruction."""
        with self._proc_lock:
            if self.is_processing or self.recorder.is_recording:
                return

            # Password & Sensitive Field Guard: Strictly refuse voice transform on password fields
            try:
                from ui_automation_context import is_sensitive_or_password_focused
                is_blocked, reason = is_sensitive_or_password_focused()
            except Exception:
                is_blocked, reason = False, ""

            if is_blocked:
                print(f"[Velodictum] Voice Edit blocked: {reason}")
                signals.injection_blocked.emit(reason or tr("hud_password_protected"))
                self.hotkey.reset_all_states()
                return

            self.is_voice_editing = True
            # 1. Grab selected text from foreground window
            self._edit_original_text = grab_selected_text_win32()
            if not self._edit_original_text or not self._edit_original_text.strip():
                signals.transcription_failed.emit(tr("hud_no_text_selected"))
                self.is_voice_editing = False
                self.hotkey.reset_all_states()
                return

            self._play_cue(start=True)
            if getattr(config.audio, "auto_ducking", True):
                def _duck_async():
                    try:
                        from audio_ducker import audio_ducker
                        duck_target = getattr(config.audio, "ducking_volume_percent", 25) / 100.0
                        audio_ducker.duck(target_fraction=duck_target)
                    except Exception:
                        pass
                threading.Thread(target=_duck_async, daemon=True).start()

            started = self.recorder.start()
            if started:
                signals.voice_edit_started.emit()

    def on_stop_voice_edit(self):
        """Stop voice edit recording and process transformation."""
        with self._proc_lock:
            if not self.recorder.is_recording or self.is_processing:
                return
            self.is_processing = True
            if getattr(config.audio, "auto_ducking", True):
                from audio_ducker import audio_ducker
                audio_ducker.unduck()
            audio_data = self.recorder.stop()
            self._play_cue(start=False)
            signals.recording_stopped.emit()

        if audio_data is not None:
            threading.Thread(target=self._process_voice_edit_worker, args=(audio_data, self._edit_original_text), daemon=True).start()
        else:
            self.is_processing = False
            self.is_voice_editing = False

    def _process_voice_edit_worker(self, audio_data, original_text: str):
        try:
            if not original_text or not original_text.strip():
                signals.transcription_failed.emit(tr("hud_no_text_selected"))
                return

            if len(audio_data) < int(self.config.audio.sample_rate * self.config.audio.min_audio_length_sec):
                signals.transcription_failed.emit("Too short" if get_current_language() == "en" else "Zu kurz")
                return

            # Transcribe spoken instruction
            result = self.stt.transcribe(audio_data, sample_rate=self.config.audio.sample_rate)
            instruction = result.get("text", "").strip()

            if not instruction:
                signals.transcription_failed.emit("No instruction detected" if get_current_language() == "en" else "Keine Anweisung erkannt")
                return

            signals.formatting_started.emit()
            # Transform text via LLM
            transformed = self.voice_editor.transform_text(
                original_text=original_text,
                instruction=instruction,
                language=result.get("language", "de"),
            )

            if transformed and transformed.strip():
                self.injector.inject(transformed.strip(), raw_text=instruction)
                payload = {
                    "text": transformed.strip(),
                    "instruction": instruction,
                    "duration": result["duration"],
                    "latency": result["latency"],
                    "mode": "voice_transform",
                    "engine": self.formatter.engine,
                }
                signals.voice_edit_completed.emit(payload)
            else:
                signals.transcription_failed.emit("Transformation not possible" if get_current_language() == "en" else "Transformation nicht möglich")
        except Exception as e:
            signals.transcription_failed.emit(str(e))
        finally:
            self.is_processing = False
            self.is_voice_editing = False

    def on_start_recording(self):
        with self._proc_lock:
            if self.is_processing or self.recorder.is_recording:
                return

            # Password & Sensitive Field Guard: Strictly refuse recording in password fields / managers
            try:
                from ui_automation_context import is_sensitive_or_password_focused
                is_blocked, reason = is_sensitive_or_password_focused()
            except Exception:
                is_blocked, reason = False, ""

            if is_blocked:
                print(f"[Velodictum] Dictation blocked: {reason}")
                signals.injection_blocked.emit(reason or tr("hud_password_protected"))
                self.hotkey.reset_all_states()
                return

            self._play_cue(start=True)
            if getattr(config.audio, "auto_ducking", True):
                def _duck_async():
                    try:
                        from audio_ducker import audio_ducker
                        duck_target = getattr(config.audio, "ducking_volume_percent", 25) / 100.0
                        audio_ducker.duck(target_fraction=duck_target)
                    except Exception:
                        pass
                threading.Thread(target=_duck_async, daemon=True).start()

            started = self.recorder.start()
            if started:
                signals.recording_started.emit()

    def on_stop_recording(self):
        with self._proc_lock:
            if not self.recorder.is_recording or self.is_processing:
                return
            self.is_processing = True
            if getattr(config.audio, "auto_ducking", True):
                from audio_ducker import audio_ducker
                audio_ducker.unduck()
            audio_data = self.recorder.stop()
            self._play_cue(start=False)
            signals.recording_stopped.emit()

        if audio_data is not None:
            threading.Thread(target=self._process_audio_worker, args=(audio_data,), daemon=True).start()
        else:
            self.is_processing = False

    def _process_audio_worker(self, audio_data):
        signals.transcription_started.emit()
        try:
            if len(audio_data) < int(self.config.audio.sample_rate * self.config.audio.min_audio_length_sec):
                signals.transcription_failed.emit(tr("hud_too_short"))
                return

            # Determine whether Whisper native acoustic translation should be used
            is_translate = getattr(self.config.translation, "enabled", False) or self.config.formatting.mode == "translate"
            stt_task = "translate" if (is_translate and getattr(self.config.translation, "target_language", "en") == "en") else "transcribe"

            # Dynamic Workspace Seeding (VS Code project, open file, git branch)
            win_ctx_initial = get_active_window_context(include_deep_text=False)
            ws_terms = [
                win_ctx_initial.get("workspace_project", ""),
                win_ctx_initial.get("workspace_file", ""),
                win_ctx_initial.get("git_branch", ""),
            ]
            from custom_vocabulary import vocab_manager
            vocab_manager.set_transient_workspace_terms([t for t in ws_terms if t])

            # 1. Transcribe with Whisper (Local GPU/CPU or Cloud Provider)
            result = self.stt.transcribe(audio_data, sample_rate=self.config.audio.sample_rate, task=stt_task)
            raw_text = result["text"]

            if not raw_text.strip():
                signals.transcription_failed.emit(tr("hud_no_speech"))
                return

            # 2. Apply AI Post-Processing & The Flow Layer
            signals.formatting_started.emit()
            win_ctx = get_active_window_context(include_deep_text=True)
            
            # Sync engine, model, API key, tone and custom instructions with current config
            self.formatter.mode = self.config.formatting.mode
            self.formatter.engine = self.config.formatting.engine
            self.formatter.api_endpoint = getattr(self.config.formatting, "api_endpoint", "https://openrouter.ai/api/v1")
            self.formatter.api_key = self.config.formatting.api_key
            self.formatter.model = getattr(self.config.formatting, "model", "qwen/qwen-2.5-72b-instruct")
            self.formatter.ollama_url = self.config.formatting.ollama_url
            self.formatter.ollama_model = self.config.formatting.ollama_model
            self.formatter.openrouter_model = self.formatter.model
            self.formatter.tone = getattr(self.config.formatting, "tone", "default")
            self.formatter.custom_instructions = getattr(self.config.formatting, "custom_instructions", "")

            fmt_result = self.formatter.format_text(
                raw_text,
                language=result.get("language", "de"),
                window_context=win_ctx,
            )
            final_text = fmt_result["text"]

            if not final_text.strip():
                signals.transcription_failed.emit(tr("hud_no_speech"))
                return

            # Prepend space if mid-sentence continuation requires it
            if win_ctx.get("needs_leading_space") and not final_text.startswith(" ") and not final_text.startswith((".", ",", "!", "?", ":", ";")):
                final_text = " " + final_text

            # 3. Check for Actions (Cancel / Send-It)
            if fmt_result.get("action") == "cancel":
                signals.recording_cancelled.emit()
                return

            send_enter = False
            if fmt_result.get("action") == "send_enter" and getattr(self.config.injection, "send_it_enabled", True):
                send_enter = True

            # 4. Auto-paste into focused application
            self.injector.inject(final_text, raw_text=raw_text, send_enter=send_enter)

            # 5. Check for unknown technical word suggestions for personal vocabulary
            try:
                suggestions = vocab_manager.suggest_words_from_text(final_text)
                for sug in suggestions:
                    signals.vocab_suggestion_available.emit(sug)
            except Exception:
                pass

            # Total latency = Whisper latency + AI formatting latency
            total_latency = result["latency"] + fmt_result.get("latency", 0.0)

            # Emit completion event to update HUD, Dashboard, and History
            payload = {
                "text": final_text,
                "raw_text": raw_text,
                "duration": result["duration"],
                "latency": total_latency,
                "language": result["language"],
                "probability": result["language_prob"],
                "mode": fmt_result["mode"],
                "engine": fmt_result["engine"],
                "action": fmt_result.get("action"),
            }
            signals.transcription_completed.emit(payload)

        except Exception as e:
            signals.transcription_failed.emit(str(e))
        finally:
            self.is_processing = False

    def start_background_workers(self):
        # Pre-warm audio stream for 0ms recording latency
        def _audio_warmup():
            try:
                self.recorder._ensure_stream_open()
            except Exception:
                pass
        threading.Thread(target=_audio_warmup, daemon=True).start()

        # Warmup Whisper model in a background worker
        def _warmup_worker():
            self.stt.load()
            self.stt.warmup()
        threading.Thread(target=_warmup_worker, daemon=True).start()

        # Start low-level hotkey listener
        self.hotkey.start()

        # Start mobile bridge if enabled
        if getattr(self.config.mobile_bridge, "enabled", False):
            self.mobile_bridge.start()


# Backward compatibility alias
VelodictumApp = VelodictumCoreApp


import atexit
from single_instance import ensure_single_instance, release_single_instance


def main():
    # 0. Single Instance Guard (Prevents duplicate hotkeys, double paste & double HUDs)
    if not ensure_single_instance(app_title="Velodictum"):
        msg = "Another instance of Velodictum is already running. Window brought to foreground." if get_current_language() == "en" else "Eine andere Instanz von Velodictum läuft bereits. Fenster wurde in den Vordergrund gebracht."
        print(f"[Velodictum] {msg}")
        sys.exit(0)

    atexit.register(release_single_instance)

    # 1. Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Velodictum")
    app.setWindowIcon(create_app_icon(64))
    app.setStyleSheet(get_stylesheet())
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray!

    # 1.5 Check First-Run Language Selection (Prompts on first open or fresh .exe unpack)
    if not getattr(config.system, "first_run_completed", False):
        from gui.language_dialog import LanguageSelectionDialog
        lang_dlg = LanguageSelectionDialog()
        lang_dlg.exec()

    # 2. Core Engine
    core = VelodictumCoreApp()
    atexit.register(core.recorder.close)
    core.start_background_workers()

    # 3. Create Windows & UI Elements
    dashboard = DashboardWindow(core.recorder, core.stt, core.formatter)
    scratchpad = ScratchpadWindow(core.formatter)
    hud = FloatingHUD()
    tray = VelodictumTrayIcon(dashboard)
    tray.show()

    # Show dashboard unless started with --minimized or configured to start minimized
    start_minimized = "--minimized" in sys.argv or getattr(config.system, "start_minimized", False)
    if not start_minimized:
        dashboard.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
