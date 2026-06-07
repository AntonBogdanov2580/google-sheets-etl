"""Pytest configuration — adds project root to sys.path."""
import sys
from pathlib import Path

# Ensure the project root is on the Python path so `etl` package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
