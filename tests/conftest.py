import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(PROJECT_ROOT, "core")

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(1, PROJECT_ROOT)


