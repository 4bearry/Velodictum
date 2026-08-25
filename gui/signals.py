"""
Velodictum - Qt Signals Event Bus
Thread-safe signals connecting background audio/hotkey/STT workers with the PyQt6 UI.
"""
from PyQt6.QtCore import QObject, pyqtSignal


class VelodictumSignals(QObject):
    # Hotkey / Recording events
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    recording_cancelled = pyqtSignal()
    audio_level_updated = pyqtSignal(float)  # RMS level [0.0 - 1.0]
    dictation_toggle_requested = pyqtSignal()
    dictation_cancel_requested = pyqtSignal()

    # STT & AI Flow events
    transcription_started = pyqtSignal()
    formatting_started = pyqtSignal()
    transcription_completed = pyqtSignal(dict)  # {"text", "duration", "latency", "language", "formatted"}
    transcription_failed = pyqtSignal(str)
    model_loading_started = pyqtSignal(str)
    model_loading_completed = pyqtSignal(str)

    # Hardware Telemetry events
    gpu_telemetry_updated = pyqtSignal(dict)

    # Voice Transform & Undo events
    voice_edit_started = pyqtSignal()
    voice_edit_completed = pyqtSignal(dict)
    injection_reverted = pyqtSignal(dict)
    injection_blocked = pyqtSignal(str)
    injection_failed = pyqtSignal(str)

    # Context & Vocabulary events
    vocab_suggestion_available = pyqtSignal(str)
    vocab_suggestion_prompt = pyqtSignal(dict)  # {"word": "Pawbert", "original": "Paulbert", "category": "Eigennamen"}
    vocab_word_learned = pyqtSignal(str)
    scratchpad_toggle_requested = pyqtSignal()

    # Config & Device change events
    language_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    mic_changed = pyqtSignal(int)
    mode_changed = pyqtSignal(str)
    dictation_mode_changed = pyqtSignal(str)
    audio_device_switched = pyqtSignal(str)  # Auto-switched microphone name
    mobile_bridge_toggled = pyqtSignal(bool)


_signals_instance = None


def get_signals() -> VelodictumSignals:
    global _signals_instance
    try:
        if _signals_instance is None:
            _signals_instance = VelodictumSignals()
        # Access a method to verify C++ object is alive
        _signals_instance.objectName()
    except (RuntimeError, AttributeError):
        _signals_instance = VelodictumSignals()
    return _signals_instance


class SignalsProxy:
    def __getattr__(self, name):
        return getattr(get_signals(), name)


# Global self-healing singleton proxy
signals = SignalsProxy()
