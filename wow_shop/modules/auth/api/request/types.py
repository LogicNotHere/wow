from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

from wow_shop.modules.auth.constants import (
    NON_EMPTY_MIN_LENGTH,
    PASSWORD_MIN_LENGTH,
)

NonEmptyStrippedStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=NON_EMPTY_MIN_LENGTH,
    ),
]
NonEmptyStr = Annotated[
    str,
    StringConstraints(min_length=NON_EMPTY_MIN_LENGTH),
]
PasswordStr = Annotated[
    str,
    StringConstraints(min_length=PASSWORD_MIN_LENGTH),
]
