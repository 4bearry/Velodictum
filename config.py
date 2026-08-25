"""
Velodictum - Configuration & Settings Persistence
Dataclass-based configuration with automatic JSON serialization.
"""
import json
import os
import sys
import logging
from dataclasses import dataclass, field, asdict, fields
from typing import Optional, List, Dict, Any
import security_credentials as sec


def get_app_dir() -> str:
    """Returns the base application directory for persistent user configuration files."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SETTINGS_FILE = os.path.join(get_app_dir(), "settings.json")


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    input_device: Optional[int] = None  # None = default Windows microphone
    device_index: Optional[int] = None
    min_audio_length_sec: float = 0.3
    silence_threshold_rms: float = 0.005
    auto_ducking: bool = True  # Automatically lower other audio sources during dictation
    ducking_volume_percent: int = 25  # Volume target % while dictating (10 - 50%)
    input_gain: float = 1.0  # Software Pre-amplification / Gain multiplier (0.5 to 3.0)


WHISPER_PROFILES = {
    "multilingual": {
        "name": "Mehrsprachig (Large-v3)",
        "tag": "MAX QUALITY",
        "model": "large-v3",
        "model_size": "large-v3",
        "device": "cuda",
        "compute_type": "float16",
        "language": None,
        "desc": "Schwerstes Modell (4.5 GB VRAM) mit maximaler Erkennungsgenauigkeit für alle Sprachen.",
    },
    "de_max": {
        "name": "Deutsch Maximum (Large-v3-Turbo)",
        "tag": "FLAGSHIP",
        "model": "large-v3-turbo",
        "model_size": "large-v3-turbo",
        "device": "cuda",
        "compute_type": "float16",
        "language": "de",
        "desc": "Beste Erkennungsgenauigkeit für Deutsch mit Dialekt- und Fachbegriffserkennung.",
    },
    "de_fast": {
        "name": "Deutsch Schnell (Medium)",
        "tag": "FAST",
        "model": "medium",
        "model_size": "medium",
        "device": "cuda",
        "compute_type": "float16",
        "language": "de",
        "desc": "Ausgewogenes Verhältnis zwischen Geschwindigkeit und Präzision.",
    },
    "low_vram": {
        "name": "Ressourcenschonend (Small)",
        "tag": "LITE",
        "model": "small",
        "model_size": "small",
        "device": "cuda",
        "compute_type": "int8_float16",
        "language": "de",
        "desc": "Geringster Speicherverbrauch (<1 GB VRAM) bei solider Erkennungsrate.",
    },
}

# Backward compatibility alias
PROFILES = WHISPER_PROFILES


@dataclass
class WhisperConfig:
    profile: str = "de_max"
    model_size: str = "large-v3-turbo"
    device: str = "cuda"
    compute_type: str = "float16"
    language: Optional[str] = None  # None = Auto-detect, "de", "en"
    beam_size: int = 5
    vad_filter: bool = True
    hallucination_filter: bool = True  # Drops silence artifacts & repetition loops
    provider: str = "local"  # "local", "universal", "grok", "openai"
    models_dir: Optional[str] = None  # Custom storage directory for Whisper models
    # Universal STT API / Custom Endpoint
    universal_endpoint: str = "https://openrouter.ai/api/v1/audio/transcriptions"
    universal_api_key: Optional[str] = None
    universal_model: str = "openai/whisper-large-v3"
    # Dedicated Provider Overrides
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    def get_api_key(self, prov: Optional[str] = None) -> Optional[str]:
        target_p = prov or self.provider
        if target_p in ("universal", "openrouter", "custom"):
            return (
                sec.get_credential(sec.KEY_WHISPER_UNIVERSAL_API)
                or self.universal_api_key
                or sec.get_credential(sec.KEY_UNIVERSAL_API)
            )
        elif target_p in ("grok", "groq"):
            return sec.get_credential(sec.KEY_WHISPER_GROQ_API) or self.groq_api_key
        elif target_p == "openai":
            return sec.get_credential(sec.KEY_WHISPER_OPENAI_API) or self.openai_api_key
        return None

    def set_api_key(self, secret: str, prov: Optional[str] = None):
        target_p = prov or self.provider
        if target_p in ("universal", "openrouter", "custom"):
            sec.set_credential(sec.KEY_WHISPER_UNIVERSAL_API, secret)
            self.universal_api_key = None
        elif target_p in ("grok", "groq"):
            sec.set_credential(sec.KEY_WHISPER_GROQ_API, secret)
            self.groq_api_key = None
        elif target_p == "openai":
            sec.set_credential(sec.KEY_WHISPER_OPENAI_API, secret)
            self.openai_api_key = None


@dataclass
class HotkeyConfig:
    key: str = "f8"
    mode: str = "push_to_talk"  # "push_to_talk" or "toggle"
    edit_key: str = "ctrl+alt+space"  # Voice edit / transform key
    undo_key: str = "ctrl+alt+z"  # Undo / Revert last injection
    scratchpad_key: str = "ctrl+shift+d"  # Floating scratchpad memo window


@dataclass
class InjectionConfig:
    auto_paste: bool = True
    restore_clipboard: bool = True
    clipboard_restore_delay: float = 0.35
    clean_filler_words: bool = True
    apply_snippets: bool = True
    send_it_enabled: bool = True  # Auto-send with Enter in chat apps on 'und abschicken' / 'und absenden'


@dataclass
class FormattingConfig:
    # Operating Modes: "flow" (AI Adaptive Flow with Context), "raw" (1:1 Whisper Bypass)
    mode: str = "flow"
    # Engines: "rules", "ollama", "universal", "openai", "gemini", "groq"
    engine: str = "universal"  # Universal API (OpenRouter & Custom Endpoints) as permanent default
    # Universal API (OpenAI-compatible generic endpoint interface)
    api_endpoint: str = "https://openrouter.ai/api/v1"
    api_key: Optional[str] = None
    model: str = "qwen/qwen-2.5-72b-instruct"
    # Ollama Local Daemon
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    # Dedicated Provider Overrides
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"
    # Tone & Personalization
    tone: str = "default"  # "default", "formal_sie", "informal_du", "concise", "academic"
    custom_instructions: str = ""
    auto_app_profiles: bool = True
    context_intelligence: bool = True  # Deep caret & preceding text continuation
    workspace_seeding: bool = True  # Auto-seed active VS Code project & git branch into Whisper
    spoken_markdown: bool = True  # Expand 'Überschrift 2', 'Checkbox', 'Fett', etc.
    send_it_enabled: bool = True  # Allow 'und absenden' voice command to press Enter
    # Routing & Privacy Options (OpenRouter & Universal API)
    routing_strategy: str = "latency"  # "latency", "price", "throughput", "default"
    zero_data_retention: bool = True  # Enforce data_collection: "deny" and zdr: true
    allow_fallbacks: bool = True  # Automatically route to backup provider if primary is down
    # Legacy alias
    openrouter_model: Optional[str] = None

    def get_api_key(self, eng: Optional[str] = None) -> Optional[str]:
        target_eng = eng or self.engine
        if target_eng in ("universal", "openrouter"):
            return sec.get_credential(sec.KEY_UNIVERSAL_API) or self.api_key
        elif target_eng == "openai":
            return sec.get_credential(sec.KEY_OPENAI_API) or self.openai_api_key
        elif target_eng == "gemini":
            return sec.get_credential(sec.KEY_GEMINI_API) or self.gemini_api_key
        elif target_eng == "groq":
            return sec.get_credential(sec.KEY_GROQ_API) or self.groq_api_key
        return None

    def set_api_key(self, secret: str, eng: Optional[str] = None):
        target_eng = eng or self.engine
        if target_eng in ("universal", "openrouter"):
            sec.set_credential(sec.KEY_UNIVERSAL_API, secret)
            self.api_key = None
        elif target_eng == "openai":
            sec.set_credential(sec.KEY_OPENAI_API, secret)
            self.openai_api_key = None
        elif target_eng == "gemini":
            sec.set_credential(sec.KEY_GEMINI_API, secret)
            self.gemini_api_key = None
        elif target_eng == "groq":
            sec.set_credential(sec.KEY_GROQ_API, secret)
            self.groq_api_key = None


@dataclass
class HUDConfig:
    enabled: bool = True
    position_mode: str = "bottom_center"  # "bottom_center" or "follow_cursor"
    fluid_animations: bool = True  # Fluid Elastic Spring Physics & Rubber Morphing
    minimal_mode: bool = False  # Minimalist icon-only pill mode without text labels
    remember_position: bool = True  # Remember custom dragged position on screen (when bottom_center)
    custom_x: Optional[int] = None
    custom_y: Optional[int] = None
    opacity_percent: int = 78  # 65% to 95% (Liquid Obsidian Glass density)
    bounce_intensity: int = 50  # 0% (Minimal/Calm) to 100% (Elastic Rubber Pop)
    scale_percent: int = 100  # 85% (Compact) to 115% (Large)


@dataclass
class MobileBridgeConfig:
    enabled: bool = False
    port: int = 8765
    auth_token: Optional[str] = None
    require_auth: bool = True
    bind_address: str = "0.0.0.0"
    use_https: bool = True  # Enable TLS encryption for Secure Context (Microphone API)
    max_payload_bytes: int = 25 * 1024 * 1024  # 25 MB max payload (DoS protection)
    rate_limit_per_minute: int = 30  # Max 30 requests per minute per IP



@dataclass
class SystemConfig:
    start_minimized: bool = False
    autostart: bool = False
    sound_cues: bool = True
    sound_theme: str = "velodictum_silk"  # "velodictum_silk", "taptic_glass", "haptic", "tactile_thock", "cyber_pulse", "velvet", "win11", "none"
    sound_volume: float = 0.70  # 0.0 to 1.0
    offline_privacy_mode: bool = False  # Air-Gapped Zero-Cloud Mode
    liquid_glass: bool = True  # Windows 11 Acrylic & Specular Glass Design (Standard)
    ui_language: str = "en"  # "en" (English) or "de" (Deutsch)
    first_run_completed: bool = False  # Set True once the user completed initial language setup dialog


@dataclass
class TranslationConfig:
    enabled: bool = False
    target_language: str = "en"  # "en", "de", "fr", "es", "it"
    engine: str = "whisper_direct"  # "whisper_direct", "llm"


def validate_endpoint_url(url: str, allow_localhost: bool = True) -> str:
    """
    Validates custom API endpoint URLs against SSRF (Server-Side Request Forgery),
    blocking cloud metadata endpoints (169.254.169.254, 100.100.100.200) and dangerous schemes.
    """
    import ipaddress
    import urllib.parse

    if not url or not isinstance(url, str):
        raise ValueError("Invalid endpoint URL: must be a non-empty string.")

    url_clean = url.strip()
    parsed = urllib.parse.urlparse(url_clean)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"SSRF violation: Unsupported scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"SSRF violation: Missing host in endpoint URL '{url}'.")

    host_low = hostname.lower()

    # Block well-known cloud metadata hostnames
    if host_low in ("metadata.google.internal", "instance-data", "metadata"):
        raise ValueError(f"SSRF violation: Access to cloud metadata service '{host_low}' is strictly blocked.")

    # Check if host is an IP address or localhost
    if host_low in ("localhost", "localhost.localdomain"):
        if not allow_localhost:
            raise ValueError("SSRF violation: Localhost access is disallowed.")
        return url_clean

    try:
        ip = ipaddress.ip_address(host_low)

        # Always block link-local (169.254.0.0/16, fe80::/10) and known metadata IPs
        if ip == ipaddress.ip_address("169.254.169.254") or ip == ipaddress.ip_address("100.100.100.200"):
            raise ValueError(f"SSRF violation: Access to cloud instance metadata IP '{ip}' is strictly blocked.")
        if str(ip) in ("::ffff:169.254.169.254", "fd00:ec2::254"):
            raise ValueError(f"SSRF violation: Access to cloud instance metadata IP '{ip}' is strictly blocked.")

        if ip.is_link_local:
            raise ValueError(f"SSRF violation: Access to link-local IP '{ip}' is strictly blocked.")

        if ip.is_loopback:
            if not allow_localhost:
                raise ValueError(f"SSRF violation: Loopback IP '{ip}' is disallowed.")
            return url_clean

        if ip.is_multicast or ip.is_unspecified:
            raise ValueError(f"SSRF violation: Multicast or unspecified IP '{ip}' is blocked.")

    except ValueError as ve:
        if "SSRF violation" in str(ve):
            raise
        # Hostname is a regular domain name
        pass

    return url_clean


def validate_safe_filepath(filepath: str, allowed_base_dirs: Optional[List[str]] = None) -> str:
    """
    Validates a file path against Directory Traversal (e.g. '../'), null bytes, and dangerous system paths.
    Returns normalized absolute path if valid, raises ValueError if unsafe.
    """
    if not filepath or not isinstance(filepath, str):
        raise ValueError("Invalid file path: path must be a non-empty string.")

    if "\0" in filepath:
        raise ValueError("Security violation: Null byte detected in file path.")

    norm = os.path.normpath(filepath)
    if not os.path.isabs(norm):
        abs_path = os.path.abspath(os.path.join(get_app_dir(), norm))
    else:
        abs_path = os.path.abspath(norm)

    # Rejection of dangerous Windows system root paths
    win_dir = os.environ.get("SystemRoot", "C:\\Windows")
    prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

    forbidden_roots = [
        os.path.abspath(win_dir).lower(),
        os.path.abspath(prog_files).lower(),
        os.path.abspath(prog_files_x86).lower(),
    ]

    abs_low = abs_path.lower()
    for f_root in forbidden_roots:
        if abs_low == f_root or abs_low.startswith(f_root + os.sep):
            raise ValueError(f"Security violation: Access to restricted system path '{abs_path}' is blocked.")

    if allowed_base_dirs:
        is_allowed = False
        for b_dir in allowed_base_dirs:
            b_abs = os.path.abspath(b_dir)
            try:
                if os.path.commonpath([b_abs, abs_path]) == b_abs:
                    is_allowed = True
                    break
            except Exception:
                pass
        if not is_allowed:
            raise ValueError(f"Security violation: Path traversal detected outside allowed directories: '{filepath}'.")

    return abs_path


def safe_atomic_json_write(filepath: str, data: Any, indent: int = 2) -> bool:
    """
    Safely and atomically writes JSON data to disk using a temporary file and atomic replace.
    Guarantees crash-safety and prevents 0-byte corrupted JSON files.
    """
    import secrets
    safe_path = validate_safe_filepath(filepath)
    parent_dir = os.path.dirname(safe_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    tmp_path = f"{safe_path}.tmp_{secrets.token_hex(6)}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, safe_path)
        return True
    except Exception as e:
        print(f"[SafeStorage] Atomic write failed for {safe_path}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    formatting: FormattingConfig = field(default_factory=FormattingConfig)
    hud: HUDConfig = field(default_factory=HUDConfig)
    mobile_bridge: MobileBridgeConfig = field(default_factory=MobileBridgeConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)

    is_first_run: bool = False

    def save(self, filepath: str = SETTINGS_FILE):
        """Save configuration to JSON file using atomic write, strictly sanitizing all secrets."""
        try:
            safe_path = validate_safe_filepath(filepath)
            wh_dict = asdict(self.whisper)
            wh_dict["universal_api_key"] = None
            wh_dict["groq_api_key"] = None
            wh_dict["openai_api_key"] = None

            fmt_dict = asdict(self.formatting)
            fmt_dict["api_key"] = None
            fmt_dict["openrouter_api_key"] = None
            fmt_dict["openai_api_key"] = None
            fmt_dict["gemini_api_key"] = None
            fmt_dict["groq_api_key"] = None

            data = {
                "audio": asdict(self.audio),
                "whisper": wh_dict,
                "hotkey": asdict(self.hotkey),
                "injection": asdict(self.injection),
                "formatting": fmt_dict,
                "hud": asdict(self.hud),
                "mobile_bridge": asdict(self.mobile_bridge),
                "system": asdict(self.system),
                "translation": asdict(self.translation),
            }
            safe_atomic_json_write(safe_path, data, indent=2)
        except Exception as e:
            print(f"[Config] Save error: {e}")

    def load(self, filepath: str = SETTINGS_FILE):
        """Load configuration from JSON file and automatically migrate legacy plaintext keys."""
        try:
            safe_path = validate_safe_filepath(filepath)
        except Exception as e:
            print(f"[Config] Invalid settings path '{filepath}': {e}")
            return

        if not os.path.exists(safe_path):
            self.is_first_run = True
            # Hardware auto-detection for first-time startup
            self._auto_tune_first_run_hardware()
            return
        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Auto-migrate any legacy plaintext keys from JSON to Windows Credential Vault
            migrated = sec.migrate_plaintext_keys(data)

            def _safe(cls, d):
                valid = {f.name for f in fields(cls)}
                if cls == WhisperConfig and "backend" in d and "provider" not in d:
                    d["provider"] = d["backend"]
                if cls == FormattingConfig:
                    if d.get("engine") == "openrouter":
                        d["engine"] = "universal"
                    if "openrouter_model" in d and ("model" not in d or not d.get("model")):
                        d["model"] = d["openrouter_model"]
                return cls(**{k: v for k, v in d.items() if k in valid})

            if "audio" in data:
                self.audio = _safe(AudioConfig, data["audio"])
            if "whisper" in data:
                self.whisper = _safe(WhisperConfig, data["whisper"])
            if "hotkey" in data:
                self.hotkey = _safe(HotkeyConfig, data["hotkey"])
            if "injection" in data:
                self.injection = _safe(InjectionConfig, data["injection"])
            if "formatting" in data:
                self.formatting = _safe(FormattingConfig, data["formatting"])
            if "hud" in data:
                self.hud = _safe(HUDConfig, data["hud"])
            if "mobile_bridge" in data:
                self.mobile_bridge = _safe(MobileBridgeConfig, data["mobile_bridge"])
            if "system" in data:
                self.system = _safe(SystemConfig, data["system"])
            if "translation" in data:
                self.translation = _safe(TranslationConfig, data["translation"])

            # Sync current UI language with i18n engine
            try:
                import i18n
                i18n.set_current_language(getattr(self.system, "ui_language", "en"))
            except Exception:
                pass

            # If migration occurred, persist the sanitized JSON file immediately
            if migrated:
                self.save(safe_path)
        except Exception as e:
            print(f"[Config] Load error: {e}")


    def _auto_tune_first_run_hardware(self):
        """Auto-configure profile on first startup based on available acceleration hardware."""
        try:
            from gpu_monitor import GPUMonitor
            mon = GPUMonitor()
            if not mon.is_cuda_available():
                # On non-CUDA / Office Laptops, default to lightweight low-VRAM / CPU profile
                self.whisper.profile = "low_vram"
                self.whisper.model_size = "small"
                self.whisper.device = "cpu"
                self.whisper.compute_type = "int8"
                print("[Config] First-run detected on CPU/Office laptop. Auto-configured lightweight 'low_vram' profile.")
        except Exception as e:
            print(f"[Config] Hardware auto-tune warning: {e}")


# Singleton instance loaded on boot
config = AppConfig()
config.load()
