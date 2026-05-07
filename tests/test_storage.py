from datetime import datetime
from decimal import Decimal

from affiliate_os.models import CSV_COLUMNS, Offer
from affiliate_os.storage import (
    append_offer,
    ensure_offers_csv,
    filter_offers,
    load_offers,
    next_offer_id,
)


def make_offer(
    offer_id: str, asp: str = "A8", genre: str = "医療者AI", reward: str = "30000"
) -> Offer:
    now = datetime(2026, 5, 7, 10, 30)
    return Offer(
        offer_id=offer_id,
        asp=asp,
        genre=genre,
        offer_name=f"Offer {offer_id}",
        reward=reward,
        created_at=now,
        updated_at=now,
    )


def test_ensure_offers_csv_creates_header(tmp_path):
    path = tmp_path / "data" / "offers.csv"

    ensure_offers_csv(path)

    assert path.exists()
    assert path.read_text(encoding="utf-8").strip() == ",".join(CSV_COLUMNS)


def test_append_load_and_next_offer_id(tmp_path):
    path = tmp_path / "offers.csv"
    append_offer(make_offer("OFF-0001"), path)
    append_offer(make_offer("OFF-0002", asp="もしも", reward="45000"), path)

    offers = load_offers(path)

    assert len(offers) == 2
    assert offers[1].asp == "もしも"
    assert offers[1].reward == Decimal("45000")
    assert next_offer_id(path) == "OFF-0003"


def test_filter_offers_by_genre_asp_and_min_reward():
    offers = [
        make_offer("OFF-0001", asp="A8", genre="医療者AI", reward="30000"),
        make_offer("OFF-0002", asp="A8", genre="転職", reward="20000"),
        make_offer("OFF-0003", asp="もしも", genre="医療者AI", reward="50000"),
    ]

    filtered = filter_offers(offers, genre="医療者AI", asp="もしも", min_reward=Decimal("40000"))

    assert [offer.offer_id for offer in filtered] == ["OFF-0003"]
