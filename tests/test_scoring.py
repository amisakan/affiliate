from datetime import datetime
from decimal import Decimal

from affiliate_os.models import Offer
from affiliate_os.scoring import (
    approval_rate_score,
    cookie_days_score,
    explain_score,
    explain_scores,
    recommendation_for,
    reward_score,
    score_offer,
    score_offers,
    write_score_explanations_markdown,
    write_scores_csv,
)


def make_offer(
    offer_id: str = "OFF-0001",
    reward: str = "30000",
    approval_rate: str = "60%",
    cookie_days: int | None = 90,
    genre: str = "習い事",
    risk_level: str = "中",
    brand_fit: str = "高",
    memo: str = "",
) -> Offer:
    now = datetime(2026, 5, 8, 10, 0)
    return Offer(
        offer_id=offer_id,
        asp="A8",
        genre=genre,
        offer_name=f"Offer {offer_id}",
        reward=reward,
        approval_rate=approval_rate,
        cookie_days=cookie_days,
        target="副業やスキルアップを考える社会人",
        problem="本業にも活かせるスキルを学びたい",
        benefit="AIとWebスキルを体系的に学べる",
        risk_level=risk_level,
        brand_fit=brand_fit,
        memo=memo,
        created_at=now,
        updated_at=now,
    )


def test_basic_score_functions():
    assert reward_score(Decimal("30000")) == 85
    assert approval_rate_score("55.85%") == 60
    assert approval_rate_score("-") == 50
    assert cookie_days_score(90) == 90
    assert cookie_days_score(None) == 50


def test_score_offer_returns_recommendation_and_risk_comment():
    offer = make_offer(
        genre="就職・転職",
        risk_level="要確認",
        memo="否認条件: 医師の診断を受けている、本人申込NG、リスティング違反",
    )

    score = score_offer(offer, scored_at=datetime(2026, 5, 8, 11, 0))

    assert score.offer_id == "OFF-0001"
    assert score.recommendation in {"推奨", "保留", "非推奨"}
    assert "断定表現や不安訴求を避ける" in score.risk_comment
    assert "成果条件・否認条件を記事作成前に確認" in score.risk_comment


def test_score_offers_sorts_by_total_score():
    stronger = make_offer("OFF-0001", reward="50000", approval_rate="85%", brand_fit="高")
    weaker = make_offer(
        "OFF-0002", reward="3000", approval_rate="20%", brand_fit="低", risk_level="高"
    )

    scores = score_offers([weaker, stronger], scored_at=datetime(2026, 5, 8, 11, 0))

    assert [score.offer_id for score in scores] == ["OFF-0001", "OFF-0002"]


def test_write_scores_csv(tmp_path):
    output_path = tmp_path / "scores.csv"
    scores = [score_offer(make_offer(), scored_at=datetime(2026, 5, 8, 11, 0))]

    write_scores_csv(scores, output_path)

    text = output_path.read_text(encoding="utf-8")
    assert "offer_id,asp,genre,offer_name" in text
    assert "OFF-0001" in text


def test_recommendation_thresholds():
    assert recommendation_for(80, 70, 60) == "推奨"
    assert recommendation_for(60, 70, 60) == "保留"
    assert recommendation_for(80, 20, 60) == "非推奨"


def test_explain_score_returns_reason_markdown():
    explanation = explain_score(
        make_offer(memo="否認条件: 本人申込NG"),
        scored_at=datetime(2026, 5, 8, 11, 0),
    )

    markdown = explanation.to_markdown()

    assert explanation.score.offer_id == "OFF-0001"
    assert len(explanation.reasons) == 8
    assert "# Offer OFF-0001" in markdown
    assert "## スコア理由" in markdown
    assert "報酬単価" in markdown
    assert "成果条件・否認条件" in explanation.score.risk_comment


def test_explain_scores_sorts_by_total_score():
    stronger = make_offer("OFF-0001", reward="50000", approval_rate="85%", brand_fit="高")
    weaker = make_offer(
        "OFF-0002", reward="3000", approval_rate="20%", brand_fit="低", risk_level="高"
    )

    explanations = explain_scores([weaker, stronger], scored_at=datetime(2026, 5, 8, 11, 0))

    assert [explanation.score.offer_id for explanation in explanations] == [
        "OFF-0001",
        "OFF-0002",
    ]


def test_write_score_explanations_markdown(tmp_path):
    output_path = tmp_path / "score_explanations.md"
    explanations = [explain_score(make_offer(), scored_at=datetime(2026, 5, 8, 11, 0))]

    write_score_explanations_markdown(explanations, output_path)

    text = output_path.read_text(encoding="utf-8")
    assert "## スコア理由" in text
    assert "### 報酬単価" in text
