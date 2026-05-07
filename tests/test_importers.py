from datetime import datetime
from decimal import Decimal

from affiliate_os.importers.reviewer import build_offer_from_draft
from affiliate_os.importers.vision_importer import image_to_data_url
from affiliate_os.models import OfferDraft


def test_image_to_data_url_encodes_local_image(tmp_path):
    image_path = tmp_path / "screenshot.png"
    image_path.write_bytes(b"fake image bytes")

    data_url = image_to_data_url(image_path)

    assert data_url.startswith("data:image/png;base64,")
    assert data_url.endswith("ZmFrZSBpbWFnZSBieXRlcw==")


def test_offer_draft_reports_missing_required_fields():
    draft = OfferDraft(asp="A8", genre="習い事")

    assert draft.missing_required_fields() == ["offer_name", "reward"]


def test_build_offer_from_draft_assigns_next_id(tmp_path):
    data_path = tmp_path / "offers.csv"
    draft = OfferDraft(
        asp="A8",
        genre="習い事",
        offer_name="AIスクール",
        reward=Decimal("30000"),
        cookie_days=90,
        risk_level="中",
        brand_fit="要確認",
    )

    offer = build_offer_from_draft(draft, data_path, timestamp=datetime(2026, 5, 7, 23, 45, 11))

    assert offer.offer_id == "OFF-0001"
    assert offer.reward == Decimal("30000")
    assert offer.cookie_days == 90
    assert offer.created_at.isoformat(timespec="seconds") == "2026-05-07T23:45:11"
