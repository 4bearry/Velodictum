# Architectural Decision Records (ADRs)

## Index
* **ADR-001**: Separation of Acoustic STT and Semantic Post-Processing
* **ADR-002**: Transition from Llama 3.2 3B to Qwen 2.5 7B for Local Post-Processing
* **ADR-003**: Pure Semantic Intent Processing vs. Hardcoded Regex Rules
* **ADR-004**: Anti-Answering & Meta-Prompt Protection via Delimited Task Framing
* **ADR-005**: Multi-Engine Intelligence Support (Ollama, OpenRouter, Cloud APIs)
* **ADR-006**: Typographic Neo-Dark Design System & Surface Elevation
* **ADR-007**: Safe Credential & Privacy Handling (.env & Masked UI)
* **ADR-008**: Dynamic Acoustic Prompt-Conditioning for Custom Vocabulary
* **ADR-009**: Pure Synthesized Harmonic Sound Feedback
* **ADR-010**: Hardware-Agnostic Dynamic GPU Detection & Multi-Platform VRAM Telemetry
* **ADR-011**: Conflict-Free Hybrid Transcription Architecture (Local, Grok AI, OpenAI)
* **ADR-012**: Dedicated Custom Preset Cards vs. Standard QPushButton Sub-Layouts
* **ADR-013**: Translucent Surface Blends over Dark Cutout Boxes
* **ADR-014**: In-Place Selection Voice-Editing Engine
* **ADR-015**: Two-Tier Dictation Mode and Style Architecture
* **ADR-016**: Provider-Agnostic Universal API & Modular Formatting Engine
* **ADR-017**: WhisperFlow Scratchpad & Thread-Safe Signal Architecture
* **ADR-018**: Strict Zero-Emoji Design Policy Across Interface and Documentation
* **ADR-019**: Procedural Zero-Latency DSP Synthesis & Audio Theme Modernization
* **ADR-020**: Dynamic Voice Macros & Rigid-Column In-Place List Editors
* **ADR-021**: Release Distribution Privacy Guard & Non-Bundled State Initialization

---

### ADR-001: Separation of Acoustic STT and Semantic Post-Processing
* **Status**: Accepted
* **Context**: Monolithic end-to-end models struggle to balance real-time acoustic phonetics with complex contextual formatting, self-correction resolution, and window awareness.
* **Decision**: Decouple the pipeline into:
  1. **Acoustic Layer**: `faster-whisper` on CUDA FP16 producing high-fidelity raw verbatim transcriptions in `<80 ms`.
  2. **Semantic Flow Layer**: Dedicated LLM (Qwen 2.5 / Gemini) performing zero-shot classification, disfluency removal, and structure formatting.
* **Consequences**: Enables modular upgrades, lower overall latency, and independent customization of speech recognition vs. text style.

---

### ADR-002: Transition to Qwen 2.5 7B on Local GPU
* **Status**: Accepted
* **Context**: `llama3.2:3b` exhibited frequent German grammar errors, hallucinated facts, and struggled to distinguish list directives from list items.
* **Decision**: Standardize local default LLM to **`qwen2.5:7b`** via Ollama on CUDA.
* **Consequences**: Qwen 2.5 7B utilizes ~4.7 GB VRAM, operates at ~350 ms latency, and delivers near-flawless German comprehension, list structuring, and instruction following.

---

### ADR-003: Pure Semantic Intent Processing vs. Hardcoded Regex Rules
* **Status**: Accepted
* **Context**: Hardcoded regex patterns (e.g. `if "ich brauche" in text`) are brittle, fail on natural spoken variations, and cannot resolve mid-speech corrections (*"ach nein, doch kein Brot"*).
* **Decision**: In LLM modes (Ollama, OpenRouter, Gemini), route the raw transcript directly to the LLM with window context. Preserve the regex engine strictly as a zero-dependency 0ms offline fallback for low-power hardware.

---

### ADR-004: Anti-Answering & Meta-Prompt Protection
* **Status**: Accepted
* **Context**: When users dictate questions (*"Wie mache ich X in Antigravity?"*) or coding prompts (*"Schreibe ein Python Skript"*), instruction-tuned LLMs attempt to answer or execute the prompt rather than formatting it.
* **Decision**:
  1. Wrap user audio text in explicit XML tags: `<diktat>\n{text}\n</diktat>\n\nFormatierter Text:`.
  2. Embed strict system prompt instructions and few-shot examples establishing that questions and coding requests must be output verbatim as spoken text.

---

### ADR-005: Multi-Engine Intelligence Support (Ollama & OpenRouter)
* **Status**: Accepted
* **Context**: Users need flexibility between 100% offline privacy (Ollama on GPU) and ultra-fast, universal cloud models (OpenRouter with 100+ models via a single key).
* **Decision**: Build unified multi-engine adapter in `ai_formatter.py` supporting `rules`, `ollama`, `openrouter`, `gemini`, `groq`, and `openai` with zero-restart live switching in the UI.

---

### ADR-006: Typographic Neo-Dark Design System & Surface Elevation
* **Status**: Accepted
* **Context**: Clunky progress bars and nested dark borders made the interface feel cluttered and unrefined.
* **Decision**: Overhaul GUI to a modern, typographic Zinc/Slate aesthetic:
  - Deep slate background (`#0c0c0f`).
  - Subtle elevated surfaces (`#131317`) with ultra-fine edges (`rgba(255,255,255,0.04)`).
  - Clean pill-style segmented tabs and calm status indicators (`● Bereit`).

---

### ADR-007: Safe Credential & Privacy Handling
* **Status**: Accepted
* **Context**: API keys must never leak into chat transcripts, git repos, or logs.
* **Decision**:
  - Automatically load `.env` from project root or `~/.env`.
  - Add `.env` and `*.log` to `.gitignore`.
  - Provide password-masked fields with toggleable visibility in the Dashboard UI.

---

### ADR-008: Dynamic Acoustic Prompt-Conditioning for Custom Vocabulary
* **Status**: Accepted
* **Context**: Technical acronyms (e.g. `CUDA`, `FastAPI`, `PyQt6`) and personal names are often misrecognized phonetically by generic acoustic models.
* **Decision**: Implement `custom_vocabulary.py` with dynamic `vocabulary.json` persistence that injects all active user terms directly into Faster-Whisper's `initial_prompt` before each decoding pass.

---

### ADR-009: Pure Synthesized Harmonic Sound Feedback
* **Status**: Accepted
* **Context**: Standard Windows system beeps (`winsound.Beep`) sound harsh and unpolished.
* **Decision**: Generate studio-grade dual-frequency harmonic sine waves (fundamental + overtone) with smooth cosine attack/decay envelopes (`sound_effects.py`) played non-blockingly via `sounddevice`.

---

### ADR-010: Hardware-Agnostic Dynamic GPU Detection & Multi-Platform VRAM Telemetry
* **Status**: Accepted
* **Context**: Hardcoding GPU models (e.g. `"RTX 4080"`) causes misleading telemetry and crashes on machines with RTX 4060, RTX 3070, AMD Radeon, Intel Arc, or CPU-only systems.
* **Decision**:
  1. Implement hierarchical telemetry query in `gpu_monitor.py`: PyNVML (NVIDIA VRAM & Clock) $\rightarrow$ PyTorch CUDA $\rightarrow$ Windows WMI/DXGI $\rightarrow$ CPU fallback.
  2. Calculate dynamic VRAM safety headroom for Whisper models (`de_max`, `de_fast`, `en_fast`, `lite`) with live Green/Yellow/Red LED indicators.
  3. Eliminate all static GPU strings from backend, UI labels, diagnostics, and documentation.

---

### ADR-011: Conflict-Free Hybrid Transcription Architecture (Local, Grok AI, OpenAI)
* **Status**: Accepted
* **Context**: Laptops and lower-tier GPUs cannot run `large-v3` locally without memory pressure or excessive latency, while users with powerful GPUs demand 100% offline privacy.
* **Decision**:
  1. Build unified `CloudWhisperEngine` in `cloud_stt.py` supporting Grok AI (Groq LPU Whisper-Large-v3, <80ms) and OpenAI Whisper API (`whisper-1`).
  2. Implement mutually exclusive UI visibility: selecting cloud providers automatically hides local model grids and exposes the respective API key input and status banners.

---

### ADR-012: Dedicated Custom Preset Cards vs. Standard QPushButton Sub-Layouts
* **Status**: Accepted
* **Context**: Placing rich child `QLabel`s inside standard `QPushButton` layouts caused severe Qt layout compression, text truncation, and overlapping letter artifacts in model selector tiles.
* **Decision**: Replace `QPushButton` hacks with dedicated `ModelPresetCard(QFrame)` and `ModePresetCard(QFrame)` components utilizing structured `QVBoxLayout`, natural text wrapping, minimum height constraints, and mouse event forwarding.

---

### ADR-013: Translucent Surface Blends over Dark Cutout Boxes
* **Status**: Accepted
* **Context**: Rendering form inputs and dropdowns with solid pitch-black backgrounds created heavy, fragmented "cutout boxes" behind text across settings and dictionary views.
* **Decision**:
  1. Use subtle translucent surface blending (`rgba(255, 255, 255, 0.035)` with soft `1px rgba(255, 255, 255, 0.07)` borders).
  2. Achieve immediate readability through crisp typographic hierarchy: high-contrast white text (`#f1f1f4`), clear secondary labels (`#9d9da8`), and quiet metadata (`#686874`).

---

### ADR-014: In-Place Selection Voice-Editing Engine
* **Status**: Accepted
* **Context**: Users frequently need to rewrite, fix, or transform existing text in desktop apps without manually deleting and retyping.
* **Decision**: Implement `voice_editor.py` with dedicated global hotkey (`ctrl+alt+space` / `ctrl+alt+z`):
  1. Automatically copies highlighted text via Ctrl+C.
  2. Records voice editing instructions (e.g. *"Mach das förmlicher"* or *"Übersetze ins Englische"*).
  3. Applies the transformation via LLM and pastes the replacement directly into the active app.

---

### ADR-015: Two-Tier Dictation Mode and Style Architecture
* **Status**: Accepted
* **Context**: Having overlapping modes like "Business", "Email", "Casual", and "Raw" alongside style profiles caused confusion and redundant UI configurations.
* **Decision**: Collapse the system into a clean 2-tier model:
  1. **Tier 1 (Betriebsmodus)**: `Intelligenter Flow` (KI-Autoflow) vs. `Rohdiktat` (1:1 Whisper-Bypass).
  2. **Tier 2 (Tonalität & Stil)**: 5 distinct profiles (`Standard`, `Formell Sie`, `Locker Du`, `Prägnant & Direkt`, `Akademisch & Gehoben`) active only in Flow mode.

---

### ADR-016: Provider-Agnostic Universal API & Modular Formatting Engine
* **Status**: Accepted
* **Context**: Hardcoding "OpenRouter" in the UI and backend restricted open-source extensibility and created vendor lock-in.
* **Decision**:
  1. Introduce **Universal API** supporting arbitrary OpenAI-compatible base URLs and model IDs (`formatting_providers.py`).
  2. Implement automatic provider detection (`detect_provider`), model catalog categorization (`categorize_models`), and dynamic connection testing (`test_connection`).
  3. Support dedicated provider adapters (`LocalRulesProvider`, `OllamaProvider`, `OpenAIProvider`, `GeminiProvider`, `GroqProvider`).

---

### ADR-017: WhisperFlow Scratchpad & Thread-Safe Signal Architecture
* **Status**: Accepted
* **Context**: Scratchpad note structuring previously froze the UI when executed from worker threads without Qt signal bridges, and the recording indicator reacted to recordings in unrelated windows.
* **Decision**:
  1. Connect Scratchpad structuring via Qt Queued Signals (`structuring_completed`, `structuring_failed`).
  2. Gate recording visual indicators to only turn active when the Scratchpad is in focus or explicitly activated.
  3. Provide a direct 1-click microphone button for hotkey-free dictation directly into notes.

---

### ADR-018: Strict Zero-Emoji Design Policy Across Interface and Documentation
* **Status**: Accepted
* **Context**: Emojis in high-end desktop productivity software look informal and disrupt visual hierarchy.
* **Decision**: Enforce 0 emojis across all UI windows, system tray menus, tables, buttons, logs, code, and documentation in favor of crisp typography and monochrome SVG iconography.

---

### ADR-019: Procedural Zero-Latency DSP Synthesis & Audio Theme Modernization
* **Status**: Accepted
* **Context**: Audio WAV file reads from disk introduce I/O latency, while standard mathematical sine generators sound robotic and harsh.
* **Decision**: Implement `pyfxr` procedural synthesis in `sound_effects.py` with in-memory pre-rendering on module load (`_THEME_BUFFERS` & `_THEME_WAV_BYTES`), delivering 0ms latency with organic tactile acoustics. Eliminate harsh legacy tones (*Windows Studio HD*, *Celestial Glass*, *Zen Bell*).

---

### ADR-020: Dynamic Voice Macros & Rigid-Column In-Place List Editors
* **Status**: Accepted
* **Context**: Static voice triggers could not resolve runtime variables (e.g. today's date, clipboard), and variable trigger text lengths caused visual jumping/displacement of list columns in the GUI.
* **Decision**:
  1. Add dynamic expansion variables (`{clipboard}`, `{date}`, `{time}`, `{weekday}`, etc.) to `smart_snippets.py`.
  2. Enforce rigid width constraints (`setFixedWidth(145)` for triggers, fixed `16px` arrows) and newline indicators (` ↵ `) to ensure all list items maintain an identical vertical baseline.
  3. Implement 1-click **Edit-in-Place** for both Dictionary and Voice Macros.

---

### ADR-021: Release Distribution Privacy Guard & Non-Bundled State Initialization
* **Status**: Accepted
* **Context**: Packing developer configuration files into release builds risks leaking personal names, custom dictionaries, and API credentials to third parties.
* **Decision**: Exclude `settings.json`, `snippets.json`, and `vocabulary.json` from PyInstaller data bundles in `build_executable.py` and `build.bat`. Destination machines automatically generate clean, neutral factory defaults on initial boot.
