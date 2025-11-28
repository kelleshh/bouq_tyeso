from __future__ import annotations
from typing import Any, List, Literal
from pydantic import BaseModel, Field, field_validator


class AlertModel(BaseModel):
    shop: Literal["Tyeso", "Bouq"]
    marketplace: Literal["WB", "Ozon", "Ozon (Кластеры)"]
    location: str
    article: str
    days: int = Field(..., description="Days until depletion", ge=0)


class AlertsPayload(BaseModel):
    """
    Root-модель: __root__ - список AlertModel.
    На вход ждём массив массивов, типа:
    [
      ["Tyeso","WB","СКЛАД_1","ART123",3],
      ...
    ]
    """

    __root__: List[AlertModel]

    @field_validator("__root__", mode="before")
    @classmethod
    def from_nested_list(cls, value: Any):
        if value == []:
            return []

        if not isinstance(value, list):
            raise TypeError("Payload must be a JSON array")

        converted: List[dict] = []

        for idx, item in enumerate(value):
            if not isinstance(item, list):
                raise TypeError(f"Item at index {idx} must be a list")
            if len(item) != 5:
                raise TypeError(
                    f"Item at index {idx} must have exactly 5 elements "
                    f"[shop, marketplace, location, article, days]"
                )

            shop, marketplace, location, article, days = item
            converted.append(
                {
                    "shop": shop,
                    "marketplace": marketplace,
                    "location": location,
                    "article": article,
                    "days": days,
                }
            )

        return converted
