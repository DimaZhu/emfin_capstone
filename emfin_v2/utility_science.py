"""Frozen research snapshot, never recomputed or sold as current edited inputs."""
import json
from pathlib import Path


def load():
    path=Path(__file__).parent/'resources'/'data'/'science'/'utility-comparison-20261107.json'
    return json.loads(path.read_text()) if path.exists() else dict(available=False)
