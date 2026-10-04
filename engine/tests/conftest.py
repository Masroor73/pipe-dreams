"""Make engine/pipe_dreams_engine importable when pytest is run from the repo or engine/."""

from pathlib import Path
import sys

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))
