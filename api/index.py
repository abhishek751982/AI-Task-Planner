import sys
from pathlib import Path

# Vercel: src layout is not on PYTHONPATH by default
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from guide_todoo.api import app  # noqa: E402
