from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from affiliate_os.compliance import ComplianceReport, check_compliance
from affiliate_os.models import Offer
from affiliate_os.scoring import OfferScore, OfferScoreExplanation, explain_scores

MAX_X_POST_LENGTH = 280
DEFAULT_X_POSTS_OUTPUT_PATH = Path("outputs") / "generated" / "x_posts.md"
DEFAULT_NOTE_ARTICLES_OUTPUT_PATH = Path("outputs") / "generated" / "note_articles.md"
DEFAULT_CONTENT_PACK_DIR = Path("outputs") / "generated" / "content_pack"
CONTENT_TEMPLATES = ("comparison", "caution", "summary")
DEFAULT_CONTENT_TEMPLATE = "comparison"


@dataclass(frozen=True)
class XPostDraft:
    offer_id: str
    offer_name: str
    text: str
    compliance_report: ComplianceReport
    score: OfferScore | None = None
    score_explanation: OfferScoreExplanation | None = None
    template: str = DEFAULT_CONTENT_TEMPLATE

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
    score: OfferScore | None = None
    score_explanation: OfferScoreExplanation | None = None
    template: str = DEFAULT_CONTENT_TEMPLATE

    @property
    def passed_compliance(self) -> bool:
        return self.compliance_report.passed


@dataclass(frozen=True)
class ContentPack:
    x_posts: list[XPostDraft]
    note_articles: list[NoteArticleDraft]
    output_dir: Path
    x_posts_path: Path
    note_articles_path: Path
    compliance_summary_path: Path

    @property
    def passed_compliance(self) -> bool:
        return all(draft.passed_compliance for draft in self.x_posts + self.note_articles)


def generate_x_post_for_offer(
    offer: Offer,
    score: OfferScore | None = None,
    score_explanation: OfferScoreExplanation | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> XPostDraft:
    template = normalize_content_template(template)
    text = fit_x_post_length(
        build_x_post_text(
            offer,
            score=score,
            score_explanation=score_explanation,
            template=template,
        )
    )
    return XPostDraft(
        offer_id=offer.offer_id,
        offer_name=offer.offer_name,
        text=text,
        compliance_report=check_compliance(text),
        score=score,
        score_explanation=score_explanation,
        template=template,
    )


def generate_x_posts_for_offers(
    offers: list[Offer],
    scores: list[OfferScore] | None = None,
    score_explanations: list[OfferScoreExplanation] | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> list[XPostDraft]:
    scores_by_offer_id = map_scores_by_offer_id(scores)
    explanations_by_offer_id = map_score_explanations_by_offer_id(score_explanations)
    return [
        generate_x_post_for_offer(
            offer,
            score=scores_by_offer_id.get(offer.offer_id),
            score_explanation=explanations_by_offer_id.get(offer.offer_id),
            template=template,
        )
        for offer in offers
    ]


def generate_note_article_for_offer(
    offer: Offer,
    score: OfferScore | None = None,
    score_explanation: OfferScoreExplanation | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> NoteArticleDraft:
    template = normalize_content_template(template)
    title = build_note_article_title(offer, template=template)
    markdown = build_note_article_markdown(
        offer,
        title,
        score=score,
        score_explanation=score_explanation,
        template=template,
    )
    return NoteArticleDraft(
        offer_id=offer.offer_id,
        offer_name=offer.offer_name,
        title=title,
        markdown=markdown,
        compliance_report=check_compliance(markdown),
        score=score,
        score_explanation=score_explanation,
        template=template,
    )


def generate_note_articles_for_offers(
    offers: list[Offer],
    scores: list[OfferScore] | None = None,
    score_explanations: list[OfferScoreExplanation] | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> list[NoteArticleDraft]:
    scores_by_offer_id = map_scores_by_offer_id(scores)
    explanations_by_offer_id = map_score_explanations_by_offer_id(score_explanations)
    return [
        generate_note_article_for_offer(
            offer,
            score=scores_by_offer_id.get(offer.offer_id),
            score_explanation=explanations_by_offer_id.get(offer.offer_id),
            template=template,
        )
        for offer in offers
    ]


def generate_content_pack(
    offers: list[Offer],
    output_dir: Path,
    include_scores: bool = False,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> ContentPack:
    template = normalize_content_template(template)
    score_explanations = explain_scores(offers) if include_scores else None
    scores = [explanation.score for explanation in score_explanations or []] or None
    x_posts = generate_x_posts_for_offers(
        offers,
        scores=scores,
        score_explanations=score_explanations,
        template=template,
    )
    note_articles = generate_note_articles_for_offers(
        offers,
        scores=scores,
        score_explanations=score_explanations,
        template=template,
    )
    x_posts_path = output_dir / "x_posts.md"
    note_articles_path = output_dir / "note_articles.md"
    compliance_summary_path = output_dir / "compliance_summary.md"

    write_x_posts_markdown(x_posts, x_posts_path)
    write_note_articles_markdown(note_articles, note_articles_path)
    write_compliance_summary_markdown(x_posts, note_articles, compliance_summary_path)

    return ContentPack(
        x_posts=x_posts,
        note_articles=note_articles,
        output_dir=output_dir,
        x_posts_path=x_posts_path,
        note_articles_path=note_articles_path,
        compliance_summary_path=compliance_summary_path,
    )


def filter_offers_by_id(offers: list[Offer], offer_id: str | None) -> list[Offer]:
    if offer_id is None:
        return offers
    return [offer for offer in offers if offer.offer_id == offer_id]


def map_scores_by_offer_id(scores: list[OfferScore] | None) -> dict[str, OfferScore]:
    if scores is None:
        return {}
    return {score.offer_id: score for score in scores}


def map_score_explanations_by_offer_id(
    explanations: list[OfferScoreExplanation] | None,
) -> dict[str, OfferScoreExplanation]:
    if explanations is None:
        return {}
    return {explanation.score.offer_id: explanation for explanation in explanations}


def normalize_content_template(template: str) -> str:
    normalized = template.strip().lower()
    if normalized not in CONTENT_TEMPLATES:
        allowed = ", ".join(CONTENT_TEMPLATES)
        raise ValueError(f"unknown content template: {template}. allowed: {allowed}")
    return normalized


def build_x_post_text(
    offer: Offer,
    score: OfferScore | None = None,
    score_explanation: OfferScoreExplanation | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> str:
    template = normalize_content_template(template)
    target = offer.target or "検討している人"
    problem = offer.problem or "自分に合うか判断したい"
    benefit = offer.benefit or "選択肢のひとつとして比較できます"
    caution = build_offer_caution(offer)
    score_note = build_score_note(score)
    score_reason_note = build_score_reason_note(score_explanation)

    if template == "caution":
        text = (
            f"{offer.offer_name}の確認メモ。\n"
            f"検討前に見る点: {caution}。\n"
            f"{target}は、公式情報と条件を確認してから比較すると判断しやすくなります。"
        )
    elif template == "summary":
        text = (
            f"{offer.offer_name}は、{problem}人向けの比較候補です。\n"
            f"要点: {benefit}。\n"
            f"確認: {caution}"
        )
    else:
        text = (
            f"{target}向けの比較メモ。\n"
            f"{offer.offer_name}は、{problem}と感じている人が検討できる案件です。\n"
            f"見るポイント: {benefit}。\n"
            f"確認したい点: {caution}"
        )
    if score_note:
        text += f"\n評価メモ: {score_note}"
    if score_reason_note:
        text += f"\n理由: {score_reason_note}"
    return text


def build_note_article_title(offer: Offer, template: str = DEFAULT_CONTENT_TEMPLATE) -> str:
    template = normalize_content_template(template)
    if template == "caution":
        return f"{offer.offer_name}の申し込み前チェックリスト"
    if template == "summary":
        return f"{offer.offer_name}の要点整理"
    return f"{offer.offer_name}を検討するときの確認メモ"


def build_note_article_markdown(
    offer: Offer,
    title: str,
    score: OfferScore | None = None,
    score_explanation: OfferScoreExplanation | None = None,
    template: str = DEFAULT_CONTENT_TEMPLATE,
) -> str:
    template = normalize_content_template(template)
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
    ]
    if template == "caution":
        sections.extend(
            [
                "",
                "## チェックリスト",
                "",
                "- 公式ページの最新条件を確認する",
                "- 成果条件と否認条件を確認する",
                "- 自分の目的、予算、時間に合うか確認する",
                "- 医療、転職、金融領域に関わる場合は断定表現を避ける",
            ]
        )
    elif template == "summary":
        sections.extend(
            [
                "",
                "## 要点",
                "",
                f"- 検討対象: {offer.offer_name}",
                f"- 想定読者: {target}",
                f"- 比較ポイント: {benefit}",
                f"- 確認事項: {caution}",
            ]
        )
    if score is not None:
        sections.extend(
            [
                "",
                "## affiliate-os評価メモ",
                "",
                f"- 総合スコア: {score.total_score}/100",
                f"- 判定: {score.recommendation}",
                f"- 倫理リスクスコア: {score.ethical_risk_score}/100",
                f"- 成約難易度スコア: {score.conversion_difficulty_score}/100",
                f"- 注意コメント: {score.risk_comment or '特記事項なし'}",
            ]
        )
    if score_explanation is not None:
        sections.extend(["", "### 評価理由", ""])
        for reason in score_explanation.reasons:
            sections.append(f"- {reason.metric}: {reason.reason}")
    sections.extend(
        [
            "",
            "## 注意点",
            "",
            "- 医療、転職、金融など慎重な判断が必要な領域では、断定的な表現を避ける",
            "- 成果条件、否認条件、返金条件、最新の公式情報を確認する",
            "- 読者の状況によって向き不向きが変わるため、比較材料として扱う",
        ]
    )
    if offer.memo:
        sections.extend(["", "## メモ", "", offer.memo])
    return "\n".join(sections).strip() + "\n"


def build_score_note(score: OfferScore | None) -> str:
    if score is None:
        return ""
    note = f"{score.recommendation} / 総合{score.total_score}/100"
    if score.risk_comment:
        note += f"。{score.risk_comment}"
    return note


def build_score_reason_note(explanation: OfferScoreExplanation | None) -> str:
    if explanation is None:
        return ""

    prioritized_metrics = ("倫理リスク", "ブランド適合度", "悩みの深さ")
    reasons_by_metric = {reason.metric: reason for reason in explanation.reasons}
    selected = [
        reasons_by_metric[metric]
        for metric in prioritized_metrics
        if metric in reasons_by_metric
    ]
    if not selected:
        selected = explanation.reasons[:2]
    reason_texts = [f"{reason.metric}は{reason.score}/100" for reason in selected[:2]]
    return "、".join(reason_texts)


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

    preserved_lines = [
        line
        for line in text.splitlines()
        if line.startswith(("評価メモ:", "理由:"))
    ]
    if preserved_lines:
        body_lines = [
            line
            for line in text.splitlines()
            if not line.startswith(("評価メモ:", "理由:"))
        ]
        suffix = "\n詳細条件は公式情報で確認してください。"
        preserved_text = "\n".join(preserved_lines)
        tail = f"\n{preserved_text}{suffix}"
        max_body_length = MAX_X_POST_LENGTH - len(tail)
        if max_body_length > 40:
            body = "\n".join(body_lines)
            trimmed_body = body[:max_body_length].rstrip("、。\n ")
            return f"{trimmed_body}{tail}"

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


def write_compliance_summary_markdown(
    x_posts: list[XPostDraft],
    note_articles: list[NoteArticleDraft],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        format_compliance_summary_markdown(x_posts, note_articles), encoding="utf-8"
    )
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
                f"- template: {draft.template}",
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
                f"<!-- template: {draft.template} -->",
                "",
                draft.markdown,
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip("-\n") + "\n"


def format_compliance_summary_markdown(
    x_posts: list[XPostDraft],
    note_articles: list[NoteArticleDraft],
) -> str:
    lines = ["# Compliance Summary", ""]
    lines.extend(format_draft_summary_rows("X Posts", x_posts))
    lines.append("")
    lines.extend(format_draft_summary_rows("Note Articles", note_articles))
    return "\n".join(lines).rstrip() + "\n"


def format_draft_summary_rows(
    title: str,
    drafts: list[XPostDraft] | list[NoteArticleDraft],
) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| Offer ID | Status | Score | Recommendation | High Risk | Issues |",
        "| --- | --- | ---: | --- | ---: | ---: |",
    ]
    if not drafts:
        lines.append("| - | no target | - | - | 0 | 0 |")
        return lines

    for draft in drafts:
        status = "passed" if draft.passed_compliance else "needs review"
        total_score = "-" if draft.score is None else str(draft.score.total_score)
        recommendation = "-" if draft.score is None else draft.score.recommendation
        lines.append(
            "| "
            f"{draft.offer_id} | "
            f"{status} | "
            f"{total_score} | "
            f"{recommendation} | "
            f"{draft.compliance_report.high_risk_count} | "
            f"{len(draft.compliance_report.issues)} |"
        )
    return lines
