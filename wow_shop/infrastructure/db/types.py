from typing import Annotated

from sqlalchemy.orm import mapped_column

int_pk = Annotated[int, mapped_column(primary_key=True)]

str20 = Annotated[str, 20]
str32 = Annotated[str, 32]
str50 = Annotated[str, 50]
str100 = Annotated[str, 100]
str255 = Annotated[str, 255]
str1024 = Annotated[str, 1024]
