from datetime import datetime

from affiliate_os.content import (
    MAX_X_POST_LENGTH,
    filter_offers_by_id,
    format_x_posts_markdown,
    generate_x_post_for_offer,
    generate_x_posts_for_offers,
    write_x_posts_markdown,
)
from affiliate_os.models import Offer


def make_offer(
    offer_id: str = "OFF-0001",
    offer_name: str = "AI講座",
    target: str = "AIを学びたい社会人",
    problem: str = "学習内容や費用を比較したい",
    benefit: str = "講座内容とサポートを比較できます",
    memo: str = "否認条件を確認してください",
) -> Offer:
    now = datetime(2026, 5, 8, 13, 0)
    return Offer(
        offer_id=offer_id,
        asp="A8",
        genre="習い事",
        offer_name=offer_name,
        reward="30000",
        target=target,
        problem=problem,
        benefit=benefit,
        risk_level="中",
        brand_fit="要確認",
        memo=memo,
        created_at=now,
        updated_at=now,
    )


def test_generate_x_post_for_offer_creates_compliant_decision_support_text():
    draft = generate_x_post_for_offer(make_offer())

    assert draft.offer_id == "OFF-0001"
    assert len(draft.text) <= MAX_X_POST_LENGTH
    assert draft.passed_compliance
    assert "比較" in draft.text
    assert "誰でも簡単" not in draft.text
    assert "必ず稼げる" not in draft.text


def test_generate_x_post_truncates_long_text():
    offer = make_offer(
        offer_name="とても長い名前のAI講座" * 20,
        target="AIとWebマーケティングを学びたい社会人" * 10,
        problem="学習内容、費用、サポート、受講期間を比較したい" * 10,
        benefit="講座内容、サポート体制、費用、受講条件を確認できます" * 10,
    )

    draft = generate_x_post_for_offer(offer)

    assert len(draft.text) <= MAX_X_POST_LENGTH
    assert draft.text.endswith("詳細条件は公式情報で確認してください。")


def test_generate_x_posts_for_offers_keeps_order():
    offers = [make_offer("OFF-0001"), make_offer("OFF-0002")]

    drafts = generate_x_posts_for_offers(offers)

    assert [draft.offer_id for draft in drafts] == ["OFF-0001", "OFF-0002"]


def test_filter_offers_by_id():
    offers = [make_offer("OFF-0001"), make_offer("OFF-0002")]

    assert filter_offers_by_id(offers, None) == offers
    assert [offer.offer_id for offer in filter_offers_by_id(offers, "OFF-0002")] == [
        "OFF-0002"
    ]
    assert filter_offers_by_id(offers, "OFF-9999") == []


def test_format_and_write_x_posts_markdown(tmp_path):
    draft = generate_x_post_for_offer(make_offer())
    output_path = tmp_path / "x_posts.md"

    saved_path = write_x_posts_markdown([draft], output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_x_posts_markdown([draft]) == text
    assert "# X Post Drafts" in text
    assert "OFF-0001" in text
