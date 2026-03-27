from typing import Annotated

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column

game_fk = Annotated[int, mapped_column(ForeignKey("catalog_games.id"))]
category_fk = Annotated[
    int, mapped_column(ForeignKey("catalog_service_categories.id"))
]
category_parent_fk = Annotated[
    int, mapped_column(ForeignKey("catalog_service_categories.id"))
]
lot_fk = Annotated[int, mapped_column(ForeignKey("catalog_service_lots.id"))]
page_fk = Annotated[int, mapped_column(ForeignKey("catalog_service_pages.id"))]
