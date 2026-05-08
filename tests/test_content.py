from datetime import datetime

from affiliate_os.content import (
    CONTENT_TEMPLATES,
    MAX_X_POST_LENGTH,
    filter_offers_by_id,
    format_compliance_summary_markdown,
    format_note_articles_markdown,
    format_x_posts_markdown,
    generate_content_pack,
    generate_note_article_for_offer,
    generate_note_articles_for_offers,
    generate_x_post_for_offer,
    generate_x_posts_for_offers,
    normalize_content_template,
    write_note_articles_markdown,
    write_x_posts_markdown,
)
from affiliate_os.models import Offer
from affiliate_os.scoring import score_offer


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


def test_generate_x_post_can_include_score_context():
    offer = make_offer()
    score = score_offer(offer)

    draft = generate_x_post_for_offer(offer, score=score)

    assert draft.score == score
    assert "評価メモ:" in draft.text
    assert score.recommendation in draft.text


def test_generate_x_post_supports_caution_template():
    draft = generate_x_post_for_offer(make_offer(), template="caution")

    assert draft.template == "caution"
    assert "確認メモ" in draft.text
    assert "検討前に見る点" in draft.text
    assert draft.passed_compliance


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
    assert "- template: comparison" in text


def test_generate_note_article_for_offer_creates_compliant_markdown():
    draft = generate_note_article_for_offer(make_offer())

    assert draft.offer_id == "OFF-0001"
    assert draft.passed_compliance
    assert draft.title == "AI講座を検討するときの確認メモ"
    assert "# AI講座を検討するときの確認メモ" in draft.markdown
    assert "成果や効果を約束するものではありません" in draft.markdown
    assert "申し込み前に確認したいこと" in draft.markdown
    assert "必ず稼げる" not in draft.markdown
    assert "月100万円確定" not in draft.markdown


def test_generate_note_article_can_include_score_context():
    offer = make_offer()
    score = score_offer(offer)

    draft = generate_note_article_for_offer(offer, score=score)

    assert draft.score == score
    assert "## affiliate-os評価メモ" in draft.markdown
    assert f"- 総合スコア: {score.total_score}/100" in draft.markdown
    assert f"- 判定: {score.recommendation}" in draft.markdown


def test_generate_note_article_supports_summary_template():
    draft = generate_note_article_for_offer(make_offer(), template="summary")

    assert draft.template == "summary"
    assert draft.title == "AI講座の要点整理"
    assert "## 要点" in draft.markdown
    assert draft.passed_compliance


def test_generate_note_articles_for_offers_keeps_order():
    offers = [make_offer("OFF-0001"), make_offer("OFF-0002")]

    drafts = generate_note_articles_for_offers(offers)

    assert [draft.offer_id for draft in drafts] == ["OFF-0001", "OFF-0002"]


def test_format_and_write_note_articles_markdown(tmp_path):
    draft = generate_note_article_for_offer(make_offer())
    output_path = tmp_path / "note_articles.md"

    saved_path = write_note_articles_markdown([draft], output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_note_articles_markdown([draft]) == text
    assert "# Note Article Drafts" in text
    assert "<!-- offer_id: OFF-0001 -->" in text
    assert "<!-- template: comparison -->" in text


def test_format_compliance_summary_markdown():
    x_post = generate_x_post_for_offer(make_offer())
    note_article = generate_note_article_for_offer(make_offer())

    text = format_compliance_summary_markdown([x_post], [note_article])

    assert "# Compliance Summary" in text
    assert "## X Posts" in text
    assert "## Note Articles" in text
    assert "| OFF-0001 | passed | - | - | 0 | 0 |" in text


def test_generate_content_pack_writes_all_outputs(tmp_path):
    output_dir = tmp_path / "content_pack"

    pack = generate_content_pack([make_offer()], output_dir)

    assert pack.output_dir == output_dir
    assert pack.passed_compliance
    assert pack.x_posts_path.exists()
    assert pack.note_articles_path.exists()
    assert pack.compliance_summary_path.exists()
    assert "X Post Drafts" in pack.x_posts_path.read_text(encoding="utf-8")
    assert "Note Article Drafts" in pack.note_articles_path.read_text(encoding="utf-8")
    assert "Compliance Summary" in pack.compliance_summary_path.read_text(encoding="utf-8")


def test_generate_content_pack_can_include_scores(tmp_path):
    output_dir = tmp_path / "content_pack"

    pack = generate_content_pack([make_offer()], output_dir, include_scores=True)
    summary = pack.compliance_summary_path.read_text(encoding="utf-8")

    assert pack.x_posts[0].score is not None
    assert pack.note_articles[0].score is not None
    assert "Recommendation" in summary
    assert pack.x_posts[0].score.recommendation in summary


def test_generate_content_pack_can_use_template(tmp_path):
    output_dir = tmp_path / "content_pack"

    pack = generate_content_pack([make_offer()], output_dir, template="caution")

    assert pack.x_posts[0].template == "caution"
    assert pack.note_articles[0].template == "caution"
    assert "チェックリスト" in pack.note_articles_path.read_text(encoding="utf-8")


def test_normalize_content_template_validates_known_templates():
    assert normalize_content_template(" SUMMARY ") == "summary"
    assert set(CONTENT_TEMPLATES) == {"comparison", "caution", "summary"}
