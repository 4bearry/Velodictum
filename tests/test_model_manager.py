"""
Velodictum - Whisper Model Manager & Storage Path Test Suite
Verifies:
1. Catalog models enumeration and status metadata.
2. Custom model storage directory configuration.
3. Disk space telemetry calculation (total_gb, free_gb, percent).
4. Custom directory creation and fallback handling.
"""
import os
import tempfile
from config import config
from model_manager import model_manager, WHISPER_MODELS_CATALOG


def test_model_manager():
    print("--- TEST: Whisper Model Manager & Storage Path ---")

    # 1. Verify Catalog
    assert len(WHISPER_MODELS_CATALOG) >= 6, "Expected at least 6 Whisper models in catalog"
    model_ids = [m["id"] for m in WHISPER_MODELS_CATALOG]
    assert "large-v3-turbo" in model_ids
    assert "large-v3" in model_ids
    assert "small" in model_ids

    # 2. Verify Disk Space calculation
    usage = model_manager.get_disk_space()
    print(f"  Disk Space: {usage['free_gb']} GB free / {usage['total_gb']} GB ({usage['free_percent']}%) at {usage['path']}")
    assert usage["total_gb"] > 0, "Total disk space must be > 0"
    assert usage["free_gb"] >= 0, "Free disk space must be >= 0"

    # 3. Verify Custom Storage Directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_target = os.path.join(tmp_dir, "custom_whisper_models")
        ok = model_manager.set_models_dir(custom_target)
        assert ok, "Failed to set custom models directory"
        assert model_manager.get_models_dir() == os.path.abspath(custom_target)
        assert os.path.exists(custom_target), "Custom models directory must be created"

        # Verify status listing on new custom dir
        status = model_manager.get_models_status(custom_target)
        assert len(status) == len(WHISPER_MODELS_CATALOG)
        for s in status:
            assert s["storage_dir"] == custom_target
            assert not s["is_downloaded"], "New empty directory should report model not downloaded"

        # Reset to default
        model_manager.set_models_dir("")
        assert config.whisper.models_dir is None

    print("[OK] [MODEL MANAGER TEST PASSED] Model catalog, custom storage routing and disk telemetry verified!")


if __name__ == "__main__":
    test_model_manager()
