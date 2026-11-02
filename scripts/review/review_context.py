"""Locations shared by review checks; write only generated review results."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = REPO/'results/review'
HERE.mkdir(parents=True, exist_ok=True)
