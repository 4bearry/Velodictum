"""
Tests for Velodictum Clipboard Safety, Leak Prevention, and Zero-Contamination
"""
import time
import pytest
from core.text_injector import (
    safe_clipboard_copy,
    safe_clipboard_paste,
    grab_selected_text_win32,
    TextInjector,
)
from core.config import config


def test_safe_clipboard_unicode_roundtrip():
    """Verify that unicode characters, umlauts, formatting, and long strings roundtrip cleanly."""
    test_text = "Velodictum Test: Äpfel, Übertragung, Größe, €100, ⚡ 🧠, \nMehrzeilig!"
    assert safe_clipboard_copy(test_text)
    pasted = safe_clipboard_paste()
    assert pasted == test_text


def test_grab_selected_text_never_leaves_sentinel():
    """Verify that grab_selected_text_win32 leaves NO sentinel or weird string in clipboard when nothing is selected."""
    orig_text = "My Original User Clipboard Content 12345"
    safe_clipboard_copy(orig_text)
    
    # Trigger grab on inactive or background process
    grabbed = grab_selected_text_win32()
    
    current_clip = safe_clipboard_paste()
    # Check that no sentinel like __VELODICTUM_GRAB_ exists
    assert "__VELODICTUM_GRAB_" not in current_clip
    assert "VELODICTUM" not in current_clip or "VELODICTUM" in orig_text


def test_text_injector_keeps_dictated_text_when_restore_is_false():
    """When restore_clipboard is False (new default), dictated text remains in clipboard so user can paste manually."""
    config.injection.restore_clipboard = False
    orig_text = "Old Clipboard"
    safe_clipboard_copy(orig_text)
    
    injector = TextInjector(auto_paste=False, restore_clipboard=False)
    dictated_text = "Hier ist mein diktierter Text, den ich überall mit Strg+V einfügen kann."
    success = injector.inject(dictated_text)
    assert success
    
    # Wait to ensure no background thread overwrites it
    time.sleep(0.1)
    
    current_clip = safe_clipboard_paste()
    assert current_clip == dictated_text


def test_text_injector_restores_clipboard_when_enabled():
    """When restore_clipboard is True, previous clipboard is restored after delay."""
    config.injection.restore_clipboard = True
    orig_text = "Preserved Original Clipboard"
    safe_clipboard_copy(orig_text)
    
    injector = TextInjector(auto_paste=False, restore_clipboard=True, restore_delay=0.05)
    dictated_text = "Temporärer Diktattext"
    success = injector.inject(dictated_text)
    assert success
    
    # Wait for async restore
    time.sleep(0.12)
    
    current_clip = safe_clipboard_paste()
    assert current_clip == orig_text
