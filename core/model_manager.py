"""
Velodictum - Whisper Model Downloader & Storage Path Manager
Provides complete catalog metadata, disk space telemetry, custom directory routing,
and background model download/deletion management for faster-whisper.
"""
import os
import shutil
import threading
from typing import Dict, List, Optional, Callable, Any

import re
from config import config, validate_safe_filepath


from i18n import tr


def get_models_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": "tiny",
            "name": "Whisper Tiny",
            "size_mb": 75,
            "vram_gb": 0.4,
            "speed": tr("whisper_speed_tiny"),
            "accuracy": tr("whisper_acc_tiny"),
            "desc": tr("whisper_desc_tiny"),
        },
        {
            "id": "base",
            "name": "Whisper Base",
            "size_mb": 145,
            "vram_gb": 0.6,
            "speed": tr("whisper_speed_base"),
            "accuracy": tr("whisper_acc_base"),
            "desc": tr("whisper_desc_base"),
        },
        {
            "id": "small",
            "name": "Whisper Small",
            "size_mb": 480,
            "vram_gb": 1.0,
            "speed": tr("whisper_speed_small"),
            "accuracy": tr("whisper_acc_small"),
            "desc": tr("whisper_desc_small"),
        },
        {
            "id": "medium",
            "name": "Whisper Medium",
            "size_mb": 1500,
            "vram_gb": 2.5,
            "speed": tr("whisper_speed_medium"),
            "accuracy": tr("whisper_acc_medium"),
            "desc": tr("whisper_desc_medium"),
        },
        {
            "id": "large-v3-turbo",
            "name": "Whisper Large-v3 Turbo",
            "size_mb": 1600,
            "vram_gb": 2.5,
            "speed": tr("whisper_speed_turbo"),
            "accuracy": tr("whisper_acc_turbo"),
            "desc": tr("whisper_desc_turbo"),
        },
        {
            "id": "large-v3",
            "name": "Whisper Large-v3",
            "size_mb": 3100,
            "vram_gb": 4.5,
            "speed": tr("whisper_speed_large"),
            "accuracy": tr("whisper_acc_large"),
            "desc": tr("whisper_desc_large"),
        },
    ]

WHISPER_MODELS_CATALOG = get_models_catalog()


def _validate_model_id(model_id: str) -> str:
    """
    Strictly validates a faster-whisper model identifier to prevent Directory Traversal.
    Allows only alphanumeric characters, underscores, hyphens, and dots.
    Rejects path separators (/, \\), parent directory references (..), and null bytes.
    """
    if not model_id or not isinstance(model_id, str):
        raise ValueError("Invalid model ID: must be a non-empty string.")

    if "\0" in model_id:
        raise ValueError("Security violation: Null byte detected in model ID.")

    clean_id = model_id.strip()
    if "/" in clean_id or "\\" in clean_id or ".." in clean_id:
        raise ValueError(f"Security violation: Path traversal characters detected in model ID '{model_id}'.")

    if not re.match(r"^[a-zA-Z0-9_\.\-]+$", clean_id):
        raise ValueError(f"Security violation: Model identifier contains illegal characters: '{model_id}'.")

    return clean_id


class WhisperModelManager:

    def __init__(self):
        self._lock = threading.Lock()
        self._active_downloads: Dict[str, float] = {}

    def get_models_dir(self) -> str:
        """Returns the configured custom models directory or default ~/.cache/whisper_models."""
        custom = getattr(config.whisper, "models_dir", None)
        if custom and isinstance(custom, str) and custom.strip():
            try:
                path = validate_safe_filepath(custom.strip())
                os.makedirs(path, exist_ok=True)
                return path
            except Exception as e:
                print(f"[ModelManager] Invalid custom models directory, falling back to default: {e}")

        default_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper_models")
        safe_default = validate_safe_filepath(default_dir)
        os.makedirs(safe_default, exist_ok=True)
        return safe_default

    def set_models_dir(self, new_dir: str) -> bool:
        """Configures a custom models storage directory (e.g. on D:/ or E:/ drive)."""
        if not new_dir or not new_dir.strip():
            config.whisper.models_dir = None
            config.save()
            return True

        try:
            abs_path = validate_safe_filepath(new_dir.strip())
            os.makedirs(abs_path, exist_ok=True)
            config.whisper.models_dir = abs_path
            config.save()
            return True
        except Exception as e:
            print(f"[ModelManager] Cannot set models directory '{new_dir}': {e}")
            return False

    def get_disk_space(self, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """Calculates total, used, and free disk space for the target drive."""
        try:
            path = validate_safe_filepath(target_dir) if target_dir else self.get_models_dir()
            usage = shutil.disk_usage(path)
            total_gb = usage.total / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_pct = (usage.free / usage.total) * 100 if usage.total > 0 else 0
            return {
                "path": path,
                "total_gb": round(total_gb, 1),
                "used_gb": round(used_gb, 1),
                "free_gb": round(free_gb, 1),
                "free_percent": round(free_pct, 1),
            }
        except Exception as e:
            fallback_path = target_dir or ""
            print(f"[ModelManager] Disk usage error for '{fallback_path}': {e}")
            return {
                "path": fallback_path,
                "total_gb": 0.0,
                "used_gb": 0.0,
                "free_gb": 0.0,
                "free_percent": 0.0,
            }

    def is_model_downloaded(self, model_id: str, custom_dir: Optional[str] = None) -> bool:
        """Checks if a given faster-whisper model exists in the target storage directory."""
        try:
            clean_id = _validate_model_id(model_id)
            directory = validate_safe_filepath(custom_dir) if custom_dir else self.get_models_dir()
        except Exception:
            return False

        if not os.path.exists(directory):
            return False

        # 1) Preferred layout: each model lives in its own named subdirectory.
        #    Name is either the model-id directly (e.g. "large-v3-turbo") or the
        #    huggingface_hub cache convention ("models--Systran--faster-whisper-...").
        for entry in os.listdir(directory):
            sub_path = os.path.join(directory, entry)
            if not os.path.isdir(sub_path):
                continue
            if clean_id.lower() in entry.lower():
                files = os.listdir(sub_path)
                if files and (
                    "snapshots" in files
                    or "model.bin" in files
                    or "model.safetensors" in files
                    or len(files) >= 3
                ):
                    return True

        # 2) Legacy flat layout: model files downloaded directly into models_dir.
        #    Only matches if models_dir itself is named after the model.
        direct_files = set(os.listdir(directory))
        if "model.bin" in direct_files and "config.json" in direct_files:
            dir_low = os.path.basename(directory).lower()
            if clean_id.lower() in dir_low:
                return True

        return False

    def get_model_dir(self, model_id: str, base_dir: Optional[str] = None) -> str:
        """Returns the dedicated per-model subdirectory path, strictly validated against traversal."""
        clean_id = _validate_model_id(model_id)
        root = validate_safe_filepath(base_dir) if base_dir else self.get_models_dir()
        target = os.path.abspath(os.path.join(root, clean_id))
        if os.path.commonpath([root, target]) != root:
            raise ValueError(f"Security violation: Target model path '{target}' escapes root directory '{root}'.")
        return target

    def get_models_status(self, custom_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns the full catalog of models with live download status and on-disk presence."""
        models_dir = validate_safe_filepath(custom_dir) if custom_dir else self.get_models_dir()
        active_model = getattr(config.whisper, "model_size", "large-v3-turbo")

        status_list = []
        for item in get_models_catalog():
            m_id = item["id"]
            downloaded = self.is_model_downloaded(m_id, models_dir)
            is_active = (m_id.lower() == active_model.lower())
            status_list.append({
                **item,
                "is_downloaded": downloaded,
                "is_active": is_active,
                "storage_dir": models_dir,
            })
        return status_list

    def download_model_sync(self, model_id: str, custom_dir: Optional[str] = None) -> bool:
        """Synchronously downloads the requested model into a dedicated per-model subdirectory."""
        try:
            clean_id = _validate_model_id(model_id)
            target_dir = self.get_model_dir(clean_id, custom_dir)
            os.makedirs(target_dir, exist_ok=True)
            from faster_whisper import download_model
            print(f"[ModelManager] Downloading '{clean_id}' to '{target_dir}'...")
            download_model(clean_id, output_dir=target_dir)
            print(f"[ModelManager] Successfully downloaded '{clean_id}'.")
            return True
        except Exception as e:
            print(f"[ModelManager] Error downloading model '{model_id}': {e}")
            try:
                if 'target_dir' in locals() and os.path.exists(target_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
            except Exception:
                pass
            return False

    def download_model_async(
        self,
        model_id: str,
        custom_dir: Optional[str] = None,
        on_progress: Optional[Callable[[str, float], None]] = None,
        on_finished: Optional[Callable[[str, bool, str], None]] = None,
    ):
        """Asynchronously downloads a Whisper model in a daemon worker thread."""
        def _worker():
            with self._lock:
                self._active_downloads[model_id] = 0.0

            if on_progress:
                on_progress(model_id, 10.0)

            ok = self.download_model_sync(model_id, custom_dir)

            with self._lock:
                self._active_downloads.pop(model_id, None)

            if on_progress:
                on_progress(model_id, 100.0 if ok else 0.0)

            if on_finished:
                msg = "Erfolgreich heruntergeladen" if ok else "Download fehlgeschlagen"
                on_finished(model_id, ok, msg)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def delete_model(self, model_id: str, custom_dir: Optional[str] = None) -> bool:
        """Deletes downloaded model files from the storage directory to free up space."""
        try:
            clean_id = _validate_model_id(model_id)
            target_dir = validate_safe_filepath(custom_dir) if custom_dir else self.get_models_dir()
        except Exception as e:
            print(f"[ModelManager] Security rejection on delete_model: {e}")
            return False

        if not os.path.exists(target_dir):
            return False

        deleted_any = False
        try:
            for entry in os.listdir(target_dir):
                sub_path = os.path.abspath(os.path.join(target_dir, entry))
                # Ensure entry is strictly a subfolder of target_dir
                if os.path.commonpath([target_dir, sub_path]) != target_dir or sub_path == target_dir:
                    continue

                if os.path.isdir(sub_path) and clean_id.lower() in entry.lower():
                    shutil.rmtree(sub_path, ignore_errors=True)
                    deleted_any = True
                    print(f"[ModelManager] Deleted model folder: {sub_path}")
            return deleted_any
        except Exception as e:
            print(f"[ModelManager] Error deleting model '{model_id}': {e}")
            return False


# Global singleton instance
model_manager = WhisperModelManager()
