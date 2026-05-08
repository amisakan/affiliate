from affiliate_os.compliance import ComplianceSeverity, check_compliance


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
