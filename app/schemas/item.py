from pydantic import BaseModel, ConfigDict


class ItemResponse(BaseModel):
    id: int
    name: str
    type: str
    chaos_value: float | None = None
    divine_value: float | None = None
    listing_count: int | None = None
    variant: str | None = None
    snapshot_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GemResponse(BaseModel):
    id: int
    name: str
    type: str
    level: int
    quality: int
    corruption: str | None = None
    chaos_value: float | None = None
    divine_value: float | None = None
    listing_count: int | None = None
    snapshot_at: str | None = None

    model_config = ConfigDict(from_attributes=True)
