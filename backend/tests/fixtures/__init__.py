import json
import pathlib

FIXTURES = pathlib.Path(__file__).parent


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
