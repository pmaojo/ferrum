import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
AI_DIR = os.path.join(ROOT, "ai")
if AI_DIR not in sys.path:
    sys.path.insert(0, AI_DIR)
os.environ["PYTHONPATH"] = os.pathsep.join([ROOT, AI_DIR, os.environ.get("PYTHONPATH", "")])
