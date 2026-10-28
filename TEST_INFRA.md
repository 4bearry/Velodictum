# Velodictum UI Redesign Test Infrastructure (`TEST_INFRA.md`)

## 1. Overview & Architecture
This document defines the automated End-to-End (E2E) testing infrastructure for the **Velodictum UI Redesign** track. Velodictum is a modern Windows 11 PyQt6 dictation desktop application featuring:
- **Liquid Glass & Fluent Design System** (`gui/theme.py`)
- **Main Dashboard Architecture & Progressive Disclosure** (`gui/dashboard_window.py`)
- **Ultra-Compact Floating HUD Overlay** (`gui/floating_hud.py`)
- **Quick-Capture Scratchpad Editor** (`gui/scratchpad_window.py`)
- **Centralized Event Bus Singleton** (`gui/signals.py`)

The test suite enforces zero logic regressions, strict interface contract compliance, boundary resilience, cross-component harmony, and complete real-world dictation lifecycle coverage.

---

## 2. Environment & Prerequisites

### 2.1 Python Environment & Tooling
All automated tests must be executed using the dedicated repository virtual environment to ensure all binary dependencies (PyQt6, pyperclip, etc.) resolve properly:
- **Python Binary**: `.venv\Scripts\python.exe` (Python 3.13)
- **Test Runner**: `pytest` (v9.1+)
- **GUI Framework**: PyQt6
- **Headless Platform Driver**: `QT_QPA_PLATFORM=offscreen`
- **Module Resolution**: `PYTHONPATH=core;.`

### 2.2 Execution Command
```powershell
cmd /c "set QT_QPA_PLATFORM=offscreen&& set PYTHONPATH=core;.&& .venv\Scripts\python.exe -m pytest tests/test_ui_redesign_e2e.py -v"
```

---

## 3. 4-Tier Test Architecture & Taxonomy

The E2E test suite (`tests/test_ui_redesign_e2e.py`) strictly implements the 4-tier testing methodology:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Tier 4: Workload Scenarios                        │
│  - Complete Dictation Lifecycle (HUD -> Audio Stream -> STT -> Pad)   │
├────────────────────────────────────────────────────────────────────────┤
│                   Tier 3: Cross-Feature Combinations                   │
│  - Signal-Slot Roundtrip with Styled UI                                │
│  - Simultaneous Bilingual Toggle Across All 3 Windows                  │
│  - Settings Accordion Expansion Under Active Search Query              │
├────────────────────────────────────────────────────────────────────────┤
│                  Tier 2: Boundary & Corner Cases                       │
│  - Empty Transcription Text Payloads                                   │
│  - Extreme & Negative Audio RMS Metering Values                        │
│  - Rapid State Transition Bursts & Race Prevention                     │
│  - Invalid Language Code Retranslation Fallbacks                       │
│  - Window Geometry & Minimum Resizing Bounds                           │
│  - Special Characters & Regex Edge Cases in Search Filtering           │
├────────────────────────────────────────────────────────────────────────┤
│                     Tier 1: Feature Coverage                           │
│  - Clean Syntax Compilation & Import of All GUI Modules               │
│  - Centralized Theme Tokens Contract (ThemeColors, Typography, Metrics)│
│  - Fluent Dark Glass QSS Completeness & Validity                       │
│  - Polymorphic Window Backdrop (int HWND & QWidget support)            │
│  - Offscreen Headless Window Instantiation                             │
│  - Floating HUD 6-State Lifecycle Integrity                            │
│  - Scratchpad Action Toolbar Buttons & Attribute Preservation          │
│  - Dashboard 3 Tabs & 7 Settings Cards Preservation                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Interface Contracts Under Test

### 4.1 Theme Engine (`gui/theme.py`)
- **Theme Tokens**: Must expose `ThemeColors`, `ThemeTypography`, and `ThemeMetrics`.
- **Global Stylesheet**: `get_stylesheet()` must return a valid, non-empty QSS string defining styling for all standard Qt controls (`QWidget`, `QFrame`, `QTabBar`, `QPushButton`, `QSlider`, `QMenu`, `QToolTip`, `QTextEdit`, `QScrollBar`).
- **Polymorphic Backdrop**: `apply_window_backdrop(target: Union[int, QWidget])` must accept either an integer window handle (HWND) or a `QWidget` instance without raising exceptions.

### 4.2 Floating HUD (`gui/floating_hud.py`)
- **Window Hierarchy & Properties**: Frameless, tool window, translucent canvas (`460x68`), non-focus-stealing.
- **6-State Lifecycle Machine**:
  - `recording`: Started via `signals.recording_started`.
  - `voice_edit`: Started via `signals.voice_edit_started`.
  - `transcribing`: Triggered via `signals.transcription_started` and `signals.formatting_started`.
  - `done`: Triggered via `signals.transcription_completed` and `signals.voice_edit_completed`.
  - `error`: Triggered via `signals.transcription_failed`, `signals.injection_blocked`, and `signals.recording_cancelled`.
- **Waveform Metering**: `on_audio_level(rms: float)` scaling RMS cleanly into `[0.0, 1.0]`.
- **Dynamic Localization**: Implements `retranslate_ui(lang_code: Optional[str])`.

### 4.3 Scratchpad Window (`gui/scratchpad_window.py`)
- **Widget Attributes**: Must preserve `btn_mic`, `btn_structure`, `btn_copy`, `btn_clear`, `text_edit`, `title_lbl`, `lbl_stats`.
- **Toolbar Actions**: 1-click dictation toggle, AI note structuring, clipboard copy with confirmation feedback, editor clear.
- **Live Counters**: Word and character counts updated immediately on text change.
- **Localization**: Supports dynamic `retranslate_ui(lang_code: Optional[str])`.

### 4.4 Dashboard Window (`gui/dashboard_window.py`)
- **Navigation Structure**: 3 primary tabs (`self.tab_studio`, `self.tab_library`, `self.tab_settings`).
- **Settings Cards**: Exactly 7 `CollapsibleSettingsCard` elements stored in `all_settings_cards`.
- **Card Aliases**: Backward compatibility aliases preserved (`card_llm`, `card_sound`, `card_mob`, `card_sys`).
- **Engine Switching Containers**: 6 engine sub-containers (`rules_container`, `universal_container`, etc.).
- **Progressive Disclosure**: Support for `_expand_all_settings()`, `_collapse_all_settings()`, and search filtering via `_on_settings_search_changed(query)`.

---

## 5. Test Suite Implementation Details

- **Test Suite Location**: `tests/test_ui_redesign_e2e.py`
- **Class Organization**:
  1. `TestTier1FeatureCoverage`: Sanity imports, design tokens, stylesheet rules, polymorphic backdrop, window instantiations, 6-state HUD transitions, scratchpad toolbar, dashboard tab & card preservation.
  2. `TestTier2BoundaryAndCornerCases`: Zero/empty transcription, extreme audio levels (`rms < 0` and `rms > 1.0`), rapid signal bursts, invalid language code fallback, resizing bounds, search filtering edge cases.
  3. `TestTier3CrossFeatureCombinations`: Signal roundtrip under active stylesheet, simultaneous bilingual toggle across all 3 windows, accordion expansion while search filter is active.
  4. `TestTier4RealWorldWorkloadScenarios`: Full end-to-end dictation session from trigger to clipboard copy and HUD dismissal.

---

## 6. Verification and Reporting Protocol

1. **Clean Offscreen Execution**: All tests must run without requiring a physical display or user interaction.
2. **State Cleanup**: Every test fixture instantiates isolated mocks and explicitly terminates active Qt animation timers (`anim_timer`, `hide_timer`) upon teardown to prevent timer leakage and cross-test pollution.
3. **Escalation Protocol**: Tests strictly assert against specifications defined in `PROJECT.md` and `ORIGINAL_REQUEST.md`. Any failing assertion due to missing implementation features must be escalated directly to the corresponding milestone track without modifying the test assertion to pass prematurely.
