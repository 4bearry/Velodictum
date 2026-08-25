import numpy as np
import time
from config import config
from main import VelodictumCoreApp

config.load()
app = VelodictumCoreApp()

# Create dummy 1.0s audio tone at 16kHz
sample_rate = config.audio.sample_rate
t = np.linspace(0, 1.0, sample_rate, endpoint=False, dtype=np.float32)
audio = 0.1 * np.sin(2 * np.pi * 440 * t)

print("[CoreApp Test] Active Engine:", app.formatter.engine)
print("[CoreApp Test] Active OpenRouter Model:", app.formatter.openrouter_model)
print("[CoreApp Test] STT Model:", app.stt.model_size)

# Verify formatter sync
app.config.formatting.openrouter_model = "qwen/qwen-2.5-72b-instruct"
app.formatter.openrouter_model = app.config.formatting.openrouter_model

res = app.formatter.format_text("Das ist ein interner Durchlauftest.", language="de")
print("[CoreApp Test] Formatter result:", res)
assert res["engine"] in ("openrouter", "universal", "groq", "openai", "gemini", "rules", "ollama")
print("[CoreApp Test] SUCCESSFUL!")
