# Velodictum - Roadmap & TODO

## Status Legend
* [x] **Completed & Verified**
* [/] **In Progress**
* [ ] **Planned / Future Roadmap**

---

## Phase 1: Core Acoustic Engine & CUDA Pipeline
- [x] **CUDA Accelerated Whisper STT**: `faster-whisper` integration with CTranslate2 and FP16 compute.
- [x] **Anti-Hallucination Pipeline**: Silero VAD, repetition penalties, clean vocabulary initial prompts.
- [x] **Win32 Smart Injector**: Virtual keystroke emulation (`keybd_event` Ctrl+V) with background clipboard backup and restore.
- [x] **Reentrant Thread Safety**: Model switching and audio processing protected by `threading.RLock()` to prevent deadlocks.
- [x] **Quality Profiles**: Intuitive 4-tier profile selector (`large-v3-turbo`, `medium`, `distil-large-v3`, `small`).

---

## Phase 2: Multi-Engine Intelligence & The Flow Layer
- [x] **Local GPU Power (Offline)**: Ollama integration default to `qwen2.5:7b` (100% offline, ~350ms).
- [x] **OpenRouter Universal API Adapter**: Single API key support for 100+ models (`qwen/qwen-2.5-72b-instruct`, `google/gemini-2.5-flash`, `meta-llama/llama-3.3-70b-instruct`, `deepseek/deepseek-chat`, `anthropic/claude-3.5-haiku`).
- [x] **Direct Cloud Engine Adapters**: Google Gemini 2.0 Flash, Groq LPU, OpenAI GPT-4o-mini.
- [x] **Anti-Answering & Meta-Prompt Protection**: Tagged XML task delimiter framing (`<diktat>...</diktat>`) preventing LLMs from answering dictated questions or executing coding prompts.
- [x] **Live Self-Correction & List Formatting**: Natural speech removal (*"ich brauche A, ach nein, kein A sondern B"*) and automated Markdown bullet point structuring.
- [x] **Spoken Formatting Directives**: Native support for spoken layout commands (*"neue Zeile"*, *"Absatz"*, *"Doppelpunkt"*, *"in Anführungszeichen"*).
- [x] **Safe Credential Management**: Hardware-bound Windows Credential Vault (`security_credentials.py`) for enterprise-grade secret storage with password-masked input fields.

---

## Phase 3: Hardware Agnostic Engine & Hybrid STT Architecture
- [x] **Dynamic GPU & Hardware Detection**: Multi-tier detection in `gpu_monitor.py` (PyNVML -> PyTorch CUDA -> WMI/DXGI -> CPU fallback) removing all hardcoded GPU model strings.
- [x] **VRAM-Aware Model Compatibility Matrix**: Live Green/Yellow/Red indicators showing whether `Large-v3-Turbo`, `Medium`, `Distil-Large-v3`, or `Small` fits the active GPU.
- [x] **Universal STT API & Custom Endpoints**:
  - Unified `CloudWhisperEngine` (`cloud_stt.py`) supporting **Universal API** (OpenRouter `openai/whisper-large-v3`, Self-Hosted `whisper.cpp`, `faster-whisper-server`, LocalAI, vLLM), **Grok AI** (Groq LPU Whisper-Large-v3, <80ms) and **OpenAI** (`whisper-1`).
  - Frei konfigurierbare Endpunkt-URLs, Modell-IDs und automatische Key-Auflösung aus dem Formatierungs-Key.
- [x] **Mutually Exclusive UI Visibility**: Dynamisches Ein- und Ausblenden der Provider-spezifischen Eingabefelder und Cloud-Banner im Tab *Spracherkennung*.
- [x] **Whisper Model Storage & Downloader Manager**: Dedizierte Unterordnerverwaltung mit freier Pfadauswahl und Speicherplatzanalyse.

---

## Phase 4: Pro Desktop UI/UX & Design System
- [x] **Liquid Glass Design System (Windows 11 Acrylic)**: Minimalistische, transluzente Obsidian-Ästhetik (`#0c0c0f` Basis, `#131317` Elevations, Specular Light Edges, Zero harsh borders).
- [x] **Mental-Model 7-Karten-Architektur**: Komplette Neuordnung der Einstellungsseite nach dem Nutzer-Mentalmodell inklusive Live-Suchfilter und visueller Abhängigkeitssteuerung.
- [x] **Dedicated Unclipped Preset Cards**: Eigene `ModelPresetCard`, `ModePresetCard`, `TonePresetCard` und harmonisierte `ModelPriorityCard` Widgets zur Beseitigung von Layout-Clipping.
- [x] **Farbharmonisierung der Modellauswahl**: Schnelligkeit, Ausgewogen und Beste Qualität nutzen das einheitliche Liquid Glass Studio-Design (`#172033` mit dezentem 1px Neon-Cyan-Rand).
- [x] **Clipping-freies Resizen & Minimum Window Size**: Dashboard Minimum Size auf 880x640 gesetzt mit vollständigem ScrollArea-Schutz auf allen Tabs.
- [x] **Live 36-Bar Audio Spectrum Meter**: Echtzeit-Visualisierung während der Aufnahme bei 60 FPS.
- [x] **Multi-Key Hotkey Recorder & Modes**: Globaler Listener für Push-to-Talk und Toggle-Modus mit modalem Capture-Dialog.
- [x] **Harmonic Studio Audio Chimes**: Synthese-Klangthemen (*Velodictum Silk*, *Velodictum Taptic Glass*).

---

## Phase 5: Deep Context & Voice Editing
- [x] **In-Place Voice Transform (`Ctrl+Alt+Space`)**: Text selection grabber und sprachgesteuerter Textumwandler.
- [x] **Atomic Undo (`Ctrl+Alt+Z`)**: Keystroke-Historienpuffer und sofortige Rücknahme der letzten Injektion.
- [x] **Floating Mini-HUD / Pill Widget**: Always-on-top Pill mit Feder-Physik, konfigurierbarer Positionierung, Transparenz und Caret-Tracking.
- [x] **Single-Instance Win32 Mutex**: Systemweiter Mutex zur Vermeidung doppelter Instanzen.
- [x] **System Tray & Autostart**: Windows Registry Autostart-Manager, `--minimized` Startflag und Tray-Icon.
- [x] **Deep UI Automation Caret Inspection**: Analyse des umgebenden Texts für nahtlose Satzfortführungen und Leerzeichen-Logik.
- [x] **Personal Style & Tone Adaptation**: Tonalitätsprofile (Formell Sie, Locker Du, Prägnant, Akademisch).
- [x] **Robust Batch Execution**: Windows `build.bat` und `build_executable.py` für Distribution und Virtual-Env-Prüfung.

---

## Phase 6: Power-User Automation & Audio-Hardware
- [x] **Auto-Ducking**: Automatische Lautstärke-Absenkung von Hintergrund-Audio (Musik, YouTube, Games) während des Diktats mit Schieberegler (10% - 50%).
- [x] **Audio-Device Hot-Plug & HUD-Benachrichtigung**:
  - Erkennung von ausgesteckten/eingesteckten Mikrofonen auch bei "System-Standard".
  - Nahtloser Fallback auf aktives Audio-Gerät mit Benachrichtigung im Floating HUD.
- [x] **Vorverstärkungs-Schieberegler & Live-Kalibrierungs-Assistent**:
  - Stufenlose Vorverstärkung (50% bis 300% / -6 dB bis +9.5 dB) mit Anti-Clipping Soft Limiter.
  - Live-Pegel-Assistent mit 3 farbigen Zonen und separatem Mikrofontest-Modus (`[Mikrofontest starten]`).
- [x] **Drei-Wege-Diktat-Abbruch**:
  - Sofortabbruch per `Escape`-Taste während der Aufnahme (0ms Latenz).
  - Rechtsklick auf das Floating HUD.
  - Gesprochener isolierter Abbruchbefehl ("Abbrechen", "Verwerfen").
- [x] **Intelligentes Wörterbuch & Live In-Field Korrekturerkennung**:
  - Erkennung von manuell im Textfeld korrigierten Eigennamen (z. B. "Powert" zu "Pawbert").
  - Interaktiver Bestätigungs-Prompt im Floating HUD mit 1-Klick-Übernahme.
  - Window- & Control-Pinning zur Vermeidung von Fehlalarmen.
- [x] **"Send It" / Voice Command Actions**:
  - Automatisches Entfernen von Trigger-Phrasen (*"und abschicken"*, *"send it"*) mit automatischem `Enter`-Tastendruck.
- [x] **Spoken Markdown Syntax Engine**:
  - Echtzeit-Umwandlung von Sprachbefehlen in sauberes Markdown (*"Überschrift 1/2/3"*, *"Fett"*, *"Checkbox"* etc.).

---

## Phase 7: Context Intelligence & Multi-Language Precision
- [x] **Automatisches Workspace-Seeding**:
  - Automatische Erkennung von VS Code Projektordnern, Dateinamen und Git-Branches zur dynamischen Whisper-Konditionierung.
- [x] **Halluzinations-Squelcher & Wörterbuch-Auto-Vorschlag**:
  - Filter für Standard-Whisper-Stille-Halluzinationen und automatische Erkennung von Fachbegriffen.
- [x] **Intelligentes Code-Switching (Denglisch / Dual-Language)**:
  - Nahtlose Verarbeitung gemischter deutsch-englischer Fachbegriffe ohne Lautschrift-Verzerrung.

---

## Phase 8: Audio-Dateien & Diktierbuch-Scratchpad
- [x] **Auto-Transkriptionen (Audio-Dateien & Voice Memos)**:
  - Batch-Verarbeitung von `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` mit Markdown-Export.
- [x] **Diktierbuch / Floating Scratchpad (`Ctrl+Shift+D`)**:
  - Minimalistisches Memofenster für Notizen mit 1-Klick-Strukturierung.

---

## Phase 9: Standalone & Mobile Releases
- [x] **Standalone Portable Windows Executable (`Velodictum.exe`)**:
  - PyInstaller Build-Pipeline mit allen Hidden-Imports, CTranslate2 DLLs, PyQt6 und Konfigurationen.
- [x] **Mobile Companion & LAN Bridge (`mobile_bridge_server.py`)**:
---

## Phase 10: High-End DSP Audio, Privacy Sanitization & Desktop UX
- [x] **Procedural DSP Sound Synthesis (`pyfxr`)**:
  - Pre-rendered zero-latency in-memory buffers (NumPy float32 & WAV bytes) with 0ms per-click CPU overhead.
  - High-fidelity acoustic themes: *Velodictum Silk Droplet*, *Velodictum Taptic Glass*, *Haptic Pop*, *Studio Tactile Thock*, *Velvet Acoustic*, *Opal Resonance*, *Quantum Precision*, *Cyber Neural*.
  - Elimination of harsh/unnatural legacy sounds (*Windows Studio HD*, *Celestial Glass*, *Zen Bell*).
- [x] **Smart Snippets & Dynamic Voice Macros**:
  - Macro expansion with dynamic placeholder variables: `{clipboard}`, `{date}`, `{time}`, `{weekday}`, `{iso_date}`, `{year}`, `{month}`, `{day}`.
  - Stable column layout with fixed trigger metrics and compact single-line visualization of multiline snippets (` ↵ `).
  - Full **Edit-in-Place** support: 1-click loading of existing macros and vocabulary entries into top inputs with live save/cancel buttons.
- [x] **CPU First-Run Auto-Detection & Laptop Assistance**:
  - Automatic detection of missing CUDA hardware on first boot via `GPUMonitor.is_cuda_available()`.
  - Automatic configuration of the lightweight `low_vram` profile (`small` model, CPU, int8) preventing heavy 1.5 GB downloads on office machines.
- [x] **Universal API Default Enforcement**:
  - Factory default configuration set to Universal API (`config.formatting.engine = "universal"`) with persistent OpenRouter model routing.
- [x] **Release Distribution Privacy Guard**:
  - Build script (`build_executable.py` & `build.bat`) sanitized to prevent bundling private developer configuration files (`settings.json`, `snippets.json`, `vocabulary.json`).
  - First launch on destination PC generates clean, neutral factory defaults.

---

## Phase 11: 3-Tier Model Intelligence & Zero-Pollution Clipboard Architecture
- [x] **Curated 3-Tier Model Hierarchy**:
  - 10 live-benchmarked LLMs categorized into **Speed Priority** (< 250ms), **Balanced** (300–500ms), and **Highest Quality** (1–2s).
  - Accurate token pricing metadata, context limits, and latency targets integrated into `formatting_providers.py`.
- [x] **Interactive Sub-Model Quick-Chips Bar (`SubModelChip`)**:
  - Visible 1-click model pill chips rendered directly below the 3 priority cards in the Formatting tab.
  - Live price badges, instant config persistence, and real-time synchronization with the model catalog dropdown.
  - Strict Zero-Emoji typography compliance across all chip titles and headers.
- [x] **Exact-First Slug Resolution & Prefix Collision Fix**:
  - Refactored model matching in `formatting_providers.py` and `ai_formatter.py` to prevent greedy substring captures (e.g. `gemini-2.5-flash` hijacking `gemini-2.5-flash-lite`).
- [x] **Native Win32 Clipboard Sequence Tracking**:
  - Replaced temporary sentinel strings (`__VELODICTUM_GRAB_...`) with native `user32.GetClipboardSequenceNumber()` in `grab_selected_text_win32()`.
  - 100% elimination of leaked test strings or clipboard corruption in Windows Clipboard History (`Win+V`).
- [x] **Immediate Dictation Clipboard Retention**:
  - Default `restore_clipboard` set to `False` in `InjectionConfig`, keeping freshly dictated text ready on the clipboard.
  - Users who accidentally click away from text input fields during dictation can immediately press `Ctrl+V` in their target window without opening the app.
- [x] **Hardened History & Studio Copy Actions**:
  - Integrated `safe_clipboard_copy()` across Studio and History cards with retry against OS clipboard locks and visual *"Kopiert!"* status feedback.

---

## Future Roadmap & Mobile
- [ ] **Native Android App**:
  - Standalone Android Client with Floating Overlay companion for desktop bridge.
