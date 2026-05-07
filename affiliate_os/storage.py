from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from affiliate_os.models import CSV_COLUMNS, Offer

DEFAULT_DATA_PATH = Path("data") / "offers.csv"


def ensure_offers_csv(path: Path = DEFAULT_DATA_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
    return path


def load_offers(path: Path = DEFAULT_DATA_PATH) -> list[Offer]:
    ensure_offers_csv(path)
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [Offer.from_csv_row(row) for row in reader]


def append_offer(offer: Offer, path: Path = DEFAULT_DATA_PATH) -> None:
    ensure_offers_csv(path)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writerow(offer.to_csv_row())


def next_offer_id(path: Path = DEFAULT_DATA_PATH) -> str:
    offers = load_offers(path)
    if not offers:
        return "OFF-0001"

    max_number = 0
    for offer in offers:
        try:
            number = int(offer.offer_id.split("-")[-1])
        except ValueError:
            continue
        max_number = max(max_number, number)
    return f"OFF-{max_number + 1:04d}"


def filter_offers(
    offers: list[Offer],
    genre: str | None = None,
    asp: str | None = None,
    min_reward: Decimal | None = None,
) -> list[Offer]:
    filtered = offers
    if genre:
        filtered = [offer for offer in filtered if offer.genre == genre]
    if asp:
        filtered = [offer for offer in filtered if offer.asp == asp]
    if min_reward is not None:
        filtered = [offer for offer in filtered if offer.reward >= min_reward]
    return filtered
