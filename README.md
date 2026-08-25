# Velodictum Desktop (Windows 11 Studio Edition)

> **High-Performance, Local-First AI Dictation & Voice Transformation Assistant for Windows 11 / 10**  
> An open-source, provider-agnostic desktop alternative to macOS-only voice dictation tools (Wispr Flow / Superwhisper).

[![Built by 4bearyy](https://img.shields.io/badge/Author-4bearyy-7c3aed?style=flat-square)](https://github.com/4bearyy)

[![Platform - Windows 11](https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-0078d4?style=flat-square)](https://microsoft.com/windows)
[![STT - Faster Whisper](https://img.shields.io/badge/STT-faster--whisper%20(CUDA%20%2F%20CPU)-10b981?style=flat-square)](https://github.com/SYSTRAN/faster-whisper)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square)](https://python.org)
[![License - MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## Overview

**Velodictum** is a local-first, low-latency AI dictation and voice-editing suite built specifically for Windows. It captures speech in real time, optionally processes it through a dedicated semantic AI flow layer (for disfluency removal, self-correction resolution, and tone transformation), and injects clean, context-aware text directly into any focused desktop application.

```mermaid
flowchart TD
    A["Microphone Input (16kHz Mono)"] --> B["Low-Latency Audio Capture (sounddevice)"]
    B --> C{"STT Transcription Provider"}
    C -->|Local CUDA / CPU| D["faster-whisper (CTranslate2)"]
    C -->|Cloud Grok AI / Groq| E["Whisper-Large-v3 (<80ms)"]
    C -->|Cloud OpenAI / Universal| F["Custom / whisper-1 Endpoint"]
    D --> G["Verbatim Transcript"]
    E --> G
    F --> G
    G --> H{"Operating Mode"}
    H -->|Rohdiktat (Raw Bypass)| L["Atomic Text Injector (Win32 API)"]
    H -->|Intelligenter Flow| I["The Flow Layer (LLM Post-Processing)"]
    I -->|Local 100% Offline| J["Ollama (Qwen 2.5 7B / Llama)"]
    I -->|Universal API / Cloud| K["OpenRouter, Gemini, Groq, DeepSeek, OpenAI"]
    J --> L
    K --> L
    L --> M["Active Window (VS Code, Outlook, Slack, Browser, Word)"]
```

---

## Key Features

### 1. Two-Tier Dictation & Tone Architecture
* **Tier 1 (Betriebsmodus)**:
  * **Intelligenter Flow (`flow`)**: Full AI post-processing pipeline. Strips hesitation sounds (*"äh"*, *"um"*), resolves mid-sentence corrections (*"ich brauche drei, ach nein, vier Schrauben"*), and formats bulleted lists automatically.
  * **Rohdiktat (`raw`)**: 1:1 acoustic Whisper bypass. Outputs exactly what was spoken with zero LLM alterations.
* **Tier 2 (Tonalität & Stil)**:
  * *Standard*: Balanced, clear, professional everyday tone.
  * *Formell (Sie)*: Formal German corporate phrasing.
  * *Locker (Du)*: Casual, direct communication for Slack/Discord/WhatsApp.
  * *Prägnant & Direkt*: Compact, bullet-ready, to-the-point sentences.
  * *Akademisch & Gehoben*: High-register vocabulary and precise formulations.

### 2. Universal API & Multi-Engine Intelligence
* **Universal OpenAI-Compatible API**: Connect seamlessly to OpenRouter (100+ models), Together AI, DeepSeek, Fireworks AI, vLLM, LiteLLM, or local endpoints with automatic provider detection and live latency testing.
* **100% Offline Local Privacy**: Built-in native support for Ollama running `qwen2.5:7b` on your local GPU.
* **Zero Data Retention (ZDR)**: Native support for OpenRouter's privacy-first routing (`data_collection: "deny"`, `zdr: true`).

### 3. In-Place Voice Editor ("Velodictum Transform")
* Highlight text in any application and press `Ctrl + Alt + Space` (or `Ctrl + Alt + Z`).
* Speak your transformation instruction (e.g. *"Mach das förmlicher"*, *"Übersetze ins Englische"*, *"Fasse das in 3 Stichpunkten zusammen"*).
* Velodictum grabs the selection, transforms it, and replaces the highlighted text atomically.

### 4. Floating Mini-HUD & Visual Feedback
* Lightweight, hardware-accelerated Liquid Glass overlay with spring physics.
* Dynamic 36-bar 60 FPS real-time audio visualizer.
* Zero idle CPU overhead and customizable screen positioning.

### 5. Personal Fachwörterbuch (Custom Vocabulary)
* Injects technical acronyms (`CUDA`, `PyQt6`, `FastAPI`), personal names, and specialized domain terms directly into Whisper's acoustic decoder prompt for perfect recognition.

### 6. Procedural DSP Audio Feedback
* 0ms latency in-memory procedural sound synthesis (`pyfxr` / NumPy) with tactile acoustic themes (*Velodictum Silk*, *Taptic Glass*, *Haptic Pop*, *Quantum Precision*). No harsh system beeps.

### 7. Audio Power Features
* **Auto-Ducking**: Automatically attenuates background audio (Spotify, YouTube, games) during active dictation.
* **Anti-Clipping Soft Limiter & Pre-Gain**: Input gain adjustment (-6 dB to +9.5 dB) with real-time level calibration.
* **Three-Way Cancellation**: Cancel ongoing dictation instantly via `Escape`, right-click on the HUD, or spoken abort commands (*"Abbrechen"*).

### 8. Mobile LAN Bridge
* Built-in zero-config local HTTP server with QR-code pairing to use your smartphone as a wireless desktop microphone.

---

## Global Hotkeys

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| `Ctrl + Alt + Space` *(or `F8`)* | Push-to-Talk / Toggle Dictation | Captures speech and injects formatted text into the active window |
| `Ctrl + Shift + D` | WhisperFlow Scratchpad | Opens the standalone note-taking scratchpad with 1-click AI structuring |
| `Ctrl + Alt + Z` | In-Place Voice Editor / Transform | Rewrites currently selected text in any app via voice instruction |
| `Escape` | Instant Cancel | Discards current recording immediately without injection |

---

## Installation & Setup

### Prerequisites
* **Windows 11 or Windows 10 (64-bit)**
* **Python 3.10 - 3.13**
* **NVIDIA GPU with CUDA support** (Optional, recommended: RTX 3060/4060+ with $\ge$ 6 GB VRAM; CPU mode is supported automatically).

### 1. Clone the Repository
```powershell
git clone https://github.com/<username>/Velodictum.git
cd Velodictum
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

*(Optional: For GPU acceleration with PyTorch / CUDA)*:
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 4. Run the Application
Double-click [`run.bat`](run.bat) or run:
```powershell
python main.py
```

---

## Building a Standalone Executable

To bundle Velodictum into a single standalone portable `.exe`:

```powershell
pip install -r requirements-dev.txt
python build_executable.py
```
The compiled executable will be placed in the `dist/` directory.

---

## Security & Privacy

* **Offline-First Guarantee**: In Local STT (`faster-whisper`) and Ollama mode, 100% of your audio and text stay on your local machine.
* **Hardware-Bound Credential Storage**: Cloud API keys are securely stored in the Windows Credential Vault via DPAPI encryption (`security_credentials.py`) and masked in the UI.

---

## License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.  
Created by **4bearyy** (2026).


