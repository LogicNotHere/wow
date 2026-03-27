from sqlalchemy import MetaData, String
from sqlalchemy.orm import DeclarativeBase

from wow_shop.infrastructure.db.types import (
    str20,
    str32,
    str50,
    str100,
    str255,
    str1024,
)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s__%(column_0_N_name)s",
    "uq": "uq_%(table_name)s__%(column_0_N_name)s",
    "ck": "ck_%(table_name)s__%(constraint_name)s",
    "fk": "fk_%(table_name)s__%(column_0_name)s__%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata
    type_annotation_map = {
        str20: String(20),
        str32: String(32),
        str50: String(50),
        str100: String(100),
        str255: String(255),
        str1024: String(1024),
    }
