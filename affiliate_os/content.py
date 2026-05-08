from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from affiliate_os.compliance import ComplianceReport, check_compliance
from affiliate_os.models import Offer

MAX_X_POST_LENGTH = 280
DEFAULT_X_POSTS_OUTPUT_PATH = Path("outputs") / "generated" / "x_posts.md"


@dataclass(frozen=True)
class XPostDraft:
    offer_id: str
    offer_name: str
    text: str
    compliance_report: ComplianceReport

    @property
    def passed_compliance(self) -> bool:
        return self.compliance_report.passed


def generate_x_post_for_offer(offer: Offer) -> XPostDraft:
    text = fit_x_post_length(build_x_post_text(offer))
    return XPostDraft(
        offer_id=offer.offer_id,
        offer_name=offer.offer_name,
        text=text,
        compliance_report=check_compliance(text),
    )


def generate_x_posts_for_offers(offers: list[Offer]) -> list[XPostDraft]:
    return [generate_x_post_for_offer(offer) for offer in offers]


def filter_offers_by_id(offers: list[Offer], offer_id: str | None) -> list[Offer]:
    if offer_id is None:
        return offers
    return [offer for offer in offers if offer.offer_id == offer_id]


def build_x_post_text(offer: Offer) -> str:
    target = offer.target or "検討している人"
    problem = offer.problem or "自分に合うか判断したい"
    benefit = offer.benefit or "選択肢のひとつとして比較できます"
    caution = build_offer_caution(offer)

    return (
        f"{target}向けの比較メモ。\n"
        f"{offer.offer_name}は、{problem}と感じている人が検討できる案件です。\n"
        f"見るポイント: {benefit}。\n"
        f"確認したい点: {caution}"
    )


def build_offer_caution(offer: Offer) -> str:
    cautions = []
    if offer.price is not None:
        cautions.append("費用")
    if offer.approval_rate:
        cautions.append("承認条件")
    if offer.cookie_days is not None:
        cautions.append("Cookie期間")
    if offer.risk_level:
        cautions.append(f"リスクレベル: {offer.risk_level}")
    if offer.memo:
        cautions.append("否認条件や注意事項")
    if not cautions:
        cautions.append("公式情報と条件")
    return "、".join(cautions)


def fit_x_post_length(text: str) -> str:
    if len(text) <= MAX_X_POST_LENGTH:
        return text

    suffix = "\n詳細条件は公式情報で確認してください。"
    max_body_length = MAX_X_POST_LENGTH - len(suffix)
    return text[:max_body_length].rstrip("、。\n ") + suffix


def write_x_posts_markdown(drafts: list[XPostDraft], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_x_posts_markdown(drafts), encoding="utf-8")
    return output_path


def format_x_posts_markdown(drafts: list[XPostDraft]) -> str:
    lines = ["# X Post Drafts", ""]
    for draft in drafts:
        status = "passed" if draft.passed_compliance else "needs review"
        lines.extend(
            [
                f"## {draft.offer_id}: {draft.offer_name}",
                "",
                f"- compliance: {status}",
                "",
                "```text",
                draft.text,
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
