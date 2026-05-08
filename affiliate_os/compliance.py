from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from affiliate_os.models import Offer


class ComplianceSeverity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ComplianceIssue:
    category: str
    severity: ComplianceSeverity
    matched_text: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class ComplianceReport:
    text: str
    issues: list[ComplianceIssue]

    @property
    def passed(self) -> bool:
        return not self.issues

    @property
    def high_risk_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == ComplianceSeverity.HIGH)


@dataclass(frozen=True)
class OfferComplianceReport:
    offer_id: str
    offer_name: str
    genre: str
    report: ComplianceReport

    @property
    def passed(self) -> bool:
        return self.report.passed


PROHIBITED_PHRASES = [
    "誰でも簡単",
    "必ず稼げる",
    "月100万円確定",
    "絶対稼げる",
    "確実に稼げる",
]

HYPE_PHRASES = [
    "絶対",
    "確実",
    " guaranteed ",
    "100%稼げる",
    "失敗しない",
    "今すぐ稼げる",
]

ANXIETY_PHRASES = [
    "知らないと損",
    "今やらないと手遅れ",
    "取り残される",
    "人生が終わる",
    "後悔します",
]

SENSITIVE_DOMAIN_KEYWORDS = {
    "医療": ["医療", "診断", "治療", "病気", "症状", "医師", "クリニック", "薬"],
    "転職": ["転職", "就職", "キャリア", "退職", "年収", "採用", "面接"],
    "金融": ["金融", "投資", "保険", "ローン", "借入", "資産運用", "クレジット"],
}

ASSERTIVE_PHRASES = [
    "治ります",
    "改善します",
    "成功します",
    "採用されます",
    "年収が上がります",
    "儲かります",
    "利益が出ます",
    "安全です",
    "リスクはありません",
    "保証します",
]


def check_compliance(text: str) -> ComplianceReport:
    normalized_text = text.strip()
    issues: list[ComplianceIssue] = []

    issues.extend(detect_prohibited_phrases(normalized_text))
    issues.extend(detect_hype_phrases(normalized_text))
    issues.extend(detect_anxiety_phrases(normalized_text))
    issues.extend(detect_sensitive_domain_assertions(normalized_text))

    return ComplianceReport(text=normalized_text, issues=dedupe_issues(issues))


def check_offer_compliance(offer: Offer) -> OfferComplianceReport:
    report = check_compliance(build_offer_compliance_text(offer))
    return OfferComplianceReport(
        offer_id=offer.offer_id,
        offer_name=offer.offer_name,
        genre=offer.genre,
        report=report,
    )


def check_offers_compliance(offers: list[Offer]) -> list[OfferComplianceReport]:
    return [check_offer_compliance(offer) for offer in offers]


def build_offer_compliance_text(offer: Offer) -> str:
    values = [
        offer.genre,
        offer.offer_name,
        offer.target,
        offer.problem,
        offer.benefit,
        offer.risk_level,
        offer.brand_fit,
        offer.memo,
    ]
    return "\n".join(value for value in values if value)


def detect_prohibited_phrases(text: str) -> list[ComplianceIssue]:
    return [
        ComplianceIssue(
            category="禁止表現",
            severity=ComplianceSeverity.HIGH,
            matched_text=phrase,
            message="収益や容易さを断定する表現です。",
            suggestion="条件、向き不向き、必要な確認事項を併記してください。",
        )
        for phrase in PROHIBITED_PHRASES
        if phrase in text
    ]


def detect_hype_phrases(text: str) -> list[ComplianceIssue]:
    return [
        ComplianceIssue(
            category="誇大表現",
            severity=ComplianceSeverity.MEDIUM,
            matched_text=phrase.strip(),
            message="成果や安全性を強く断定する可能性があります。",
            suggestion="事実ベースの表現にし、個人差や条件を補ってください。",
        )
        for phrase in HYPE_PHRASES
        if phrase in text
    ]


def detect_anxiety_phrases(text: str) -> list[ComplianceIssue]:
    return [
        ComplianceIssue(
            category="不安訴求",
            severity=ComplianceSeverity.MEDIUM,
            matched_text=phrase,
            message="読者の不安や焦りを過度に刺激する可能性があります。",
            suggestion="判断材料や比較観点を示す表現に置き換えてください。",
        )
        for phrase in ANXIETY_PHRASES
        if phrase in text
    ]


def detect_sensitive_domain_assertions(text: str) -> list[ComplianceIssue]:
    domains = [
        domain
        for domain, keywords in SENSITIVE_DOMAIN_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    if not domains:
        return []

    return [
        ComplianceIssue(
            category=f"{'/'.join(domains)}領域の断定表現",
            severity=ComplianceSeverity.HIGH,
            matched_text=phrase,
            message="医療、転職、金融などの慎重な説明が必要な領域で断定表現があります。",
            suggestion="効果や結果を約束せず、条件、リスク、専門家確認の余地を示してください。",
        )
        for phrase in ASSERTIVE_PHRASES
        if phrase in text
    ]


def dedupe_issues(issues: list[ComplianceIssue]) -> list[ComplianceIssue]:
    seen: set[tuple[str, str]] = set()
    unique: list[ComplianceIssue] = []
    for issue in issues:
        key = (issue.category, issue.matched_text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique
