from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from affiliate_os.content import NoteArticleDraft, XPostDraft

DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH = Path("outputs") / "generated" / "content_reviews.csv"
DEFAULT_CONTENT_REVIEWS_MARKDOWN_PATH = Path("outputs") / "generated" / "content_reviews.md"
DEFAULT_APPROVED_CONTENT_OUTPUT_PATH = (
    Path("outputs") / "generated" / "approved_content.csv"
)
DEFAULT_APPROVED_CONTENT_MARKDOWN_PATH = (
    Path("outputs") / "generated" / "approved_content.md"
)
DEFAULT_REVISION_SUGGESTIONS_OUTPUT_PATH = (
    Path("outputs") / "generated" / "revision_suggestions.csv"
)
DEFAULT_REVISION_SUGGESTIONS_MARKDOWN_PATH = (
    Path("outputs") / "generated" / "revision_suggestions.md"
)
REVIEW_STATUSES = ("draft", "approved", "needs_revision", "rejected", "on_hold")
DEFAULT_REVIEW_STATUS = "draft"
REVIEW_COLUMNS = [
    "review_id",
    "content_type",
    "offer_id",
    "offer_name",
    "title",
    "status",
    "reviewer_comment",
    "compliance_status",
    "high_risk_count",
    "issue_count",
    "score",
    "recommendation",
    "template",
    "content_preview",
    "reviewed_at",
]
REVISION_SUGGESTION_COLUMNS = [
    "review_id",
    "content_type",
    "offer_id",
    "offer_name",
    "title",
    "revision_reason",
    "suggestion",
    "reviewer_comment",
    "compliance_status",
    "score",
    "recommendation",
    "content_preview",
]


@dataclass(frozen=True)
class ContentReview:
    review_id: str
    content_type: str
    offer_id: str
    offer_name: str
    title: str
    status: str
    reviewer_comment: str
    compliance_status: str
    high_risk_count: int
    issue_count: int
    score: int | None
    recommendation: str
    template: str
    content_preview: str
    reviewed_at: datetime

    def to_csv_row(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "content_type": self.content_type,
            "offer_id": self.offer_id,
            "offer_name": self.offer_name,
            "title": self.title,
            "status": self.status,
            "reviewer_comment": self.reviewer_comment,
            "compliance_status": self.compliance_status,
            "high_risk_count": str(self.high_risk_count),
            "issue_count": str(self.issue_count),
            "score": "" if self.score is None else str(self.score),
            "recommendation": self.recommendation,
            "template": self.template,
            "content_preview": self.content_preview,
            "reviewed_at": self.reviewed_at.isoformat(timespec="seconds"),
        }


@dataclass(frozen=True)
class ContentReviewUpdateResult:
    reviews: list[ContentReview]
    updated_review: ContentReview | None

    @property
    def updated(self) -> bool:
        return self.updated_review is not None


@dataclass(frozen=True)
class RevisionSuggestion:
    review_id: str
    content_type: str
    offer_id: str
    offer_name: str
    title: str
    revision_reason: str
    suggestion: str
    reviewer_comment: str
    compliance_status: str
    score: int | None
    recommendation: str
    content_preview: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "content_type": self.content_type,
            "offer_id": self.offer_id,
            "offer_name": self.offer_name,
            "title": self.title,
            "revision_reason": self.revision_reason,
            "suggestion": self.suggestion,
            "reviewer_comment": self.reviewer_comment,
            "compliance_status": self.compliance_status,
            "score": "" if self.score is None else str(self.score),
            "recommendation": self.recommendation,
            "content_preview": self.content_preview,
        }


def build_content_reviews(
    x_posts: list[XPostDraft],
    note_articles: list[NoteArticleDraft],
    status: str = DEFAULT_REVIEW_STATUS,
    reviewer_comment: str = "",
    reviewed_at: datetime | None = None,
) -> list[ContentReview]:
    normalized_status = normalize_review_status(status)
    reviewed_at = reviewed_at or datetime.now()
    reviews = [
        build_x_post_review(
            draft,
            status=normalized_status,
            reviewer_comment=reviewer_comment,
            reviewed_at=reviewed_at,
        )
        for draft in x_posts
    ]
    reviews.extend(
        build_note_article_review(
            draft,
            status=normalized_status,
            reviewer_comment=reviewer_comment,
            reviewed_at=reviewed_at,
        )
        for draft in note_articles
    )
    return reviews


def build_x_post_review(
    draft: XPostDraft,
    status: str = DEFAULT_REVIEW_STATUS,
    reviewer_comment: str = "",
    reviewed_at: datetime | None = None,
) -> ContentReview:
    return ContentReview(
        review_id=f"x_post:{draft.offer_id}",
        content_type="x_post",
        offer_id=draft.offer_id,
        offer_name=draft.offer_name,
        title="X投稿案",
        status=normalize_review_status(status),
        reviewer_comment=reviewer_comment,
        compliance_status=compliance_status_for(draft.passed_compliance),
        high_risk_count=draft.compliance_report.high_risk_count,
        issue_count=len(draft.compliance_report.issues),
        score=None if draft.score is None else draft.score.total_score,
        recommendation="" if draft.score is None else draft.score.recommendation,
        template=draft.template,
        content_preview=content_preview(draft.text),
        reviewed_at=reviewed_at or datetime.now(),
    )


def build_note_article_review(
    draft: NoteArticleDraft,
    status: str = DEFAULT_REVIEW_STATUS,
    reviewer_comment: str = "",
    reviewed_at: datetime | None = None,
) -> ContentReview:
    return ContentReview(
        review_id=f"note_article:{draft.offer_id}",
        content_type="note_article",
        offer_id=draft.offer_id,
        offer_name=draft.offer_name,
        title=draft.title,
        status=normalize_review_status(status),
        reviewer_comment=reviewer_comment,
        compliance_status=compliance_status_for(draft.passed_compliance),
        high_risk_count=draft.compliance_report.high_risk_count,
        issue_count=len(draft.compliance_report.issues),
        score=None if draft.score is None else draft.score.total_score,
        recommendation="" if draft.score is None else draft.score.recommendation,
        template=draft.template,
        content_preview=content_preview(draft.markdown),
        reviewed_at=reviewed_at or datetime.now(),
    )


def normalize_review_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in REVIEW_STATUSES:
        allowed = ", ".join(REVIEW_STATUSES)
        raise ValueError(f"unknown review status: {status}. allowed: {allowed}")
    return normalized


def load_content_reviews_csv(path: Path) -> list[ContentReview]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [content_review_from_row(row) for row in reader]


def content_review_from_row(row: dict[str, str]) -> ContentReview:
    return ContentReview(
        review_id=row.get("review_id", ""),
        content_type=row.get("content_type", ""),
        offer_id=row.get("offer_id", ""),
        offer_name=row.get("offer_name", ""),
        title=row.get("title", ""),
        status=normalize_review_status(row.get("status", DEFAULT_REVIEW_STATUS)),
        reviewer_comment=row.get("reviewer_comment", ""),
        compliance_status=row.get("compliance_status", ""),
        high_risk_count=parse_int(row.get("high_risk_count", "0")),
        issue_count=parse_int(row.get("issue_count", "0")),
        score=parse_optional_int(row.get("score", "")),
        recommendation=row.get("recommendation", ""),
        template=row.get("template", ""),
        content_preview=row.get("content_preview", ""),
        reviewed_at=parse_datetime(row.get("reviewed_at", "")),
    )


def update_content_review(
    reviews: list[ContentReview],
    review_id: str,
    status: str,
    reviewer_comment: str | None = None,
    reviewed_at: datetime | None = None,
) -> ContentReviewUpdateResult:
    normalized_status = normalize_review_status(status)
    reviewed_at = reviewed_at or datetime.now()
    updated_review = None
    updated_reviews = []
    for review in reviews:
        if review.review_id == review_id:
            updated_review = replace(
                review,
                status=normalized_status,
                reviewer_comment=(
                    review.reviewer_comment
                    if reviewer_comment is None
                    else reviewer_comment
                ),
                reviewed_at=reviewed_at,
            )
            updated_reviews.append(updated_review)
        else:
            updated_reviews.append(review)
    return ContentReviewUpdateResult(
        reviews=updated_reviews,
        updated_review=updated_review,
    )


def update_content_review_csv(
    input_path: Path,
    review_id: str,
    status: str,
    reviewer_comment: str | None = None,
    output_path: Path | None = None,
    reviewed_at: datetime | None = None,
) -> ContentReviewUpdateResult:
    reviews = load_content_reviews_csv(input_path)
    result = update_content_review(
        reviews,
        review_id=review_id,
        status=status,
        reviewer_comment=reviewer_comment,
        reviewed_at=reviewed_at,
    )
    if result.updated:
        write_content_reviews_csv(result.reviews, output_path or input_path)
    return result


def approved_content_reviews(reviews: list[ContentReview]) -> list[ContentReview]:
    approved = [review for review in reviews if review.status == "approved"]
    return sorted(
        approved,
        key=lambda review: (
            review.reviewed_at,
            review.offer_id,
            review.content_type,
        ),
        reverse=True,
    )


def write_approved_content_csv(
    reviews: list[ContentReview],
    output_path: Path = DEFAULT_APPROVED_CONTENT_OUTPUT_PATH,
) -> Path:
    return write_content_reviews_csv(approved_content_reviews(reviews), output_path)


def write_approved_content_markdown(
    reviews: list[ContentReview],
    output_path: Path = DEFAULT_APPROVED_CONTENT_MARKDOWN_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_approved_content_markdown(reviews), encoding="utf-8")
    return output_path


def format_approved_content_markdown(reviews: list[ContentReview]) -> str:
    approved = approved_content_reviews(reviews)
    lines = [
        "# Approved Content",
        "",
        "| Review ID | Type | Offer | Score | Recommendation | Reviewed At |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    if not approved:
        lines.append("| - | - | no approved content | - | - | - |")
        return "\n".join(lines) + "\n"

    for review in approved:
        score = "-" if review.score is None else str(review.score)
        lines.append(
            "| "
            f"{review.review_id} | "
            f"{review.content_type} | "
            f"{review.offer_id} | "
            f"{score} | "
            f"{review.recommendation or '-'} | "
            f"{review.reviewed_at.isoformat(timespec='seconds')} |"
        )
    lines.extend(["", "## Publishing Notes", ""])
    for review in approved:
        comment = review.reviewer_comment or "最終公開前に公式条件を確認する"
        lines.extend(
            [
                f"### {review.review_id}",
                "",
                f"- 案件名: {review.offer_name}",
                f"- タイトル: {review.title}",
                f"- コンプライアンス: {review.compliance_status}",
                f"- コメント: {comment}",
                f"- プレビュー: {review.content_preview}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def needs_revision_reviews(reviews: list[ContentReview]) -> list[ContentReview]:
    revision_targets = [review for review in reviews if review.status == "needs_revision"]
    return sorted(
        revision_targets,
        key=lambda review: (
            review.high_risk_count,
            review.issue_count,
            review.reviewed_at,
        ),
        reverse=True,
    )


def build_revision_suggestions(reviews: list[ContentReview]) -> list[RevisionSuggestion]:
    return [
        build_revision_suggestion(review)
        for review in needs_revision_reviews(reviews)
    ]


def build_revision_suggestion(review: ContentReview) -> RevisionSuggestion:
    return RevisionSuggestion(
        review_id=review.review_id,
        content_type=review.content_type,
        offer_id=review.offer_id,
        offer_name=review.offer_name,
        title=review.title,
        revision_reason=revision_reason_for(review),
        suggestion=revision_suggestion_for(review),
        reviewer_comment=review.reviewer_comment,
        compliance_status=review.compliance_status,
        score=review.score,
        recommendation=review.recommendation,
        content_preview=review.content_preview,
    )


def revision_reason_for(review: ContentReview) -> str:
    reasons = []
    if review.high_risk_count > 0:
        reasons.append(f"highリスク表現が{review.high_risk_count}件あります")
    if review.issue_count > 0:
        reasons.append(f"コンプライアンス確認項目が{review.issue_count}件あります")
    if review.reviewer_comment:
        reasons.append(f"レビューコメント: {review.reviewer_comment}")
    if review.score is not None and review.score < 70:
        reasons.append(f"スコアが{review.score}/100のため、訴求軸と条件確認を見直します")
    if not reasons:
        reasons.append("レビュー状態がneeds_revisionです")
    return " / ".join(reasons)


def revision_suggestion_for(review: ContentReview) -> str:
    suggestions = [
        "成果や効果を断定せず、比較材料として読める表現に整える",
        "公式条件、成果条件、否認条件、費用を確認する文を残す",
    ]
    if review.high_risk_count > 0 or review.issue_count > 0:
        suggestions.append("強い断定、収益保証、不安訴求に見える表現を弱める")
    if review.reviewer_comment:
        suggestions.append("レビューコメントの確認事項を本文またはチェックリストに反映する")
    if review.content_type == "x_post":
        suggestions.append("X投稿では短くしすぎず、最終確認を促す一文を残す")
    if review.content_type == "note_article":
        suggestions.append("note記事では見出し単位で確認事項と注意点を分ける")
    return " / ".join(suggestions)


def write_revision_suggestions_csv(
    suggestions: list[RevisionSuggestion],
    output_path: Path = DEFAULT_REVISION_SUGGESTIONS_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVISION_SUGGESTION_COLUMNS)
        writer.writeheader()
        for suggestion in suggestions:
            writer.writerow(suggestion.to_csv_row())
    return output_path


def write_revision_suggestions_markdown(
    suggestions: list[RevisionSuggestion],
    output_path: Path = DEFAULT_REVISION_SUGGESTIONS_MARKDOWN_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_revision_suggestions_markdown(suggestions), encoding="utf-8")
    return output_path


def format_revision_suggestions_markdown(suggestions: list[RevisionSuggestion]) -> str:
    lines = [
        "# Revision Suggestions",
        "",
        "| Review ID | Type | Offer | Compliance | Score | Reason |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    if not suggestions:
        lines.append("| - | - | no revision targets | - | - | - |")
        return "\n".join(lines) + "\n"

    for suggestion in suggestions:
        score = "-" if suggestion.score is None else str(suggestion.score)
        lines.append(
            "| "
            f"{suggestion.review_id} | "
            f"{suggestion.content_type} | "
            f"{suggestion.offer_id} | "
            f"{suggestion.compliance_status} | "
            f"{score} | "
            f"{suggestion.revision_reason} |"
        )
    lines.extend(["", "## Suggestions", ""])
    for suggestion in suggestions:
        lines.extend(
            [
                f"### {suggestion.review_id}",
                "",
                f"- 案件名: {suggestion.offer_name}",
                f"- タイトル: {suggestion.title}",
                f"- 修正提案: {suggestion.suggestion}",
                f"- プレビュー: {suggestion.content_preview}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_optional_int(value: str) -> int | None:
    if not value:
        return None
    return parse_int(value)


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0)


def compliance_status_for(passed: bool) -> str:
    return "passed" if passed else "needs_review"


def content_preview(text: str, max_length: int = 120) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "…"


def write_content_reviews_csv(
    reviews: list[ContentReview],
    output_path: Path = DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for review in reviews:
            writer.writerow(review.to_csv_row())
    return output_path


def write_content_reviews_markdown(
    reviews: list[ContentReview],
    output_path: Path = DEFAULT_CONTENT_REVIEWS_MARKDOWN_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_content_reviews_markdown(reviews), encoding="utf-8")
    return output_path


def format_content_reviews_markdown(reviews: list[ContentReview]) -> str:
    lines = [
        "# Content Reviews",
        "",
        "| Review ID | Type | Offer | Status | Compliance | Score | Recommendation | Comment |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    if not reviews:
        lines.append("| - | - | - | no target | - | - | - | - |")
        return "\n".join(lines) + "\n"

    for review in reviews:
        score = "-" if review.score is None else str(review.score)
        comment = review.reviewer_comment or "-"
        lines.append(
            "| "
            f"{review.review_id} | "
            f"{review.content_type} | "
            f"{review.offer_id} | "
            f"{review.status} | "
            f"{review.compliance_status} | "
            f"{score} | "
            f"{review.recommendation or '-'} | "
            f"{comment} |"
        )
    lines.extend(["", "## Review Notes", ""])
    for review in reviews:
        lines.extend(
            [
                f"### {review.review_id}",
                "",
                f"- 案件名: {review.offer_name}",
                f"- タイトル: {review.title}",
                f"- テンプレート: {review.template}",
                f"- プレビュー: {review.content_preview}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
