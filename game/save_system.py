from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SAVE_VERSION = 1
SAVE_FILE = Path(__file__).resolve().parent.parent / "savegame.json"


def save_exists() -> bool:
    """ 
    check if a save file exists by verifying if the game's save file exists in the 
    expected location. It returns True if the save file is found, indicating that there is
    a saved game available, and False if the save file does not exist, indicating that 
    there is no saved game to load.
    """
    return SAVE_FILE.exists()


def load_save_data() -> dict[str, Any] | None:
    if not SAVE_FILE.exists():
        return None

    with SAVE_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if data.get("version") != SAVE_VERSION:
        raise ValueError("Unsupported save version.")

    return data


def write_save_data(data: dict[str, Any]) -> None:
    payload = {"version": SAVE_VERSION, **data}
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SAVE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
