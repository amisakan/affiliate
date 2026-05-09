from datetime import datetime

import pytest

from affiliate_os.content import generate_note_article_for_offer, generate_x_post_for_offer
from affiliate_os.models import Offer
from affiliate_os.reviews import (
    approved_content_reviews,
    build_content_reviews,
    build_content_rewrite_drafts,
    build_revision_suggestions,
    content_preview,
    format_approved_content_markdown,
    format_content_reviews_markdown,
    format_content_rewrite_drafts_markdown,
    format_revision_suggestions_markdown,
    load_content_reviews_csv,
    needs_revision_reviews,
    normalize_review_status,
    update_content_review,
    update_content_review_csv,
    write_approved_content_csv,
    write_approved_content_markdown,
    write_content_reviews_csv,
    write_content_reviews_markdown,
    write_content_rewrite_drafts_markdown,
    write_revision_suggestions_csv,
    write_revision_suggestions_markdown,
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


def test_load_content_reviews_csv_round_trips_rows(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviewed_at = datetime(2026, 5, 8, 14, 0)
    reviews = build_content_reviews(
        [x_post],
        [],
        status="approved",
        reviewed_at=reviewed_at,
    )
    output_path = tmp_path / "content_reviews.csv"
    write_content_reviews_csv(reviews, output_path)

    loaded = load_content_reviews_csv(output_path)

    assert loaded == reviews


def test_update_content_review_changes_status_and_comment():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([x_post], [note_article])

    result = update_content_review(
        reviews,
        review_id="x_post:OFF-0001",
        status="approved",
        reviewer_comment="公開候補として扱う",
    )

    assert result.updated
    assert result.updated_review is not None
    assert result.updated_review.status == "approved"
    assert result.updated_review.reviewer_comment == "公開候補として扱う"
    assert result.reviews[1].status == "draft"


def test_update_content_review_keeps_comment_when_not_provided():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews(
        [x_post],
        [],
        status="needs_revision",
        reviewer_comment="条件を確認する",
    )

    result = update_content_review(
        reviews,
        review_id="x_post:OFF-0001",
        status="on_hold",
    )

    assert result.updated_review is not None
    assert result.updated_review.status == "on_hold"
    assert result.updated_review.reviewer_comment == "条件を確認する"


def test_update_content_review_returns_not_updated_for_unknown_id():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [])

    result = update_content_review(
        reviews,
        review_id="x_post:OFF-9999",
        status="approved",
    )

    assert not result.updated
    assert result.updated_review is None
    assert result.reviews == reviews


def test_update_content_review_csv_writes_updated_rows(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [])
    output_path = tmp_path / "content_reviews.csv"
    write_content_reviews_csv(reviews, output_path)

    result = update_content_review_csv(
        output_path,
        review_id="x_post:OFF-0001",
        status="rejected",
        reviewer_comment="条件確認が必要",
    )
    loaded = load_content_reviews_csv(output_path)

    assert result.updated
    assert loaded[0].status == "rejected"
    assert loaded[0].reviewer_comment == "条件確認が必要"


def test_approved_content_reviews_filters_and_sorts_approved_rows():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews(
        [x_post],
        [note_article],
        reviewed_at=datetime(2026, 5, 8, 14, 0),
    )
    first_update = update_content_review(
        reviews,
        review_id="x_post:OFF-0001",
        status="approved",
        reviewer_comment="公開候補",
        reviewed_at=datetime(2026, 5, 8, 15, 0),
    )
    second_update = update_content_review(
        first_update.reviews,
        review_id="note_article:OFF-0001",
        status="approved",
        reviewer_comment="記事候補",
        reviewed_at=datetime(2026, 5, 8, 16, 0),
    )

    approved = approved_content_reviews(second_update.reviews)

    assert [review.review_id for review in approved] == [
        "note_article:OFF-0001",
        "x_post:OFF-0001",
    ]
    assert all(review.status == "approved" for review in approved)


def test_write_approved_content_csv_only_writes_approved_rows(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([x_post], [note_article])
    result = update_content_review(
        reviews,
        review_id="x_post:OFF-0001",
        status="approved",
    )
    output_path = tmp_path / "approved_content.csv"

    saved_path = write_approved_content_csv(result.reviews, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert "x_post:OFF-0001" in text
    assert "note_article:OFF-0001" not in text


def test_write_approved_content_markdown(tmp_path):
    offer = make_offer()
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([], [note_article])
    result = update_content_review(
        reviews,
        review_id="note_article:OFF-0001",
        status="approved",
        reviewer_comment="公開前にLP条件を確認する",
    )
    output_path = tmp_path / "approved_content.md"

    saved_path = write_approved_content_markdown(result.reviews, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_approved_content_markdown(result.reviews) == text
    assert "# Approved Content" in text
    assert "note_article:OFF-0001" in text
    assert "公開前にLP条件を確認する" in text


def test_needs_revision_reviews_filters_revision_targets():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([x_post], [note_article])
    updated = update_content_review(
        reviews,
        review_id="note_article:OFF-0001",
        status="needs_revision",
        reviewer_comment="注意点を本文に追加する",
    )

    targets = needs_revision_reviews(updated.reviews)

    assert [review.review_id for review in targets] == ["note_article:OFF-0001"]
    assert targets[0].reviewer_comment == "注意点を本文に追加する"


def test_build_revision_suggestions_uses_review_context():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [])
    updated = update_content_review(
        reviews,
        review_id="x_post:OFF-0001",
        status="needs_revision",
        reviewer_comment="成果条件を明記する",
    )

    suggestions = build_revision_suggestions(updated.reviews)

    assert len(suggestions) == 1
    assert suggestions[0].review_id == "x_post:OFF-0001"
    assert "レビューコメント: 成果条件を明記する" in suggestions[0].revision_reason
    assert "成果や効果を断定せず" in suggestions[0].suggestion
    assert "X投稿" in suggestions[0].suggestion


def test_write_revision_suggestions_csv(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [], status="needs_revision")
    suggestions = build_revision_suggestions(reviews)
    output_path = tmp_path / "revision_suggestions.csv"

    saved_path = write_revision_suggestions_csv(suggestions, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert "review_id,content_type,offer_id" in text
    assert "x_post:OFF-0001" in text


def test_write_revision_suggestions_markdown(tmp_path):
    offer = make_offer()
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews([], [note_article], status="needs_revision")
    suggestions = build_revision_suggestions(reviews)
    output_path = tmp_path / "revision_suggestions.md"

    saved_path = write_revision_suggestions_markdown(suggestions, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_revision_suggestions_markdown(suggestions) == text
    assert "# Revision Suggestions" in text
    assert "note_article:OFF-0001" in text
    assert "note記事では見出し単位" in text


def test_build_content_rewrite_drafts_creates_safe_x_post_draft():
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews(
        [x_post],
        [],
        status="needs_revision",
        reviewer_comment="費用と否認条件を残す",
    )

    drafts = build_content_rewrite_drafts(reviews)

    assert len(drafts) == 1
    assert drafts[0].review_id == "x_post:OFF-0001"
    assert "公式条件、成果条件、否認条件、費用" in drafts[0].markdown
    assert "費用と否認条件を残す" in drafts[0].markdown
    assert "自動公開しない" in drafts[0].safety_notes
    assert len(drafts[0].markdown) <= 280


def test_build_content_rewrite_drafts_creates_note_article_checklist():
    offer = make_offer()
    note_article = generate_note_article_for_offer(offer)
    reviews = build_content_reviews(
        [],
        [note_article],
        status="needs_revision",
        reviewer_comment="成果条件を明記する",
    )

    drafts = build_content_rewrite_drafts(reviews)

    assert len(drafts) == 1
    assert drafts[0].content_type == "note_article"
    assert "## 申し込み前に確認したいこと" in drafts[0].markdown
    assert "- 成果条件" in drafts[0].markdown
    assert "- 否認条件" in drafts[0].markdown
    assert "成果や効果を約束するものではありません" in drafts[0].markdown


def test_write_content_rewrite_drafts_markdown(tmp_path):
    offer = make_offer()
    x_post = generate_x_post_for_offer(offer)
    reviews = build_content_reviews([x_post], [], status="needs_revision")
    drafts = build_content_rewrite_drafts(reviews)
    output_path = tmp_path / "rewrite_content_drafts.md"

    saved_path = write_content_rewrite_drafts_markdown(drafts, output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_content_rewrite_drafts_markdown(drafts) == text
    assert "# Rewrite Content Drafts" in text
    assert "自動公開はしません" in text
    assert "x_post:OFF-0001" in text


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
