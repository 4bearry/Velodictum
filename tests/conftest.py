import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(PROJECT_ROOT, "core")

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(1, PROJECT_ROOT)

import pytest
import security_credentials as sec
import config as config_mod

# Prevent dual-module loading between `import security_credentials` and `from core import security_credentials`
sys.modules["core.security_credentials"] = sec
sys.modules["core.config"] = config_mod

_SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")


def _snapshot_credentials():
    try:
        keys = [
            sec.KEY_OPENAI_API,
            sec.KEY_GEMINI_API,
            sec.KEY_GROQ_API,
            sec.KEY_OPENROUTER_API,
            sec.KEY_UNIVERSAL_API,
            sec.KEY_WHISPER_UNIVERSAL_API,
            sec.KEY_MOBILE_BRIDGE_TOKEN,
        ]
        snap = {}
        for k in keys:
            val = sec.get_credential(k)
            if val == "sk-ant-adversarial-test-key-998877":
                sec.delete_credential(k)
                val = None
            snap[k] = val
        return snap
    except Exception:
        return {}


def _restore_credentials(snap):
    if not snap:
        return
    try:
        for k, val in snap.items():
            if val is not None:
                sec.set_credential(k, val)
            else:
                sec.delete_credential(k)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _isolate_user_settings_and_credentials():
    settings_bytes = None
    if os.path.exists(_SETTINGS_PATH):
        with open(_SETTINGS_PATH, "rb") as f:
            settings_bytes = f.read()
    cred_snap = _snapshot_credentials()
    try:
        yield
    finally:
        _restore_credentials(cred_snap)
        if settings_bytes is not None:
            try:
                with open(_SETTINGS_PATH, "wb") as f:
                    f.write(settings_bytes)
                config_mod.config.load()
            except Exception:
                pass
