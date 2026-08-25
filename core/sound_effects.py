"""
Velodictum - High-Fidelity Studio Audio Cues Engine
Physical modeling DSP synthesizer & high-definition acoustic themes for recording feedback.
Velodictum - High-Fidelity Studio Audio Cues Engine
Zero-latency synthetic auditory feedback using NumPy physical modeling DSP.
Produces soft organic pops, haptic transients, and acoustic tones.
"""
import numpy as np
import io
import wave
import threading
import os
import time
from typing import Dict, Optional, Tuple

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    HAS_SD = False

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False


from i18n import tr

SAMPLE_RATE = 44100


def get_sound_themes() -> Dict[str, Dict[str, str]]:
    return {
        "velodictum_silk": {
            "name": tr("sound_theme_silk_name"),
            "desc": tr("sound_theme_silk_desc"),
        },
        "taptic_glass": {
            "name": tr("sound_theme_taptic_name"),
            "desc": tr("sound_theme_taptic_desc"),
        },
        "haptic": {
            "name": tr("sound_theme_haptic_name"),
            "desc": tr("sound_theme_haptic_desc"),
        },
        "tactile_thock": {
            "name": tr("sound_theme_thock_name"),
            "desc": tr("sound_theme_thock_desc"),
        },
        "cyber_pulse": {
            "name": tr("sound_theme_cyber_name"),
            "desc": tr("sound_theme_cyber_desc"),
        },
        "velvet": {
            "name": tr("sound_theme_velvet_name"),
            "desc": tr("sound_theme_velvet_desc"),
        },
        "opal_resonance": {
            "name": tr("sound_theme_opal_name"),
            "desc": tr("sound_theme_opal_desc"),
        },
        "quantum_haptic": {
            "name": tr("sound_theme_quantum_name"),
            "desc": tr("sound_theme_quantum_desc"),
        },
        "none": {
            "name": tr("sound_theme_none_name"),
            "desc": tr("sound_theme_none_desc"),
        },
    }

SOUND_THEMES = get_sound_themes()


# =========================================================================
# Physical Modeling & Acoustic DSP Synthesizers
# =========================================================================

def _synth_velodictum_silk(start: bool = True) -> np.ndarray:
    """
    Ultra-HD Velodictum Silk Droplet:
    Extrem geschmeidiger, organischer Wassertropfen-Pop mit sanfter Tiefenwärme.
    Aufsteigender Pitch-Sweep beim Start für den authentischen "Liquid Drop" Pop-Effekt.
    """
    try:
        import pyfxr
        if start:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Pure Sine
                p_base_freq=0.46,
                p_freq_ramp=0.38,       # Aufsteigender Pitch für natürlichen "Pop"
                p_env_attack=0.0,
                p_env_sustain=0.012,
                p_env_decay=0.052,
                p_env_punch=0.35,
                p_lpf_freq=0.88,
            )
        else:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Pure Sine
                p_base_freq=0.52,
                p_freq_ramp=-0.28,      # Sanfter abfallender Ausklang
                p_env_attack=0.0,
                p_env_sustain=0.010,
                p_env_decay=0.045,
                p_env_punch=0.20,
                p_lpf_freq=0.78,
            )
        arr = np.frombuffer(s_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return (arr * 0.48).astype(np.float32)
    except Exception:
        duration = 0.038
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        f_main = 260.0 + 460.0 * np.exp(-t / 0.007)
        phase_main = 2 * np.pi * np.cumsum(f_main) / SAMPLE_RATE
        env_main = np.exp(-t / 0.008) * (1.0 - np.exp(-t / 0.0012))
        return ((np.sin(phase_main) + 0.12 * np.sin(2 * phase_main)) * env_main * 0.45).astype(np.float32)


def _synth_taptic_glass(start: bool = True) -> np.ndarray:
    """
    Velodictum Taptic Glass:
    Kristallklarer doppelter Mikro-Tap (8ms Versatz) wie bei einem Glas-Trackpad.
    """
    try:
        import pyfxr
        if start:
            # Tap 1 (Präziser Glaskontakt)
            s1 = pyfxr.sfx(wave_type=2, p_base_freq=0.80, p_freq_ramp=-0.40, p_env_attack=0.0, p_env_sustain=0.006, p_env_decay=0.026, p_env_punch=0.45, p_lpf_freq=0.98)
            # Tap 2 (Hellere Glasresonanz)
            s2 = pyfxr.sfx(wave_type=2, p_base_freq=0.88, p_freq_ramp=-0.48, p_env_attack=0.0, p_env_sustain=0.010, p_env_decay=0.035, p_env_punch=0.55, p_lpf_freq=0.98)
            a1 = np.frombuffer(s1, dtype=np.int16).astype(np.float32) / 32768.0
            a2 = np.frombuffer(s2, dtype=np.int16).astype(np.float32) / 32768.0
            # 8ms Versatz
            offset = int(0.008 * SAMPLE_RATE)
            total_len = max(len(a1), len(a2) + offset)
            merged = np.zeros(total_len, dtype=np.float32)
            merged[:len(a1)] += a1 * 0.45
            merged[offset:offset + len(a2)] += a2 * 0.65
            return (merged * 0.50).astype(np.float32)
        else:
            s = pyfxr.sfx(wave_type=2, p_base_freq=0.60, p_freq_ramp=-0.35, p_env_attack=0.0, p_env_sustain=0.010, p_env_decay=0.038, p_env_punch=0.35, p_lpf_freq=0.92)
            a = np.frombuffer(s, dtype=np.int16).astype(np.float32) / 32768.0
            return (a * 0.45).astype(np.float32)
    except Exception:
        duration = 0.042
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        f = 300.0 + 340.0 * np.exp(-t / 0.005)
        p = 2 * np.pi * np.cumsum(f) / SAMPLE_RATE
        e = np.exp(-t / 0.006) * (1.0 - np.exp(-t / 0.001))
        return (np.sin(p) * e * 0.40).astype(np.float32)


def _synth_haptic(start: bool = True) -> np.ndarray:
    """
    Haptic Pop:
    Ultrakurzer, chirurgischer Mikroschalter-Pop mit 0ms Nachschwingen.
    """
    try:
        import pyfxr
        s = pyfxr.sfx(
            wave_type=2,
            p_base_freq=0.72 if start else 0.54,
            p_freq_ramp=-0.55,
            p_env_attack=0.0,
            p_env_sustain=0.006,
            p_env_decay=0.030,
            p_env_punch=0.55,
            p_lpf_freq=0.96,
        )
        a = np.frombuffer(s, dtype=np.int16).astype(np.float32) / 32768.0
        return (a * 0.48).astype(np.float32)
    except Exception:
        duration = 0.032
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        freq = 560.0 if start else 400.0
        phase = 2 * np.pi * np.cumsum(freq * np.exp(-t / 0.010)) / SAMPLE_RATE
        env = np.exp(-t / 0.007) * (1.0 - np.exp(-t / 0.001))
        return (np.sin(phase) * env * 0.40).astype(np.float32)


def _synth_tactile_thock(start: bool = True) -> np.ndarray:
    """
    Studio Tactile Thock:
    Geschmierter Custom Mechanical Keyboard Switch mit sattem Tiefbass-Körper (Thock).
    """
    try:
        import pyfxr
        s = pyfxr.sfx(
            wave_type=2,
            p_base_freq=0.32 if start else 0.24,
            p_freq_ramp=-0.62,
            p_env_attack=0.0,
            p_env_sustain=0.018,
            p_env_decay=0.065,
            p_env_punch=0.70,
            p_lpf_freq=0.58,
            p_lpf_resonance=0.25,
        )
        a = np.frombuffer(s, dtype=np.int16).astype(np.float32) / 32768.0
        return (a * 0.50).astype(np.float32)
    except Exception:
        duration = 0.040
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        f_pitch = (120.0 if start else 90.0) * np.exp(-t / 0.009)
        body = np.sin(2 * np.pi * np.cumsum(f_pitch) / SAMPLE_RATE) * np.exp(-t / 0.016)
        snap = np.sin(2 * np.pi * 2800.0 * t) * np.exp(-t / 0.004) * (1.0 - np.exp(-t / 0.0008))
        return (np.tanh((body * 0.80 + snap * 0.35) * 1.5) * 0.40).astype(np.float32)


def _synth_cyber_pulse(start: bool = True) -> np.ndarray:
    """Cyberpunk Neural Link: FM-Chirp mit Crystalline-Obertönen."""
    try:
        import pyfxr
        if start:
            s = pyfxr.sfx(
                wave_type=1,  # Sawtooth filtered
                p_base_freq=0.72,
                p_freq_ramp=-0.60,
                p_env_attack=0.0,
                p_env_sustain=0.025,
                p_env_decay=0.09,
                p_env_punch=0.45,
                p_lpf_freq=0.65,
                p_lpf_resonance=0.35,
            )
        else:
            s = pyfxr.sfx(
                wave_type=1,
                p_base_freq=0.55,
                p_freq_ramp=-0.45,
                p_env_attack=0.0,
                p_env_sustain=0.02,
                p_env_decay=0.08,
                p_env_punch=0.35,
                p_lpf_freq=0.60,
            )
        a = np.frombuffer(s, dtype=np.int16).astype(np.float32) / 32768.0
        return (a * 0.40).astype(np.float32)
    except Exception:
        duration = 0.070
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        chirp = np.sin(2 * np.pi * 2400.0 * t) * np.exp(-t / 0.010)
        return (chirp * 0.40).astype(np.float32)


def _synth_velvet(start: bool = True) -> np.ndarray:
    """
    Velvet Acoustic:
    Warmer, harmonischer Rhodes-Chime mit weichem Ausklang.
    """
    try:
        import pyfxr
        if start:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Sine
                p_base_freq=0.68,
                p_freq_ramp=0.04,
                p_env_attack=0.008,
                p_env_sustain=0.035,
                p_env_decay=0.18,
                p_env_punch=0.16,
                p_lpf_freq=0.90,
            )
        else:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Sine
                p_base_freq=0.54,
                p_freq_ramp=-0.10,
                p_env_attack=0.006,
                p_env_sustain=0.025,
                p_env_decay=0.14,
                p_env_punch=0.12,
                p_lpf_freq=0.85,
            )
        arr = np.frombuffer(s_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return (arr * 0.44).astype(np.float32)
    except Exception:
        duration = 0.085 if start else 0.075
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        f1, f2 = (659.25, 830.61) if start else (987.77, 659.25)
        env = np.exp(-t / 0.026) * (1.0 - np.exp(-t / 0.0025))
        sig = (np.sin(2 * np.pi * f1 * t) + 0.35 * np.sin(2 * np.pi * f2 * t)) * env
        return (np.tanh(sig * 1.5) * 0.35).astype(np.float32)


def _synth_opal_resonance(start: bool = True) -> np.ndarray:
    """
    Opal Resonance:
    Transparenter Kristall-Impuls mit sanftem Obertonglanz.
    """
    try:
        import pyfxr
        if start:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Sine
                p_base_freq=0.74,
                p_freq_ramp=0.08,
                p_env_attack=0.006,
                p_env_sustain=0.030,
                p_env_decay=0.16,
                p_env_punch=0.25,
                p_vib_strength=0.08,
                p_vib_speed=0.55,
                p_lpf_freq=0.95,
            )
        else:
            s_bytes = pyfxr.sfx(
                wave_type=2,
                p_base_freq=0.58,
                p_freq_ramp=-0.14,
                p_env_attack=0.005,
                p_env_sustain=0.025,
                p_env_decay=0.13,
                p_env_punch=0.18,
                p_vib_strength=0.05,
                p_vib_speed=0.50,
                p_lpf_freq=0.90,
            )
        arr = np.frombuffer(s_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return (arr * 0.42).astype(np.float32)
    except Exception:
        duration = 0.065 if start else 0.050
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        f_main = 880.0 + 600.0 * np.exp(-t / 0.012)
        phase_main = 2 * np.pi * np.cumsum(f_main) / SAMPLE_RATE
        env_main = np.exp(-t / 0.020) * (1.0 - np.exp(-t / 0.001))
        return ((np.sin(phase_main) + 0.35 * np.sin(2.76 * phase_main)) * env_main * 0.40).astype(np.float32)


def _synth_quantum_haptic(start: bool = True) -> np.ndarray:
    """
    Quantum Precision:
    Ultra-kurzer, haptischer Micro-Impuls mit pyfxr.
    """
    try:
        import pyfxr
        if start:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Sine
                p_base_freq=0.74,
                p_freq_ramp=-0.50,
                p_env_attack=0.0,
                p_env_sustain=0.015,
                p_env_decay=0.045,
                p_env_punch=0.40,
                p_lpf_freq=0.95,
            )
        else:
            s_bytes = pyfxr.sfx(
                wave_type=2,  # Sine
                p_base_freq=0.55,
                p_freq_ramp=-0.40,
                p_env_attack=0.0,
                p_env_sustain=0.012,
                p_env_decay=0.040,
                p_env_punch=0.30,
                p_lpf_freq=0.90,
            )
        arr = np.frombuffer(s_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return (arr * 0.45).astype(np.float32)
    except Exception:
        return _synth_haptic(start)


# =========================================================================
# Pre-rendered Zero-Latency In-Memory Buffers (NumPy Float + WAV Bytes)
# =========================================================================

_THEME_BUFFERS: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
_THEME_WAV_BYTES: Dict[str, Tuple[bytes, bytes]] = {}


def _to_wav_bytes(arr: np.ndarray) -> bytes:
    arr16 = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(arr16.tobytes())
    return buf.getvalue()


def _init_buffers():
    global _THEME_BUFFERS, _THEME_WAV_BYTES
    raw_themes = {
        "velodictum_silk": (_synth_velodictum_silk(True), _synth_velodictum_silk(False)),
        "veloflow_silk": (_synth_velodictum_silk(True), _synth_velodictum_silk(False)),
        "taptic_glass": (_synth_taptic_glass(True), _synth_taptic_glass(False)),
        "haptic": (_synth_haptic(True), _synth_haptic(False)),
        "tactile_thock": (_synth_tactile_thock(True), _synth_tactile_thock(False)),
        "cyber_pulse": (_synth_cyber_pulse(True), _synth_cyber_pulse(False)),
        "velvet": (_synth_velvet(True), _synth_velvet(False)),
        "opal_resonance": (_synth_opal_resonance(True), _synth_opal_resonance(False)),
        "quantum_haptic": (_synth_quantum_haptic(True), _synth_quantum_haptic(False)),
    }
    _THEME_BUFFERS = raw_themes
    _THEME_WAV_BYTES = {
        k: (_to_wav_bytes(v[0]), _to_wav_bytes(v[1]))
        for k, v in raw_themes.items()
    }


_init_buffers()


# =========================================================================
# Playback Engine
# =========================================================================

def play_cue_async(start: bool = True, theme: Optional[str] = None, volume: Optional[float] = None):
    """Plays cue asynchronously with zero blocking (<1ms latency)."""
    def _worker():
        try:
            from config import config
            active_theme = theme or getattr(config.system, "sound_theme", "velodictum_silk")
            vol = volume if volume is not None else getattr(config.system, "sound_volume", 0.75)
            
            if active_theme == "none" or vol <= 0.01:
                return

            if active_theme in _THEME_BUFFERS:
                buf_pair = _THEME_BUFFERS[active_theme]
                audio_data = buf_pair[0] if start else buf_pair[1]
                
                if HAS_SD and audio_data is not None:
                    try:
                        scaled = audio_data * float(vol)
                        sd.play(scaled, samplerate=SAMPLE_RATE, blocking=False)
                        return
                    except Exception:
                        pass

                # Ultra-reliable Windows Multimedia API fallback
                if HAS_WINSOUND and active_theme in _THEME_WAV_BYTES:
                    wav_data = _THEME_WAV_BYTES[active_theme][0 if start else 1]
                    winsound.PlaySound(wav_data, winsound.SND_MEMORY)
                    return

            if HAS_WINSOUND:
                sound_alias = "SystemAsterisk" if start else "SystemExclamation"
                winsound.PlaySound(sound_alias, winsound.SND_ALIAS)

        except Exception as e:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def preview_cue(theme: str = "velodictum_silk", volume: float = 0.75):
    """Plays start cue followed by stop cue after 380ms for immediate auditioning in UI."""
    def _preview():
        play_cue_async(start=True, theme=theme, volume=volume)
        time.sleep(0.38)
        play_cue_async(start=False, theme=theme, volume=volume)

    threading.Thread(target=_preview, daemon=True).start()
