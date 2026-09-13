"""
Creator data provider abstraction.

The rest of the app talks to creators only through `CreatorProvider`.
Today `MockCreatorProvider` reads a local JSON file of fictional demo
creators. Swapping in a real creator-discovery API later means writing a
new class with the same `list_creators()` / `get_creator(id)` interface
and pointing `get_provider()` at it -- no other code needs to change.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

DATA_FILE = Path(__file__).parent / "creators.json"


class CreatorProvider(ABC):
    @abstractmethod
    def list_creators(self) -> list[dict]:
        """Return all available creator records."""

    @abstractmethod
    def get_creator(self, creator_id: str) -> Optional[dict]:
        """Return a single creator record by id, or None if not found."""


class MockCreatorProvider(CreatorProvider):
    """Demo/simulated creator dataset for the OUTTHERE hackathon MVP.

    All creators returned by this provider are fictional and clearly
    labeled as demo data -- see the `_note` field in creators.json.
    """

    def __init__(self, data_file: Path = DATA_FILE):
        self._data_file = data_file
        self._creators: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self._creators = payload.get("creators", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self._creators = []

    def list_creators(self) -> list[dict]:
        return list(self._creators)

    def get_creator(self, creator_id: str) -> Optional[dict]:
        for creator in self._creators:
            if creator["id"] == creator_id:
                return creator
        return None


_provider: Optional[CreatorProvider] = None


def get_provider() -> CreatorProvider:
    """Return the active creator data provider (singleton).

    Hackathon MVP always uses the mock provider. A future real API
    integration can be swapped in here behind an env flag, e.g.:

        if os.getenv("CREATOR_API_MODE") == "live":
            return LiveCreatorProvider()
    """
    global _provider
    if _provider is None:
        _provider = MockCreatorProvider()
    return _provider
