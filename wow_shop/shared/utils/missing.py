from __future__ import annotations

from enum import Enum
from typing import Final, Literal


class MissingType(Enum):
    """Represents a request field that was not provided."""

    MISSING = "__missing__"

    def __bool__(self) -> Literal[False]:
        return False


Missing: Final = MissingType.MISSING
