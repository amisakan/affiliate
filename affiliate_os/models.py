from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

CSV_COLUMNS = [
    "offer_id",
    "asp",
    "genre",
    "offer_name",
    "reward",
    "price",
    "commission_rate",
    "approval_rate",
    "cookie_days",
    "target",
    "problem",
    "benefit",
    "risk_level",
    "brand_fit",
    "lp_url",
    "memo",
    "created_at",
    "updated_at",
]


class Offer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    offer_id: str
    asp: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    offer_name: str = Field(min_length=1)
    reward: Decimal = Field(ge=0)
    price: Decimal | None = None
    commission_rate: str = ""
    approval_rate: str = ""
    cookie_days: int | None = None
    target: str = ""
    problem: str = ""
    benefit: str = ""
    risk_level: str = ""
    brand_fit: str = ""
    lp_url: str = ""
    memo: str = ""
    created_at: datetime
    updated_at: datetime

    @field_validator("reward", "price", mode="before")
    @classmethod
    def parse_decimal(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value).replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError("数値を入力してください") from exc

    @field_validator("cookie_days", mode="before")
    @classmethod
    def parse_cookie_days(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    def to_csv_row(self) -> dict[str, str]:
        return {
            "offer_id": self.offer_id,
            "asp": self.asp,
            "genre": self.genre,
            "offer_name": self.offer_name,
            "reward": format_decimal(self.reward),
            "price": format_decimal(self.price),
            "commission_rate": self.commission_rate,
            "approval_rate": self.approval_rate,
            "cookie_days": "" if self.cookie_days is None else str(self.cookie_days),
            "target": self.target,
            "problem": self.problem,
            "benefit": self.benefit,
            "risk_level": self.risk_level,
            "brand_fit": self.brand_fit,
            "lp_url": self.lp_url,
            "memo": self.memo,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "updated_at": self.updated_at.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> Offer:
        return cls(**row)


class OfferDraft(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asp: str = ""
    genre: str = ""
    offer_name: str = ""
    reward: Decimal | None = None
    price: Decimal | None = None
    commission_rate: str = ""
    approval_rate: str = ""
    cookie_days: int | None = None
    target: str = ""
    problem: str = ""
    benefit: str = ""
    risk_level: str = ""
    brand_fit: str = ""
    lp_url: str = ""
    memo: str = ""

    @field_validator("reward", "price", mode="before")
    @classmethod
    def parse_optional_decimal(cls, value: Any) -> Decimal | None:
        return Offer.parse_decimal(value)

    @field_validator("cookie_days", mode="before")
    @classmethod
    def parse_optional_cookie_days(cls, value: Any) -> int | None:
        return Offer.parse_cookie_days(value)

    def missing_required_fields(self) -> list[str]:
        missing = []
        if not self.asp:
            missing.append("asp")
        if not self.genre:
            missing.append("genre")
        if not self.offer_name:
            missing.append("offer_name")
        if self.reward is None:
            missing.append("reward")
        return missing

    def to_offer(self, offer_id: str, timestamp: datetime) -> Offer:
        return Offer(
            offer_id=offer_id,
            asp=self.asp,
            genre=self.genre,
            offer_name=self.offer_name,
            reward=self.reward,
            price=self.price,
            commission_rate=self.commission_rate,
            approval_rate=self.approval_rate,
            cookie_days=self.cookie_days,
            target=self.target,
            problem=self.problem,
            benefit=self.benefit,
            risk_level=self.risk_level,
            brand_fit=self.brand_fit,
            lp_url=self.lp_url,
            memo=self.memo,
            created_at=timestamp,
            updated_at=timestamp,
        )


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")
