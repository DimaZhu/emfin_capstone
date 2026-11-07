"""Frozen dynamic research, not an implementation/default policy selection."""
import json
from pathlib import Path


def load():
    path=Path(__file__).parent/'resources/data/science/dynamic-policy-20261107.json'
    return json.loads(path.read_text()) if path.exists() else dict(available=False)
