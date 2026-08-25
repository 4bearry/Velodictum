"""
Velodictum - Windows Credential Manager & Security Test Suite
Verifies:
1. Native Win32 Credential Vault write/read/delete operations.
2. Auto-migration of legacy plaintext keys from JSON dictionaries.
3. Plaintext secret sanitization during config.save().
4. Security key masking.
"""
import json
import os
import tempfile
import security_credentials as sec
from config import AppConfig, config


def test_native_vault_crud():
    print("--- TEST 1: Native Windows Credential Vault CRUD ---")
    test_key = "Test_Secret_Key_123"
    test_val = "sk-test-live-key-998877665544"

    # Store
    ok = sec.set_credential(test_key, test_val)
    assert ok, "Failed to store credential in Windows Vault"

    # Exists
    assert sec.has_credential(test_key), "Credential should exist in Vault"

    # Retrieve
    retrieved = sec.get_credential(test_key)
    assert retrieved == test_val, f"Expected {test_val}, got {retrieved}"

    # Delete
    del_ok = sec.delete_credential(test_key)
    assert del_ok, "Failed to delete credential from Windows Vault"
    assert not sec.has_credential(test_key), "Credential should no longer exist"
    print("[OK] [TEST 1 PASSED] Native Windows Vault CRUD verified!")


def test_key_masking():
    print("\n--- TEST 2: Key Visual Masking ---")
    assert sec.mask_secret("") == "Nicht konfiguriert"
    assert sec.mask_secret(None) == "Nicht konfiguriert"
    masked = sec.mask_secret("sk-or-v1-abcdef1234567890")
    assert "••••" in masked
    assert "sk-or" in masked
    assert "7890" in masked
    assert "abcdef" not in masked, "Sensitive middle part of key must not be visible"
    print(f"  Masked Sample: {masked}")
    print("[OK] [TEST 2 PASSED] Key Visual Masking verified!")


def test_plaintext_migration_and_sanitization():
    print("\n--- TEST 3: Plaintext Migration & JSON Sanitization ---")
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_settings_path = os.path.join(tmp_dir, "test_settings.json")
        fake_data = {
            "formatting": {
                "engine": "universal",
                "api_key": "sk-or-legacy-plaintext-key-1234",
                "openai_api_key": "sk-openai-plaintext-5678",
            },
            "whisper": {
                "provider": "grok",
                "groq_api_key": "gsk-groq-plaintext-9999",
            }
        }
        with open(fake_settings_path, "w", encoding="utf-8") as f:
            json.dump(fake_data, f)

        # Create temporary AppConfig and load from fake settings
        cfg = AppConfig()
        cfg.load(fake_settings_path)

        # 1. Verify secrets were migrated to Windows Vault
        assert sec.get_credential(sec.KEY_UNIVERSAL_API) == "sk-or-legacy-plaintext-key-1234"
        assert sec.get_credential(sec.KEY_OPENAI_API) == "sk-openai-plaintext-5678"
        assert sec.get_credential(sec.KEY_WHISPER_GROQ_API) == "gsk-groq-plaintext-9999"

        # 2. Verify settings.json on disk was sanitized (no plaintext keys remain in JSON)
        with open(fake_settings_path, "r", encoding="utf-8") as f:
            saved_content = f.read()

        assert "sk-or-legacy-plaintext-key-1234" not in saved_content, "Plaintext API key must not be on disk"
        assert "sk-openai-plaintext-5678" not in saved_content, "Plaintext OpenAI key must not be on disk"
        assert "gsk-groq-plaintext-9999" not in saved_content, "Plaintext Groq key must not be on disk"

        # 3. Clean up test credentials from vault
        sec.delete_credential(sec.KEY_UNIVERSAL_API)
        sec.delete_credential(sec.KEY_OPENAI_API)
        sec.delete_credential(sec.KEY_WHISPER_GROQ_API)

    print("[OK] [TEST 3 PASSED] Auto-Migration & JSON Sanitization verified!")


if __name__ == "__main__":
    test_native_vault_crud()
    test_key_masking()
    test_plaintext_migration_and_sanitization()
    print("\n==================================================")
    print("ALL SECURITY CREDENTIAL TESTS PASSED! 100% SUCCESS")
    print("==================================================")
