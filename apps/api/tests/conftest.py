import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AI_MODE", "mock")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
