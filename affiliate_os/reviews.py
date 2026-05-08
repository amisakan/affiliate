from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from affiliate_os.content import NoteArticleDraft, XPostDraft

DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH = Path("outputs") / "generated" / "content_reviews.csv"
DEFAULT_CONTENT_REVIEWS_MARKDOWN_PATH = Path("outputs") / "generated" / "content_reviews.md"
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
