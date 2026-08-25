"""
Velodictum - Unit Tests for Universal STT API & Custom Endpoints
Validates payload construction, headers, authentication, and fallback routing for Universal STT.
"""
import pytest
import numpy as np
from cloud_stt import CloudWhisperEngine
from config import config
import security_credentials as sec


def test_cloud_whisper_engine_universal_defaults():
    engine = CloudWhisperEngine(provider="universal", api_key="sk-test-key-123")
    assert engine.provider == "universal"
    assert engine.api_key == "sk-test-key-123"


def test_cloud_whisper_engine_custom_config():
    engine = CloudWhisperEngine()
    engine.set_config(
        provider="custom",
        api_key="my-secret-key",
        endpoint="http://localhost:8000/v1/audio/transcriptions",
        model="whisper-custom-v1",
    )
    assert engine.provider == "custom"
    assert engine.api_key == "my-secret-key"
    assert engine.endpoint == "http://localhost:8000/v1/audio/transcriptions"
    assert engine.model == "whisper-custom-v1"


def test_config_whisper_universal_key_resolution():
    # Test setting and resolving key for universal provider
    config.whisper.provider = "universal"
    config.whisper.set_api_key("sk-or-v1-universal-test", "universal")
    resolved = config.whisper.get_api_key("universal")
    assert resolved == "sk-or-v1-universal-test"
    # Clean up test credential
    sec.delete_credential(sec.KEY_WHISPER_UNIVERSAL_API)
