from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Action = Literal["BUY", "SELL", "HOLD"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssetTechnicalView(StrictSchema):
    asset: Literal["BTC/USDT", "ETH/USDT"]
    trend: Literal["BULLISH", "BEARISH", "NEUTRAL", "INSUFFICIENT_DATA"]
    indicators: dict
    favorable_arguments: list[str]
    contrary_arguments: list[str]
    action: Action
    justification: str
    invalidation_conditions: list[str]


class AlexOutput(StrictSchema):
    assessments: list[AssetTechnicalView]
    selected_asset: Literal["BTC/USDT", "ETH/USDT"] | None
    action: Action
    summary: str

    @model_validator(mode="after")
    def hold_has_no_asset(self):
        if self.action == "HOLD" and self.selected_asset is not None:
            raise ValueError("HOLD não pode selecionar ativo.")
        if self.action != "HOLD" and self.selected_asset is None:
            raise ValueError("BUY/SELL exige ativo.")
        return self


class MayaOutput(StrictSchema):
    action: Action
    asset: Literal["BTC/USDT", "ETH/USDT"] | None
    allocation_percent: Decimal = Field(ge=0, le=5)
    favorable_arguments: list[str]
    hold_arguments: list[str]
    disagreements: list[str]
    reasoning: str

    @field_validator("allocation_percent")
    @classmethod
    def finite_allocation(cls, value):
        if not value.is_finite():
            raise ValueError("Alocação precisa ser finita.")
        return value

    @model_validator(mode="after")
    def coherent_action(self):
        if self.action == "HOLD" and (self.asset is not None or self.allocation_percent != 0):
            raise ValueError("HOLD não pode alocar capital.")
        if self.action != "HOLD" and (self.asset is None or self.allocation_percent <= 0):
            raise ValueError("Operação exige ativo e alocação positiva.")
        return self


class VictorOutput(StrictSchema):
    action: Action
    risk_allowed: bool
    risk_codes: list[str]
    approved_checks: list[str]
    failed_checks: list[str]
    fragile_hypotheses: list[str]
    reasoning: str
    suggested_adjustment: str | None

    @model_validator(mode="after")
    def deterministic_risk_wins(self):
        if not self.risk_allowed and self.action != "HOLD":
            raise ValueError("Risco reprovado exige HOLD.")
        return self
