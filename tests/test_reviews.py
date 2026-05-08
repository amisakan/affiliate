from datetime import datetime

import pytest

from affiliate_os.content import generate_note_article_for_offer, generate_x_post_for_offer
from affiliate_os.models import Offer
from affiliate_os.reviews import (
    build_content_reviews,
    content_preview,
    format_content_reviews_markdown,
    normalize_review_status,
    write_content_reviews_csv,
    write_content_reviews_markdown,
)
from affiliate_os.scoring import explain_score


def make_offer() -> Offer:
    now = datetime(2026, 5, 8, 13, 0)
    return Offer(
        offer_id="OFF-0001",
        asp="A8",
        genre="習い事",
        offer_name="AI講座",
        reward="30000",
        target="AIを学びたい社会人",
        problem="学習内容や費用を比較したい",
        benefit="講座内容とサポートを比較できます",
        risk_level="中",
        brand_fit="要確認",
        memo="否認条件を確認してください",
        created_at=now,
        updated_at=now,
    )


def test_build_content_reviews_creates_rows_for_x_and_note():
    offer = make_offer()
    explanation = explain_score(offer)
    x_post = generate_x_post_for_offer(
        offer,
        score=explanation.score,
        score_explanation=explanation,
    )
    note_article = generate_note_article_for_offer(
        offer,
        score=explanation.score,
        score_explanation=explanation,
    )

    reviews = build_content_reviews(
        [x_post],
        [note_article],
        status="needs_revision",
        reviewer_comment="公式条件を再確認する",
    )

    assert [review.review_id for review in reviews] == [
        "x_post:OFF-0001",
        "note_article:OFF-0001",
    ]
    assert all(review.status == "needs_revision" for review in reviews)
    assert all(review.reviewer_comment == "公式条件を再確認する" for review in reviews)
    assert all(review.compliance_status == "passed" for review in reviews)
    assert reviews[0].score == explanation.score.total_score
    assert reviews[0].recommendation == explanation.score.recommendation


def test_write_content_reviews_csv(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [])
    output_path = tmp_path / "content_reviews.csv"

    saved_path = write_content_reviews_csv(reviews, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert "review_id,content_type,offer_id" in text
    assert "x_post:OFF-0001" in text
    assert ",draft," in text


def test_write_content_reviews_markdown(tmp_path):
    offer = make_offer()
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([], [note_article], status="on_hold")
    output_path = tmp_path / "content_reviews.md"

    saved_path = write_content_reviews_markdown(reviews, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_content_reviews_markdown(reviews) == text
    assert "# Content Reviews" in text
    assert "note_article:OFF-0001" in text
    assert "on_hold" in text
    assert "## Review Notes" in text


def test_normalize_review_status_validates_known_statuses():
    assert normalize_review_status(" APPROVED ") == "approved"
    with pytest.raises(ValueError, match="unknown review status"):
        normalize_review_status("pending")


def test_content_preview_compacts_and_truncates_text():
    text = "一行目\n\n二行目 " + "長い説明" * 40

    preview = content_preview(text, max_length=30)

    assert "\n" not in preview
    assert len(preview) <= 30
    assert preview.endswith("…")
