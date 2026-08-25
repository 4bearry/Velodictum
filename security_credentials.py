"""
Velodictum - Windows Credential Manager Security Layer
Provides enterprise-grade, hardware/account-bound encrypted storage for API keys & secrets
via native Win32 advapi32.dll CredWriteW / CredReadW / CredDeleteW APIs.

Zero external dependencies - 100% portable on Windows 10/11.
"""
import ctypes
from ctypes import wintypes
import os
from typing import Dict, List, Optional

import threading
from typing import Dict, List, Optional

# Win32 Credential Types & Constants
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
CRED_PERSIST_ENTERPRISE = 3

TARGET_PREFIX = "Velodictum/"
MAX_SECRET_LENGTH = 4096
MAX_KEY_NAME_LENGTH = 256

# Module-level reentrant lock for thread-safe native Win32 vault operations
_vault_lock = threading.RLock()


class CREDENTIAL_ATTRIBUTE(ctypes.Structure):
    _fields_ = [
        ("Keyword", wintypes.LPWSTR),
        ("Flags", wintypes.DWORD),
        ("ValueSize", wintypes.DWORD),
        ("Value", ctypes.POINTER(wintypes.BYTE)),
    ]


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(wintypes.BYTE)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTE)),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


# Win32 Advapi32 bindings
try:
    _advapi32 = ctypes.windll.advapi32
    _kernel32 = ctypes.windll.kernel32

    _CredWriteW = _advapi32.CredWriteW
    _CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
    _CredWriteW.restype = wintypes.BOOL

    _CredReadW = _advapi32.CredReadW
    _CredReadW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    _CredReadW.restype = wintypes.BOOL

    _CredDeleteW = _advapi32.CredDeleteW
    _CredDeleteW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    _CredDeleteW.restype = wintypes.BOOL

    _CredFree = _advapi32.CredFree
    _CredFree.argtypes = [ctypes.c_void_p]
    _HAS_WIN32_VAULT = True
except Exception as e:
    _HAS_WIN32_VAULT = False
    print(f"[SecurityCredentials] Warning: Win32 Credential Vault not accessible: {e}")


def _normalize_target(key_name: str) -> str:
    """Ensure key name is strictly validated and prefixed with namespace."""
    if not key_name or not isinstance(key_name, str):
        raise ValueError("Invalid key_name: must be a non-empty string.")

    if "\0" in key_name or "\r" in key_name or "\n" in key_name:
        raise ValueError("Security violation: Control characters or null bytes detected in credential key name.")

    k = key_name.strip()
    if len(k) > MAX_KEY_NAME_LENGTH:
        raise ValueError(f"Security violation: Credential key name exceeds max length ({MAX_KEY_NAME_LENGTH}).")

    if k.startswith(TARGET_PREFIX):
        return k
    return f"{TARGET_PREFIX}{k}"


def set_credential(key_name: str, secret: str, username: str = "VelodictumUser") -> bool:
    """
    Encrypts and persists a secret in the Windows Credential Manager.
    Thread-safe and guarded against struct buffer overflows.
    If secret is empty, deletes the existing credential.
    """
    with _vault_lock:
        try:
            target = _normalize_target(key_name)
        except Exception as e:
            print(f"[SecurityCredentials] Invalid key name: {e}")
            return False

        if not secret or not secret.strip():
            return delete_credential(key_name)

        if not _HAS_WIN32_VAULT:
            return False

        clean_secret = secret.strip()
        if len(clean_secret) > MAX_SECRET_LENGTH:
            print(f"[SecurityCredentials] Error: Secret length exceeds max threshold of {MAX_SECRET_LENGTH} characters.")
            return False

        try:
            blob = clean_secret.encode("utf-16le")
            blob_len = len(blob)
            blob_buf = (wintypes.BYTE * blob_len).from_buffer_copy(blob)

            cred = CREDENTIAL()
            cred.Flags = 0
            cred.Type = CRED_TYPE_GENERIC
            cred.TargetName = target
            cred.Comment = "Velodictum Hardware-Bound Encrypted Secret"
            cred.CredentialBlobSize = blob_len
            cred.CredentialBlob = ctypes.cast(blob_buf, ctypes.POINTER(wintypes.BYTE))
            cred.Persist = CRED_PERSIST_LOCAL_MACHINE
            cred.AttributeCount = 0
            cred.Attributes = None
            cred.TargetAlias = None
            cred.UserName = username[:128] if username else "VelodictumUser"

            res = bool(_CredWriteW(ctypes.byref(cred), 0))
            if not res:
                err_code = _kernel32.GetLastError()
                print(f"[SecurityCredentials] CredWriteW failed for '{key_name}' with Win32 Error Code: {err_code}")
            return res
        except Exception as e:
            print(f"[SecurityCredentials] Error storing credential '{key_name}': {e}")
            return False


def get_credential(key_name: str) -> Optional[str]:
    """
    Retrieves and decrypts a secret from the Windows Credential Manager.
    Thread-safe, memory-safe with NULL pointer validation.
    Returns None if not found or on error.
    """
    with _vault_lock:
        if not _HAS_WIN32_VAULT:
            return None

        try:
            target = _normalize_target(key_name)
        except Exception:
            return None

        p_cred = ctypes.POINTER(CREDENTIAL)()
        ok = False
        try:
            ok = bool(_CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(p_cred)))
            if not ok or not bool(p_cred):
                return None

            cred = p_cred.contents
            # Pointer & size safety checks
            if not bool(cred.CredentialBlob) or cred.CredentialBlobSize <= 0 or cred.CredentialBlobSize > 65536:
                return None

            raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
            try:
                val = raw.decode("utf-16le").strip()
            except UnicodeDecodeError:
                val = raw.decode("utf-8", errors="replace").strip()

            return val if val else None
        except Exception as e:
            print(f"[SecurityCredentials] Error reading credential '{key_name}': {e}")
            return None
        finally:
            if ok and bool(p_cred):
                try:
                    _CredFree(p_cred)
                except Exception:
                    pass


def delete_credential(key_name: str) -> bool:
    """Deletes a secret from the Windows Credential Manager in a thread-safe manner."""
    with _vault_lock:
        if not _HAS_WIN32_VAULT:
            return False
        try:
            target = _normalize_target(key_name)
            return bool(_CredDeleteW(target, CRED_TYPE_GENERIC, 0))
        except Exception:
            return False


def has_credential(key_name: str) -> bool:
    """Checks if a credential exists in the Windows Credential Manager."""
    with _vault_lock:
        val = get_credential(key_name)
        return bool(val and val.strip())


def mask_secret(secret: Optional[str]) -> str:
    """
    Returns a secure visual representation of a secret (e.g. sk-or••••••••3f9a).
    """
    if not secret or not secret.strip():
        return "Nicht konfiguriert"
    s = secret.strip()
    if len(s) <= 8:
        return "••••••••"
    prefix = s[:5] if len(s) > 12 else s[:3]
    suffix = s[-4:] if len(s) > 12 else s[-2:]
    return f"{prefix}••••••••{suffix}"


# Key Name Constants
KEY_UNIVERSAL_API = "Universal_API_Key"
KEY_OPENAI_API = "OpenAI_API_Key"
KEY_GEMINI_API = "Gemini_API_Key"
KEY_GROQ_API = "Groq_API_Key"
KEY_WHISPER_UNIVERSAL_API = "Whisper_Universal_API_Key"
KEY_WHISPER_GROQ_API = "Whisper_Groq_API_Key"
KEY_WHISPER_OPENAI_API = "Whisper_OpenAI_API_Key"


def migrate_plaintext_keys(config_dict: Dict) -> bool:
    """
    Detects any legacy plaintext keys in config data, migrates them to the
    Windows Credential Vault, and sanitizes the dictionary.
    Thread-safe. Returns True if any migration occurred.
    """
    with _vault_lock:
        migrated = False

        # 1. Formatting Keys
        fmt = config_dict.get("formatting", {})
        if isinstance(fmt, dict):
            key_mappings = [
                ("api_key", KEY_UNIVERSAL_API),
                ("openrouter_api_key", KEY_UNIVERSAL_API),
                ("openai_api_key", KEY_OPENAI_API),
                ("gemini_api_key", KEY_GEMINI_API),
                ("groq_api_key", KEY_GROQ_API),
            ]
            for field, vault_target in key_mappings:
                val = fmt.get(field)
                if val and isinstance(val, str) and val.strip() and not val.startswith("••••"):
                    set_credential(vault_target, val.strip())
                    fmt[field] = None
                    migrated = True

        # 2. Whisper STT Keys
        wh = config_dict.get("whisper", {})
        if isinstance(wh, dict):
            stt_mappings = [
                ("universal_api_key", KEY_WHISPER_UNIVERSAL_API),
                ("openrouter_api_key", KEY_WHISPER_UNIVERSAL_API),
                ("custom_api_key", KEY_WHISPER_UNIVERSAL_API),
                ("groq_api_key", KEY_WHISPER_GROQ_API),
                ("openai_api_key", KEY_WHISPER_OPENAI_API),
            ]
            for field, vault_target in stt_mappings:
                val = wh.get(field)
                if val and isinstance(val, str) and val.strip() and not val.startswith("••••"):
                    set_credential(vault_target, val.strip())
                    wh[field] = None
                    migrated = True

        return migrated

