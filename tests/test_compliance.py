from datetime import datetime

from affiliate_os.compliance import (
    ComplianceSeverity,
    build_offer_compliance_text,
    check_compliance,
    check_offer_compliance,
    check_offers_compliance,
)
from affiliate_os.models import Offer


def test_check_compliance_detects_prohibited_income_claims():
    report = check_compliance("誰でも簡単に始められて、月100万円確定です。")

    assert not report.passed
    assert report.high_risk_count == 2
    assert {issue.matched_text for issue in report.issues} >= {"誰でも簡単", "月100万円確定"}


def test_check_compliance_detects_anxiety_phrases():
    report = check_compliance("今やらないと手遅れです。知らないと損します。")

    assert [issue.category for issue in report.issues] == ["不安訴求", "不安訴求"]
    assert all(issue.severity == ComplianceSeverity.MEDIUM for issue in report.issues)


def test_check_compliance_detects_sensitive_domain_assertions():
    report = check_compliance("転職サービスを使えば年収が上がります。金融投資でも利益が出ます。")

    assert not report.passed
    assert any("転職/金融領域の断定表現" == issue.category for issue in report.issues)
    assert {"年収が上がります", "利益が出ます"} <= {
        issue.matched_text for issue in report.issues
    }


def test_check_compliance_passes_decision_support_text():
    report = check_compliance(
        "この講座はAIを学びたい人の比較候補になります。費用、学習時間、サポート条件を確認してください。"
    )

    assert report.passed
    assert report.issues == []


def make_offer(
    offer_id: str = "OFF-0001",
    genre: str = "習い事",
    benefit: str = "",
    memo: str = "",
) -> Offer:
    now = datetime(2026, 5, 8, 12, 0)
    return Offer(
        offer_id=offer_id,
        asp="A8",
        genre=genre,
        offer_name="AI講座",
        reward="30000",
        target="AIを学びたい社会人",
        problem="学習内容や費用を比較したい",
        benefit=benefit,
        memo=memo,
        created_at=now,
        updated_at=now,
    )


def test_build_offer_compliance_text_includes_relevant_fields():
    offer = make_offer(benefit="比較候補になります", memo="条件を確認してください")

    text = build_offer_compliance_text(offer)

    assert "AI講座" in text
    assert "比較候補になります" in text
    assert "条件を確認してください" in text


def test_check_offer_compliance_detects_risky_offer_fields():
    offer = make_offer(genre="転職", benefit="このサービスなら年収が上がります")

    report = check_offer_compliance(offer)

    assert report.offer_id == "OFF-0001"
    assert not report.passed
    assert report.report.high_risk_count == 1
    assert report.report.issues[0].matched_text == "年収が上がります"


def test_check_offers_compliance_returns_report_for_each_offer():
    safe_offer = make_offer("OFF-0001", benefit="条件を比較できます")
    risky_offer = make_offer("OFF-0002", benefit="誰でも簡単に始められます")

    reports = check_offers_compliance([safe_offer, risky_offer])

    assert [report.offer_id for report in reports] == ["OFF-0001", "OFF-0002"]
    assert reports[0].passed
    assert not reports[1].passed
