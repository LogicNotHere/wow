from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, create_model

from wow_shop.shared.utils.missing import Missing, MissingType


def _get_partial_base_model(model_cls: type[BaseModel]) -> type[BaseModel]:
    """Pick a lightweight base without inheriting source data fields."""

    for base_cls in model_cls.__mro__[1:]:
        if not issubclass(base_cls, BaseModel):
            continue
        base_fields = getattr(base_cls, "model_fields", {})
        if not base_fields:
            return base_cls
    return BaseModel


def build_partial_model(
    model_cls: type[BaseModel],
    *,
    name: str | None = None,
    exclude_fields: set[str] | None = None,
) -> type[BaseModel]:
    """Build PATCH-style model where absent fields are represented by Missing."""

    excluded = exclude_fields or set()
    field_definitions: dict[str, Any] = {}

    for field_name, field_info in model_cls.model_fields.items():
        if field_name in excluded:
            continue

        field_data = field_info.asdict()
        annotation = field_data["annotation"] | None | MissingType
        metadata = list(field_data["metadata"])
        attributes = dict(field_data["attributes"])
        attributes.pop("default", None)
        attributes.pop("default_factory", None)

        annotated_type = Annotated.__class_getitem__(
            (annotation, *metadata, Field(**attributes))
        )
        field_definitions[field_name] = (annotated_type, Missing)

    partial_model_name = name or f"Partial{model_cls.__name__}"
    return create_model(
        partial_model_name,
        __base__=_get_partial_base_model(model_cls),
        __module__=model_cls.__module__,
        **field_definitions,
    )


class PartialModel:
    """
    Class decorator for PATCH request models.

    Usage:
        @PartialModel()
        class PatchRequest(CommonRequest):
            extra_patch_only_field: str | None = None
    """

    def __init__(
        self,
        *,
        exclude_fields: set[str] | None = None,
    ) -> None:
        self._exclude_fields = set(exclude_fields or set())

    def __call__(self, model_cls: type[BaseModel]) -> type[BaseModel]:
        class_exclude = getattr(model_cls, "__partial_exclude_fields__", set())
        exclude_fields = self._exclude_fields | set(class_exclude)
        return build_partial_model(
            model_cls,
            name=model_cls.__name__,
            exclude_fields=exclude_fields,
        )
