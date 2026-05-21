from pydantic import BaseModel, ConfigDict


class CurrencyResponse(BaseModel):
    id: int
    name: str
    type: str
    chaos_value: float
    low_confidence: bool
    snapshot_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PriceHistoryPoint(BaseModel):
    price_chaos: float | None = None
    price_divine: float | None = None
    recorded_at: str | None = None
