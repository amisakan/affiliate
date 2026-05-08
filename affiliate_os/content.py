from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from affiliate_os.compliance import ComplianceReport, check_compliance
from affiliate_os.models import Offer

MAX_X_POST_LENGTH = 280
DEFAULT_X_POSTS_OUTPUT_PATH = Path("outputs") / "generated" / "x_posts.md"
DEFAULT_NOTE_ARTICLES_OUTPUT_PATH = Path("outputs") / "generated" / "note_articles.md"


@dataclass(frozen=True)
class XPostDraft:
    offer_id: str
    offer_name: str
    text: str
    compliance_report: ComplianceReport

    @property
    def passed_compliance(self) -> bool:
        return self.compliance_report.passed


@dataclass(frozen=True)
class NoteArticleDraft:
    offer_id: str
    offer_name: str
    title: str
    markdown: str
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


def generate_note_article_for_offer(offer: Offer) -> NoteArticleDraft:
    title = build_note_article_title(offer)
    markdown = build_note_article_markdown(offer, title)
    return NoteArticleDraft(
        offer_id=offer.offer_id,
        offer_name=offer.offer_name,
        title=title,
        markdown=markdown,
        compliance_report=check_compliance(markdown),
    )


def generate_note_articles_for_offers(offers: list[Offer]) -> list[NoteArticleDraft]:
    return [generate_note_article_for_offer(offer) for offer in offers]


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


def build_note_article_title(offer: Offer) -> str:
    return f"{offer.offer_name}を検討するときの確認メモ"


def build_note_article_markdown(offer: Offer, title: str) -> str:
    target = offer.target or "この案件を検討している人"
    problem = offer.problem or "自分に合うか判断したい"
    benefit = offer.benefit or "比較候補として確認できます"
    caution = build_offer_caution(offer)
    price = "要確認" if offer.price is None else str(offer.price)
    cookie_days = "要確認" if offer.cookie_days is None else f"{offer.cookie_days}日"

    sections = [
        f"# {title}",
        "",
        "## この記事の目的",
        "",
        (
            f"この記事は、{target}が「{offer.offer_name}」を検討するときに、"
            "条件や注意点を整理するための下書きです。成果や効果を約束するものではありません。"
        ),
        "",
        "## どんな人が検討しやすいか",
        "",
        f"- {problem}と感じている人",
        "- 公式情報、費用、条件を確認したうえで比較したい人",
        "",
        "## 期待できるポイント",
        "",
        f"- {benefit}",
        "- 自分の目的、予算、学習時間、サポート条件に合うかを確認しやすい",
        "",
        "## 申し込み前に確認したいこと",
        "",
        f"- 商品価格: {price}",
        f"- 承認率: {offer.approval_rate or '要確認'}",
        f"- Cookie期間: {cookie_days}",
        f"- リスクレベル: {offer.risk_level or '要確認'}",
        f"- その他: {caution}",
        "",
        "## 注意点",
        "",
        "- 医療、転職、金融など慎重な判断が必要な領域では、断定的な表現を避ける",
        "- 成果条件、否認条件、返金条件、最新の公式情報を確認する",
        "- 読者の状況によって向き不向きが変わるため、比較材料として扱う",
    ]
    if offer.memo:
        sections.extend(["", "## メモ", "", offer.memo])
    return "\n".join(sections).strip() + "\n"


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


def write_note_articles_markdown(drafts: list[NoteArticleDraft], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_note_articles_markdown(drafts), encoding="utf-8")
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


def format_note_articles_markdown(drafts: list[NoteArticleDraft]) -> str:
    lines = ["# Note Article Drafts", ""]
    for draft in drafts:
        status = "passed" if draft.passed_compliance else "needs review"
        lines.extend(
            [
                f"<!-- offer_id: {draft.offer_id} -->",
                f"<!-- compliance: {status} -->",
                "",
                draft.markdown,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip("-\n") + "\n"
