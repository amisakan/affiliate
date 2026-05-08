from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from affiliate_os.models import Offer, format_decimal

DEFAULT_SCORES_PATH = Path("data") / "scores.csv"

SCORE_COLUMNS = [
    "offer_id",
    "asp",
    "genre",
    "offer_name",
    "reward_score",
    "approval_rate_score",
    "cookie_days_score",
    "problem_depth_score",
    "brand_fit_score",
    "ethical_risk_score",
    "conversion_difficulty_score",
    "long_term_asset_score",
    "total_score",
    "recommendation",
    "risk_comment",
    "scored_at",
]


@dataclass(frozen=True)
class OfferScore:
    offer_id: str
    asp: str
    genre: str
    offer_name: str
    reward_score: int
    approval_rate_score: int
    cookie_days_score: int
    problem_depth_score: int
    brand_fit_score: int
    ethical_risk_score: int
    conversion_difficulty_score: int
    long_term_asset_score: int
    total_score: int
    recommendation: str
    risk_comment: str
    scored_at: datetime

    def to_csv_row(self) -> dict[str, str]:
        return {
            "offer_id": self.offer_id,
            "asp": self.asp,
            "genre": self.genre,
            "offer_name": self.offer_name,
            "reward_score": str(self.reward_score),
            "approval_rate_score": str(self.approval_rate_score),
            "cookie_days_score": str(self.cookie_days_score),
            "problem_depth_score": str(self.problem_depth_score),
            "brand_fit_score": str(self.brand_fit_score),
            "ethical_risk_score": str(self.ethical_risk_score),
            "conversion_difficulty_score": str(self.conversion_difficulty_score),
            "long_term_asset_score": str(self.long_term_asset_score),
            "total_score": str(self.total_score),
            "recommendation": self.recommendation,
            "risk_comment": self.risk_comment,
            "scored_at": self.scored_at.isoformat(timespec="seconds"),
        }


@dataclass(frozen=True)
class ScoreReason:
    metric: str
    score: int
    reason: str


@dataclass(frozen=True)
class OfferScoreExplanation:
    score: OfferScore
    reasons: list[ScoreReason]

    def to_markdown(self) -> str:
        lines = [
            f"# {self.score.offer_name}",
            "",
            f"- 案件ID: {self.score.offer_id}",
            f"- ASP: {self.score.asp}",
            f"- ジャンル: {self.score.genre}",
            f"- 総合スコア: {self.score.total_score}/100",
            f"- 判定: {self.score.recommendation}",
        ]
        if self.score.risk_comment:
            lines.append(f"- 注意コメント: {self.score.risk_comment}")
        lines.extend(["", "## スコア理由", ""])
        for reason in self.reasons:
            lines.extend(
                [
                    f"### {reason.metric}: {reason.score}/100",
                    "",
                    reason.reason,
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"


def score_offer(offer: Offer, scored_at: datetime | None = None) -> OfferScore:
    scored_at = scored_at or datetime.now()
    reward = reward_score(offer.reward)
    approval = approval_rate_score(offer.approval_rate)
    cookie = cookie_days_score(offer.cookie_days)
    problem = problem_depth_score(offer)
    brand = brand_fit_score(offer.brand_fit)
    ethics = ethical_risk_score(offer)
    conversion = conversion_difficulty_score(offer, approval)
    asset = long_term_asset_score(offer)

    total = round(
        reward * 0.18
        + approval * 0.15
        + cookie * 0.10
        + problem * 0.14
        + brand * 0.13
        + ethics * 0.14
        + conversion * 0.08
        + asset * 0.08
    )
    recommendation = recommendation_for(total, ethics, conversion)
    risk_comment = risk_comment_for(offer, ethics, conversion)

    return OfferScore(
        offer_id=offer.offer_id,
        asp=offer.asp,
        genre=offer.genre,
        offer_name=offer.offer_name,
        reward_score=reward,
        approval_rate_score=approval,
        cookie_days_score=cookie,
        problem_depth_score=problem,
        brand_fit_score=brand,
        ethical_risk_score=ethics,
        conversion_difficulty_score=conversion,
        long_term_asset_score=asset,
        total_score=total,
        recommendation=recommendation,
        risk_comment=risk_comment,
        scored_at=scored_at,
    )


def explain_score(offer: Offer, scored_at: datetime | None = None) -> OfferScoreExplanation:
    score = score_offer(offer, scored_at=scored_at)
    reasons = [
        ScoreReason("報酬単価", score.reward_score, reward_reason(offer)),
        ScoreReason("承認率", score.approval_rate_score, approval_rate_reason(offer)),
        ScoreReason("Cookie期間", score.cookie_days_score, cookie_days_reason(offer)),
        ScoreReason("悩みの深さ", score.problem_depth_score, problem_depth_reason(offer)),
        ScoreReason("ブランド適合度", score.brand_fit_score, brand_fit_reason(offer)),
        ScoreReason("倫理リスク", score.ethical_risk_score, ethical_risk_reason(offer)),
        ScoreReason(
            "成約難易度",
            score.conversion_difficulty_score,
            conversion_difficulty_reason(offer, score.approval_rate_score),
        ),
        ScoreReason("長期資産性", score.long_term_asset_score, long_term_asset_reason(offer)),
    ]
    return OfferScoreExplanation(score=score, reasons=reasons)


def explain_scores(
    offers: list[Offer],
    scored_at: datetime | None = None,
) -> list[OfferScoreExplanation]:
    scored_at = scored_at or datetime.now()
    explanations = [explain_score(offer, scored_at=scored_at) for offer in offers]
    return sorted(explanations, key=lambda explanation: explanation.score.total_score, reverse=True)


def score_offers(offers: list[Offer], scored_at: datetime | None = None) -> list[OfferScore]:
    scored_at = scored_at or datetime.now()
    scores = [score_offer(offer, scored_at=scored_at) for offer in offers]
    return sorted(scores, key=lambda score: score.total_score, reverse=True)


def write_scores_csv(scores: list[OfferScore], path: Path = DEFAULT_SCORES_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SCORE_COLUMNS)
        writer.writeheader()
        for score in scores:
            writer.writerow(score.to_csv_row())
    return path


def write_score_explanations_markdown(
    explanations: list[OfferScoreExplanation],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = [explanation.to_markdown() for explanation in explanations]
    path.write_text("\n---\n\n".join(sections), encoding="utf-8")
    return path


def reward_score(reward: Decimal) -> int:
    if reward >= Decimal("50000"):
        return 100
    if reward >= Decimal("30000"):
        return 85
    if reward >= Decimal("15000"):
        return 70
    if reward >= Decimal("8000"):
        return 55
    if reward >= Decimal("3000"):
        return 40
    return 25


def reward_reason(offer: Offer) -> str:
    reward = format_decimal(offer.reward)
    if offer.reward >= Decimal("30000"):
        return f"報酬単価は{reward}で高めです。単価だけで判断せず、承認条件と読者適合を確認します。"
    if offer.reward >= Decimal("8000"):
        return f"報酬単価は{reward}で中程度です。比較記事や導線設計と合わせて検討します。"
    return f"報酬単価は{reward}です。収益性より読者にとっての適合性を優先して確認します。"


def approval_rate_score(value: str) -> int:
    rate = parse_percent(value)
    if rate is None:
        return 50
    if rate >= Decimal("80"):
        return 95
    if rate >= Decimal("60"):
        return 80
    if rate >= Decimal("40"):
        return 60
    if rate >= Decimal("20"):
        return 35
    return 20


def approval_rate_reason(offer: Offer) -> str:
    rate = parse_percent(offer.approval_rate)
    if rate is None:
        return "承認率が未確認です。成果見込みを断定せず、ASPや広告主の条件確認を優先します。"
    if rate >= Decimal("60"):
        return f"承認率は{offer.approval_rate}です。比較的確認しやすい材料ですが、否認条件も併せて見ます。"
    return f"承認率は{offer.approval_rate}です。成果条件、否認条件、申込後のハードルを慎重に確認します。"


def cookie_days_score(cookie_days: int | None) -> int:
    if cookie_days is None:
        return 50
    if cookie_days >= 90:
        return 90
    if cookie_days >= 60:
        return 75
    if cookie_days >= 30:
        return 60
    if cookie_days >= 7:
        return 40
    return 25


def cookie_days_reason(offer: Offer) -> str:
    if offer.cookie_days is None:
        return "Cookie期間が未確認です。再訪問による成果条件を公式情報で確認します。"
    if offer.cookie_days >= 60:
        return f"Cookie期間は{offer.cookie_days}日です。比較検討期間が長い案件でも確認しやすい条件です。"
    return f"Cookie期間は{offer.cookie_days}日です。検討期間が短くなりやすいため導線設計を確認します。"


def problem_depth_score(offer: Offer) -> int:
    text = searchable_text(offer)
    score = 45
    deep_keywords = [
        "転職",
        "就職",
        "医療",
        "金融",
        "介護",
        "障害",
        "診断",
        "悩み",
        "不安",
        "負担",
        "副業",
        "収入",
        "スキル",
    ]
    light_keywords = ["ポイント", "無料", "キャンペーン", "セルフバック"]
    score += sum(8 for keyword in deep_keywords if keyword in text)
    score -= sum(8 for keyword in light_keywords if keyword in text)
    if offer.problem:
        score += 12
    if offer.target:
        score += 6
    return clamp_score(score)


def problem_depth_reason(offer: Offer) -> str:
    text = searchable_text(offer)
    sensitive_hits = matched_keywords(text, ["転職", "就職", "医療", "金融", "副業", "収入", "スキル"])
    details = []
    if offer.problem:
        details.append("解決したい悩みが入力されています")
    if offer.target:
        details.append("想定ターゲットが入力されています")
    if sensitive_hits:
        details.append(f"深い検討につながりやすい語句: {', '.join(sensitive_hits)}")
    if not details:
        details.append("悩みやターゲットの情報が少ないため追加確認が必要です")
    return " / ".join(details)


def brand_fit_score(value: str) -> int:
    normalized = value.strip()
    if normalized in {"高", "高い", "非常に高い", "良い", "◎"}:
        return 90
    if normalized in {"中", "普通", "○"}:
        return 65
    if normalized in {"低", "低い", "悪い", "×"}:
        return 25
    if "要確認" in normalized or not normalized:
        return 50
    return 55


def brand_fit_reason(offer: Offer) -> str:
    value = offer.brand_fit.strip()
    if not value or "要確認" in value:
        return "ブランド適合度は要確認です。自分の発信テーマ、読者層、過去コンテンツとの整合を確認します。"
    return f"ブランド適合度は「{value}」です。読者の期待と紹介理由が自然につながるか確認します。"


def ethical_risk_score(offer: Offer) -> int:
    text = searchable_text(offer)
    risk = 5
    risk_level = offer.risk_level.strip()
    if risk_level in {"低", "低い"}:
        risk += 0
    elif risk_level in {"中", "普通"}:
        risk += 12
    elif risk_level in {"高", "高い"}:
        risk += 45
    elif "要確認" in risk_level:
        risk += 22

    sensitive_keywords = [
        "医療",
        "金融",
        "転職",
        "就職",
        "障害",
        "診断",
        "投資",
        "借入",
        "ローン",
        "保険",
    ]
    denial_keywords = [
        "否認",
        "本人",
        "NG",
        "不正",
        "いたずら",
        "キャンセル",
        "リスティング違反",
        "連絡がつかない",
        "悪質",
    ]
    hype_keywords = ["必ず", "誰でも", "簡単", "確定", "月100万", "稼げる"]
    risk += sum(6 for keyword in sensitive_keywords if keyword in text)
    risk += sum(3 for keyword in denial_keywords if keyword in text)
    risk += sum(12 for keyword in hype_keywords if keyword in text)

    return clamp_score(100 - risk)


def ethical_risk_reason(offer: Offer) -> str:
    text = searchable_text(offer)
    hits = matched_keywords(
        text,
        ["医療", "金融", "転職", "就職", "障害", "診断", "投資", "借入", "ローン", "保険"],
    )
    denial_hits = matched_keywords(text, ["否認", "本人", "NG", "リスティング違反", "キャンセル"])
    parts = []
    if offer.risk_level:
        parts.append(f"リスクレベル: {offer.risk_level}")
    if hits:
        parts.append(f"慎重な表現が必要な語句: {', '.join(hits)}")
    if denial_hits:
        parts.append(f"条件確認が必要な語句: {', '.join(denial_hits)}")
    if not parts:
        parts.append("明確な高リスク語句は少ないですが、最新条件と表現の確認は必要です")
    return " / ".join(parts)


def conversion_difficulty_score(offer: Offer, approval_score: int) -> int:
    text = searchable_text(offer)
    score = 70
    difficult_keywords = [
        "説明会",
        "面談",
        "入金",
        "受講",
        "審査",
        "診断",
        "医師",
        "連絡がつかない",
        "受講意思",
    ]
    easy_keywords = ["無料登録", "資料請求", "商品リンク", "スマホ最適化"]
    score -= sum(8 for keyword in difficult_keywords if keyword in text)
    score += sum(6 for keyword in easy_keywords if keyword in text)
    if offer.reward >= Decimal("30000"):
        score -= 10
    if approval_score < 50:
        score -= 12
    elif approval_score >= 80:
        score += 8
    return clamp_score(score)


def conversion_difficulty_reason(offer: Offer, approval_score: int) -> str:
    text = searchable_text(offer)
    difficult_hits = matched_keywords(text, ["説明会", "面談", "入金", "受講", "審査", "診断"])
    parts = []
    if difficult_hits:
        parts.append(f"成約前のハードルになり得る語句: {', '.join(difficult_hits)}")
    if offer.reward >= Decimal("30000"):
        parts.append("高単価のため検討・成約ハードルが上がる可能性があります")
    if approval_score < 50:
        parts.append("承認率スコアが低いため成果条件の確認が必要です")
    if not parts:
        parts.append("明確な高ハードル要素は少ないですが、申込条件と導線を確認します")
    return " / ".join(parts)


def long_term_asset_score(offer: Offer) -> int:
    text = searchable_text(offer)
    score = 45
    asset_keywords = [
        "AI",
        "Web",
        "IT",
        "スキル",
        "学習",
        "講座",
        "スクール",
        "転職",
        "キャリア",
        "資格",
        "比較",
        "基礎",
    ]
    short_lived_keywords = ["キャンペーン", "期間限定", "セール", "ポイント"]
    score += sum(7 for keyword in asset_keywords if keyword in text)
    score -= sum(10 for keyword in short_lived_keywords if keyword in text)
    if offer.benefit:
        score += 6
    return clamp_score(score)


def long_term_asset_reason(offer: Offer) -> str:
    text = searchable_text(offer)
    asset_hits = matched_keywords(text, ["AI", "Web", "IT", "スキル", "学習", "講座", "比較", "基礎"])
    short_hits = matched_keywords(text, ["キャンペーン", "期間限定", "セール", "ポイント"])
    parts = []
    if asset_hits:
        parts.append(f"長期記事化しやすい語句: {', '.join(asset_hits)}")
    if short_hits:
        parts.append(f"短期要素として確認する語句: {', '.join(short_hits)}")
    if offer.benefit:
        parts.append("ベネフィットが入力されており記事構成に使いやすいです")
    if not parts:
        parts.append("長期資産化の観点は追加情報を確認します")
    return " / ".join(parts)


def recommendation_for(total_score: int, ethical_score: int, conversion_score: int) -> str:
    if ethical_score < 35 or total_score < 45:
        return "非推奨"
    if total_score >= 72 and ethical_score >= 50 and conversion_score >= 45:
        return "推奨"
    return "保留"


def risk_comment_for(offer: Offer, ethical_score: int, conversion_score: int) -> str:
    comments = []
    text = searchable_text(offer)
    if ethical_score < 50:
        comments.append("倫理・コンプライアンス面の確認を優先")
    if any(keyword in text for keyword in ["医療", "金融", "転職", "就職", "障害", "診断"]):
        comments.append("断定表現や不安訴求を避ける")
    if any(keyword in text for keyword in ["否認", "本人", "NG", "リスティング違反", "キャンセル"]):
        comments.append("成果条件・否認条件を記事作成前に確認")
    if conversion_score < 45:
        comments.append("成約ハードルが高いため比較・導線設計が必要")
    return " / ".join(dict.fromkeys(comments))


def parse_percent(value: str) -> Decimal | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    if not match:
        return None
    try:
        return Decimal(match.group())
    except InvalidOperation:
        return None


def searchable_text(offer: Offer) -> str:
    return " ".join(
        [
            offer.asp,
            offer.genre,
            offer.offer_name,
            offer.commission_rate,
            offer.approval_rate,
            offer.target,
            offer.problem,
            offer.benefit,
            offer.risk_level,
            offer.brand_fit,
            offer.lp_url,
            offer.memo,
            format_decimal(offer.reward),
            format_decimal(offer.price),
        ]
    )


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def clamp_score(value: int) -> int:
    return max(0, min(100, value))
