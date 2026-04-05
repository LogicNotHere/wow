from __future__ import annotations

from typing import Annotated

from annotated_types import Gt

IntId = Annotated[int, Gt(0)]
