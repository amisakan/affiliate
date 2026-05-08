from __future__ import annotations

from decimal import Decimal, InvalidOperation

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from affiliate_os.compliance import ComplianceReport, OfferComplianceReport
from affiliate_os.models import Offer, OfferDraft, format_decimal
from affiliate_os.scoring import OfferScore

console = Console()


def ask_required(prompt: str) -> str:
    while True:
        value = typer.prompt(prompt).strip()
        if value:
            return value
        console.print("[red]必須項目です。入力してください。[/red]")


def ask_optional(prompt: str) -> str:
    return typer.prompt(prompt, default="", show_default=False).strip()


def ask_decimal(prompt: str, required: bool = False) -> Decimal | None:
    while True:
        raw = typer.prompt(prompt, default="" if not required else None, show_default=False)
        raw = str(raw).strip()
        if not raw and not required:
            return None
        if not raw and required:
            console.print("[red]必須項目です。数値を入力してください。[/red]")
            continue
        try:
            value = Decimal(raw.replace(",", ""))
        except InvalidOperation:
            console.print("[red]数値を入力してください。例: 30000[/red]")
            continue
        if value < 0:
            console.print("[red]0以上の数値を入力してください。[/red]")
            continue
        return value


def ask_int(prompt: str) -> int | None:
    while True:
        raw = ask_optional(prompt)
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            console.print("[red]整数を入力してください。例: 30[/red]")
            continue
        if value < 0:
            console.print("[red]0以上の整数を入力してください。[/red]")
            continue
        return value


def render_offer_detail(offer: Offer) -> None:
    markdown = "\n".join(
        [
            f"# {offer.offer_name}",
            "",
            f"- 案件ID: {offer.offer_id}",
            f"- ASP: {offer.asp}",
            f"- ジャンル: {offer.genre}",
            f"- 報酬単価: {format_decimal(offer.reward)}",
            f"- 商品価格: {format_decimal(offer.price)}",
            f"- 報酬率: {offer.commission_rate}",
            f"- 承認率: {offer.approval_rate}",
            f"- Cookie期間: {'' if offer.cookie_days is None else offer.cookie_days}",
            f"- 想定ターゲット: {offer.target}",
            f"- 解決する悩み: {offer.problem}",
            f"- ベネフィット: {offer.benefit}",
            f"- リスクレベル: {offer.risk_level}",
            f"- ブランド相性: {offer.brand_fit}",
            f"- LP URL: {offer.lp_url}",
            f"- メモ: {offer.memo}",
        ]
    )
    console.print(Panel(markdown, title="登録内容", border_style="green"))


def render_offer_draft(draft: OfferDraft) -> None:
    markdown = "\n".join(
        [
            "# 抽出結果",
            "",
            f"- ASP: {draft.asp}",
            f"- ジャンル: {draft.genre}",
            f"- 案件名: {draft.offer_name}",
            f"- 報酬単価: {format_decimal(draft.reward)}",
            f"- 商品価格: {format_decimal(draft.price)}",
            f"- 報酬率: {draft.commission_rate}",
            f"- 承認率: {draft.approval_rate}",
            f"- Cookie期間: {'' if draft.cookie_days is None else draft.cookie_days}",
            f"- 想定ターゲット: {draft.target}",
            f"- 解決する悩み: {draft.problem}",
            f"- ベネフィット: {draft.benefit}",
            f"- リスクレベル: {draft.risk_level}",
            f"- ブランド相性: {draft.brand_fit}",
            f"- LP URL: {draft.lp_url}",
            f"- メモ: {draft.memo}",
        ]
    )
    missing = draft.missing_required_fields()
    if missing:
        markdown += "\n\n不足している必須項目: " + ", ".join(missing)
    console.print(Panel(markdown, title="画像からの取り込み下書き", border_style="cyan"))


def render_offer_table(offers: list[Offer]) -> None:
    if not offers:
        console.print("[yellow]該当する案件はありません。[/yellow]")
        return

    table = Table(title="Affiliate Offers")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("ASP")
    table.add_column("Genre")
    table.add_column("Offer")
    table.add_column("Reward", justify="right")
    table.add_column("Risk")
    table.add_column("Brand Fit")

    for offer in offers:
        table.add_row(
            offer.offer_id,
            offer.asp,
            offer.genre,
            offer.offer_name,
            format_decimal(offer.reward),
            offer.risk_level,
            offer.brand_fit,
        )
    console.print(table)


def render_score_ranking(scores: list[OfferScore]) -> None:
    lines = ["# 案件スコアリングランキング", ""]
    for rank, score in enumerate(scores, start=1):
        lines.extend(
            [
                f"## {rank}. {score.offer_name}",
                "",
                f"- 案件ID: {score.offer_id}",
                f"- ASP: {score.asp}",
                f"- ジャンル: {score.genre}",
                f"- 総合スコア: {score.total_score}/100",
                f"- 判定: {score.recommendation}",
                f"- 報酬単価: {score.reward_score}",
                f"- 承認率: {score.approval_rate_score}",
                f"- Cookie期間: {score.cookie_days_score}",
                f"- 悩みの深さ: {score.problem_depth_score}",
                f"- ブランド適合度: {score.brand_fit_score}",
                f"- 倫理リスク: {score.ethical_risk_score}",
                f"- 成約難易度: {score.conversion_difficulty_score}",
                f"- 長期資産性: {score.long_term_asset_score}",
            ]
        )
        if score.risk_comment:
            lines.append(f"- 注意コメント: {score.risk_comment}")
        lines.append("")
    console.print("\n".join(lines))


def render_compliance_report(report: ComplianceReport) -> None:
    if report.passed:
        console.print("[green]コンプライアンス上の明確なリスク表現は見つかりませんでした。[/green]")
        return

    table = Table(title="Compliance Check")
    table.add_column("Severity", style="cyan", no_wrap=True)
    table.add_column("Category")
    table.add_column("Matched")
    table.add_column("Message")
    table.add_column("Suggestion")

    for issue in report.issues:
        style = "red" if issue.severity == "high" else "yellow"
        table.add_row(
            issue.severity.value,
            issue.category,
            issue.matched_text,
            issue.message,
            issue.suggestion,
            style=style,
        )

    console.print(table)
    console.print(
        f"[yellow]検出件数: {len(report.issues)}件 / high: {report.high_risk_count}件[/yellow]"
    )


def render_offers_compliance_reports(reports: list[OfferComplianceReport]) -> None:
    if not reports:
        console.print("[yellow]チェック対象の案件がありません。[/yellow]")
        return

    risky_reports = [report for report in reports if not report.passed]
    if not risky_reports:
        console.print("[green]全案件で明確なリスク表現は見つかりませんでした。[/green]")
        return

    table = Table(title="Offer Compliance Check")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Genre")
    table.add_column("Offer")
    table.add_column("Severity")
    table.add_column("Category")
    table.add_column("Matched")
    table.add_column("Suggestion")

    for offer_report in risky_reports:
        for issue in offer_report.report.issues:
            style = "red" if issue.severity == "high" else "yellow"
            table.add_row(
                offer_report.offer_id,
                offer_report.genre,
                offer_report.offer_name,
                issue.severity.value,
                issue.category,
                issue.matched_text,
                issue.suggestion,
                style=style,
            )

    console.print(table)
    console.print(
        "[yellow]"
        f"リスクあり: {len(risky_reports)}件 / チェック対象: {len(reports)}件"
        "[/yellow]"
    )
