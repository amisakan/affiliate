from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from affiliate_os.models import Offer, format_decimal


def test_offer_accepts_required_fields_and_formats_csv_row():
    now = datetime(2026, 5, 7, 10, 30)
    offer = Offer(
        offer_id="OFF-0001",
        asp="A8",
        genre="医療者AI",
        offer_name="AI講座",
        reward="30,000",
        created_at=now,
        updated_at=now,
    )

    row = offer.to_csv_row()

    assert offer.reward == Decimal("30000")
    assert row["reward"] == "30000"
    assert row["created_at"] == "2026-05-07T10:30:00"


def test_offer_requires_core_fields():
    with pytest.raises(ValidationError):
        Offer(
            offer_id="OFF-0001",
            asp="",
            genre="医療者AI",
            offer_name="AI講座",
            reward="30000",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


def test_format_decimal_handles_empty_and_fractional_values():
    assert format_decimal(None) == ""
    assert format_decimal(Decimal("30000.00")) == "30000"
    assert format_decimal(Decimal("12.50")) == "12.5"
