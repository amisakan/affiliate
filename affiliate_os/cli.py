from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import typer

from affiliate_os.compliance import check_compliance, check_offers_compliance
from affiliate_os.content import (
    CONTENT_TEMPLATES,
    DEFAULT_CONTENT_PACK_DIR,
    filter_offers_by_id,
    generate_content_pack,
    generate_note_articles_for_offers,
    generate_x_posts_for_offers,
    normalize_content_template,
    write_note_articles_markdown,
    write_x_posts_markdown,
)
from affiliate_os.importers.reviewer import (
    build_offer_from_draft,
    complete_required_fields,
    confirm_save,
)
from affiliate_os.importers.vision_importer import extract_offer_from_image
from affiliate_os.models import Offer
from affiliate_os.quiet_workflow import (
    DEFAULT_METRICS_PATH,
    DEFAULT_POSTS_OUTPUT_DIR,
    DEFAULT_POSTS_PATH,
    DEFAULT_THEMES_PATH,
    append_posts,
    ensure_quiet_workflow_csvs,
    find_theme,
    generate_quiet_workflow_posts,
    load_posts,
    load_themes,
    next_post_number,
    validate_quiet_workflow_posts,
    write_posts_markdown,
)
from affiliate_os.reviews import (
    DEFAULT_APPROVED_CONTENT_MARKDOWN_PATH,
    DEFAULT_APPROVED_CONTENT_OUTPUT_PATH,
    DEFAULT_CONTENT_REVIEWS_MARKDOWN_PATH,
    DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
    DEFAULT_REVISION_SUGGESTIONS_MARKDOWN_PATH,
    DEFAULT_REVISION_SUGGESTIONS_OUTPUT_PATH,
    DEFAULT_REWRITE_CONTENT_DRAFTS_MARKDOWN_PATH,
    REVIEW_STATUSES,
    approved_content_reviews,
    build_content_reviews,
    build_content_rewrite_drafts,
    build_revision_suggestions,
    load_content_reviews_csv,
    normalize_review_status,
    update_content_review_csv,
    write_approved_content_csv,
    write_approved_content_markdown,
    write_content_reviews_csv,
    write_content_reviews_markdown,
    write_content_rewrite_drafts_markdown,
    write_revision_suggestions_csv,
    write_revision_suggestions_markdown,
)
from affiliate_os.scoring import (
    DEFAULT_SCORES_PATH,
    explain_scores,
    score_offers,
    write_score_explanations_markdown,
    write_scores_csv,
)
from affiliate_os.storage import (
    DEFAULT_DATA_PATH,
    append_offer,
    filter_offers,
    load_offers,
    next_offer_id,
)
from affiliate_os.utils import (
    ask_decimal,
    ask_int,
    ask_optional,
    ask_required,
    console,
    render_compliance_report,
    render_content_pack,
    render_content_reviews,
    render_note_article_drafts,
    render_offer_detail,
    render_offer_draft,
    render_offer_table,
    render_offers_compliance_reports,
    render_score_explanations,
    render_score_ranking,
    render_x_post_drafts,
)

app = typer.Typer(help="信頼型アフィリエイト運用OSのMVP CLI")


@app.command("add-offer")
def add_offer(
    data_path: Path = typer.Option(DEFAULT_DATA_PATH, "--data-path", help="offers.csv の保存先"),
) -> None:
    """対話形式で新規アフィリエイト案件を追加します。"""
    offer_id = next_offer_id(data_path)
    now = datetime.now()

    offer = Offer(
        offer_id=offer_id,
        asp=ask_required("ASP名"),
        genre=ask_required("ジャンル"),
        offer_name=ask_required("案件名"),
        reward=ask_decimal("報酬単価", required=True),
        price=ask_decimal("商品価格"),
        commission_rate=ask_optional("報酬率"),
        approval_rate=ask_optional("承認率"),
        cookie_days=ask_int("Cookie期間（日数）"),
        target=ask_optional("想定ターゲット"),
        problem=ask_optional("解決する悩み"),
        benefit=ask_optional("ベネフィット"),
        risk_level=ask_optional("リスクレベル"),
        brand_fit=ask_optional("自分のブランドとの相性"),
        lp_url=ask_optional("LP URL"),
        memo=ask_optional("メモ"),
        created_at=now,
        updated_at=now,
    )

    append_offer(offer, data_path)
    console.print("[green]案件を登録しました。[/green]")
    render_offer_detail(offer)


@app.command("list-offers")
def list_offers(
    genre: str | None = typer.Option(None, "--genre", help="ジャンルで絞り込み"),
    asp: str | None = typer.Option(None, "--asp", help="ASP名で絞り込み"),
    min_reward: str | None = typer.Option(None, "--min-reward", help="最低報酬単価で絞り込み"),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
) -> None:
    """登録済み案件の一覧を表示します。"""
    min_reward_value = parse_min_reward(min_reward)
    offers = load_offers(data_path)
    render_offer_table(filter_offers(offers, genre=genre, asp=asp, min_reward=min_reward_value))


@app.command("import-offer")
def import_offer(
    from_image: Path = typer.Option(..., "--from-image", help="案件スクリーンショット画像のパス"),
    yes: bool = typer.Option(False, "--yes", "-y", help="必須項目が揃っていれば確認なしで保存"),
    dry_run: bool = typer.Option(False, "--dry-run", help="CSVには保存せず抽出結果だけ表示"),
    model: str | None = typer.Option(
        None, "--model", help="OpenAIモデル名。未指定時は環境変数または既定値を使用"
    ),
    data_path: Path = typer.Option(DEFAULT_DATA_PATH, "--data-path", help="offers.csv の保存先"),
) -> None:
    """画像から案件情報を抽出してCSVに取り込みます。"""
    draft = extract_offer_from_image(from_image, model=model)
    render_offer_draft(draft)

    if dry_run:
        console.print("[yellow]dry-run のため保存しませんでした。[/yellow]")
        return

    if draft.missing_required_fields():
        console.print("[yellow]必須項目が不足しています。不足分だけ入力してください。[/yellow]")
        draft = complete_required_fields(draft)

    offer = build_offer_from_draft(draft, data_path)
    render_offer_detail(offer)
    if not confirm_save(yes):
        console.print("[yellow]保存をキャンセルしました。[/yellow]")
        return

    append_offer(offer, data_path)
    console.print("[green]案件を登録しました。[/green]")


@app.command("score-offers")
def score_offers_command(
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path = typer.Option(
        DEFAULT_SCORES_PATH, "--output-path", help="scores.csv の保存先"
    ),
) -> None:
    """登録済み案件をルールベースでスコアリングします。"""
    offers = load_offers(data_path)
    if not offers:
        console.print("[yellow]スコアリング対象の案件がありません。[/yellow]")
        return

    scores = score_offers(offers)
    write_scores_csv(scores, output_path)
    console.print(f"[green]スコアを保存しました: {output_path}[/green]")
    render_score_ranking(scores)


@app.command("explain-scores")
def explain_scores_command(
    offer_id: str | None = typer.Option(None, "--offer-id", help="特定の案件IDだけ表示"),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="Markdown保存先。未指定時は保存しません"
    ),
) -> None:
    """登録済み案件のスコア理由を表示します。"""
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    if offer_id and not offers:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return
    explanations = explain_scores(offers)
    render_score_explanations(explanations)
    if output_path:
        saved_path = write_score_explanations_markdown(explanations, output_path)
        console.print(f"[green]スコア理由を保存しました: {saved_path}[/green]")


@app.command("check-text")
def check_text(
    text: str | None = typer.Argument(None, help="チェック対象テキスト"),
    file_path: Path | None = typer.Option(None, "--file", "-f", help="チェック対象ファイル"),
) -> None:
    """テキストの誇大表現、禁止表現、断定表現をチェックします。"""
    target_text = read_check_target(text=text, file_path=file_path)
    report = check_compliance(target_text)
    render_compliance_report(report)


@app.command("check-offers")
def check_offers(
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
) -> None:
    """登録済み案件のメモやベネフィットをまとめてコンプライアンスチェックします。"""
    offers = load_offers(data_path)
    reports = check_offers_compliance(offers)
    render_offers_compliance_reports(reports)


@app.command("generate-x-posts")
def generate_x_posts(
    offer_id: str | None = typer.Option(None, "--offer-id", help="特定の案件IDだけ生成"),
    with_scores: bool = typer.Option(False, "--with-scores", help="スコアリング結果を反映"),
    template: str = typer.Option(
        "comparison", "--template", help=f"生成テンプレート: {', '.join(CONTENT_TEMPLATES)}"
    ),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="Markdown保存先。未指定時は保存しません"
    ),
) -> None:
    """登録済み案件から信頼型のX投稿案を生成します。"""
    template = parse_content_template(template)
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    score_explanations = explain_scores(offers) if with_scores else None
    scores = [explanation.score for explanation in score_explanations or []] or None
    drafts = generate_x_posts_for_offers(
        offers,
        scores=scores,
        score_explanations=score_explanations,
        template=template,
    )
    render_x_post_drafts(drafts)
    if offer_id and not drafts:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return
    if output_path:
        saved_path = write_x_posts_markdown(drafts, output_path)
        console.print(f"[green]X投稿案を保存しました: {saved_path}[/green]")


@app.command("generate-note-articles")
def generate_note_articles(
    offer_id: str | None = typer.Option(None, "--offer-id", help="特定の案件IDだけ生成"),
    with_scores: bool = typer.Option(False, "--with-scores", help="スコアリング結果を反映"),
    template: str = typer.Option(
        "comparison", "--template", help=f"生成テンプレート: {', '.join(CONTENT_TEMPLATES)}"
    ),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="Markdown保存先。未指定時は保存しません"
    ),
) -> None:
    """登録済み案件からnote記事下書きを生成します。"""
    template = parse_content_template(template)
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    score_explanations = explain_scores(offers) if with_scores else None
    scores = [explanation.score for explanation in score_explanations or []] or None
    drafts = generate_note_articles_for_offers(
        offers,
        scores=scores,
        score_explanations=score_explanations,
        template=template,
    )
    render_note_article_drafts(drafts)
    if offer_id and not drafts:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return
    if output_path:
        saved_path = write_note_articles_markdown(drafts, output_path)
        console.print(f"[green]note記事下書きを保存しました: {saved_path}[/green]")


@app.command("generate-content-pack")
def generate_content_pack_command(
    offer_id: str | None = typer.Option(None, "--offer-id", help="特定の案件IDだけ生成"),
    with_scores: bool = typer.Option(False, "--with-scores", help="スコアリング結果を反映"),
    template: str = typer.Option(
        "comparison", "--template", help=f"生成テンプレート: {', '.join(CONTENT_TEMPLATES)}"
    ),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_dir: Path = typer.Option(
        DEFAULT_CONTENT_PACK_DIR, "--output-dir", help="生成物の保存先ディレクトリ"
    ),
) -> None:
    """X投稿案、note記事下書き、コンプライアンス概要をまとめて生成します。"""
    template = parse_content_template(template)
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    if offer_id and not offers:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return
    pack = generate_content_pack(
        offers,
        output_dir,
        include_scores=with_scores,
        template=template,
    )
    render_content_pack(pack)


@app.command("generate-posts")
def generate_posts_command(
    theme_id: str = typer.Option(..., "--theme", help="投稿テーマID。例: 001"),
    count: int = typer.Option(5, "--count", min=1, help="生成する投稿案の数"),
    themes_path: Path = typer.Option(
        DEFAULT_THEMES_PATH,
        "--themes-path",
        help="themes.csv の読み込み先",
    ),
    posts_path: Path = typer.Option(
        DEFAULT_POSTS_PATH,
        "--posts-path",
        help="posts.csv の追記先",
    ),
    metrics_path: Path = typer.Option(
        DEFAULT_METRICS_PATH,
        "--metrics-path",
        help="metrics.csv の確認先",
    ),
    output_dir: Path = typer.Option(
        DEFAULT_POSTS_OUTPUT_DIR,
        "--output-dir",
        help="Markdown投稿案の保存先ディレクトリ",
    ),
) -> None:
    """Quiet Workflow向けのX投稿案と画像生成プロンプトを作成します。"""
    ensure_quiet_workflow_csvs(
        themes_path=themes_path,
        posts_path=posts_path,
        metrics_path=metrics_path,
    )
    themes = load_themes(themes_path)
    theme = find_theme(themes, theme_id)
    if theme is None:
        console.print(f"[yellow]テーマIDが見つかりません: {theme_id}[/yellow]")
        return

    existing_posts = load_posts(posts_path)
    drafts = generate_quiet_workflow_posts(
        theme,
        count=count,
        starting_number=next_post_number(existing_posts),
    )
    warnings = validate_quiet_workflow_posts(drafts)
    if warnings:
        for warning in warnings:
            console.print(f"[yellow]{warning}[/yellow]")
        raise typer.Exit(code=1)

    append_posts(drafts, posts_path)
    markdown_path = write_posts_markdown(drafts, output_dir)
    console.print(f"[green]Quiet Workflow投稿案を保存しました: {markdown_path}[/green]")
    console.print(f"[green]posts.csv に追記しました: {posts_path}[/green]")
    console.print("[yellow]自動投稿はしません。公開前に文脈、事実関係、画像意図を確認してください。[/yellow]")


@app.command("generate-content-reviews")
def generate_content_reviews_command(
    offer_id: str | None = typer.Option(None, "--offer-id", help="特定の案件IDだけ生成"),
    with_scores: bool = typer.Option(False, "--with-scores", help="スコアリング結果を反映"),
    template: str = typer.Option(
        "comparison", "--template", help=f"生成テンプレート: {', '.join(CONTENT_TEMPLATES)}"
    ),
    status: str = typer.Option(
        "draft", "--status", help=f"初期レビュー状態: {', '.join(REVIEW_STATUSES)}"
    ),
    comment: str = typer.Option("", "--comment", help="レビューコメントの初期値"),
    output_format: str = typer.Option("csv", "--format", help="出力形式: csv, markdown"),
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="レビュー一覧の保存先。未指定時は既定パスに保存"
    ),
) -> None:
    """生成物レビュー用の一覧を作成します。"""
    template = parse_content_template(template)
    status = parse_review_status(status)
    output_format = parse_review_output_format(output_format)
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    if offer_id and not offers:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return

    score_explanations = explain_scores(offers) if with_scores else None
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
    reviews = build_content_reviews(
        x_posts,
        note_articles,
        status=status,
        reviewer_comment=comment,
    )
    render_content_reviews(reviews)

    if output_format == "markdown":
        target_path = output_path or DEFAULT_CONTENT_REVIEWS_MARKDOWN_PATH
        saved_path = write_content_reviews_markdown(reviews, target_path)
    else:
        target_path = output_path or DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH
        saved_path = write_content_reviews_csv(reviews, target_path)
    console.print(f"[green]生成物レビュー一覧を保存しました: {saved_path}[/green]")


@app.command("update-content-review")
def update_content_review_command(
    review_id: str = typer.Argument(..., help="更新するレビューID。例: x_post:OFF-0001"),
    status: str = typer.Option(..., "--status", help=f"レビュー状態: {', '.join(REVIEW_STATUSES)}"),
    comment: str | None = typer.Option(
        None,
        "--comment",
        help="レビューコメント。未指定時は既存コメントを保持",
    ),
    input_path: Path = typer.Option(
        DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
        "--input-path",
        help="更新対象のレビューCSV",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="保存先CSV。未指定時は入力CSVを上書き",
    ),
) -> None:
    """生成物レビューCSVの状態とコメントを更新します。"""
    if not input_path.exists():
        raise typer.BadParameter(f"レビューCSVが見つかりません: {input_path}")
    status = parse_review_status(status)
    result = update_content_review_csv(
        input_path=input_path,
        review_id=review_id,
        status=status,
        reviewer_comment=comment,
        output_path=output_path,
    )
    if not result.updated:
        console.print(f"[yellow]レビューIDが見つかりません: {review_id}[/yellow]")
        return
    assert result.updated_review is not None
    render_content_reviews([result.updated_review])
    console.print(f"[green]レビューを更新しました: {output_path or input_path}[/green]")


@app.command("list-approved-content")
def list_approved_content_command(
    input_path: Path = typer.Option(
        DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
        "--input-path",
        help="読み込むレビューCSV",
    ),
    output_format: str = typer.Option("markdown", "--format", help="出力形式: csv, markdown"),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="公開候補リストの保存先。未指定時は既定パスに保存",
    ),
) -> None:
    """approved の生成物だけを公開候補リストとして出力します。"""
    if not input_path.exists():
        raise typer.BadParameter(f"レビューCSVが見つかりません: {input_path}")
    output_format = parse_review_output_format(output_format)
    reviews = load_content_reviews_csv(input_path)
    approved_reviews = approved_content_reviews(reviews)
    render_content_reviews(approved_reviews)

    if output_format == "markdown":
        target_path = output_path or DEFAULT_APPROVED_CONTENT_MARKDOWN_PATH
        saved_path = write_approved_content_markdown(reviews, target_path)
    else:
        target_path = output_path or DEFAULT_APPROVED_CONTENT_OUTPUT_PATH
        saved_path = write_approved_content_csv(reviews, target_path)
    console.print(f"[green]公開候補リストを保存しました: {saved_path}[/green]")


@app.command("suggest-content-revisions")
def suggest_content_revisions_command(
    input_path: Path = typer.Option(
        DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
        "--input-path",
        help="読み込むレビューCSV",
    ),
    output_format: str = typer.Option("markdown", "--format", help="出力形式: csv, markdown"),
    output_path: Path | None = typer.Option(
        None,
        "--output-path",
        help="修正提案リストの保存先。未指定時は既定パスに保存",
    ),
) -> None:
    """needs_revision の生成物に修正提案を付けて出力します。"""
    if not input_path.exists():
        raise typer.BadParameter(f"レビューCSVが見つかりません: {input_path}")
    output_format = parse_review_output_format(output_format)
    reviews = load_content_reviews_csv(input_path)
    suggestions = build_revision_suggestions(reviews)
    if suggestions:
        revision_reviews = [review for review in reviews if review.status == "needs_revision"]
        render_content_reviews(revision_reviews)
    else:
        console.print("[green]修正対象の生成物はありません。[/green]")

    if output_format == "markdown":
        target_path = output_path or DEFAULT_REVISION_SUGGESTIONS_MARKDOWN_PATH
        saved_path = write_revision_suggestions_markdown(suggestions, target_path)
    else:
        target_path = output_path or DEFAULT_REVISION_SUGGESTIONS_OUTPUT_PATH
        saved_path = write_revision_suggestions_csv(suggestions, target_path)
    console.print(f"[green]修正提案リストを保存しました: {saved_path}[/green]")


@app.command("rewrite-content-drafts")
def rewrite_content_drafts_command(
    input_path: Path = typer.Option(
        DEFAULT_CONTENT_REVIEWS_OUTPUT_PATH,
        "--input-path",
        help="読み込むレビューCSV",
    ),
    output_path: Path = typer.Option(
        DEFAULT_REWRITE_CONTENT_DRAFTS_MARKDOWN_PATH,
        "--output-path",
        help="安全寄りリライト案Markdownの保存先",
    ),
) -> None:
    """needs_revision の生成物に安全寄りのリライト案を作成します。"""
    if not input_path.exists():
        raise typer.BadParameter(f"レビューCSVが見つかりません: {input_path}")
    reviews = load_content_reviews_csv(input_path)
    drafts = build_content_rewrite_drafts(reviews)
    if drafts:
        revision_reviews = [review for review in reviews if review.status == "needs_revision"]
        render_content_reviews(revision_reviews)
    else:
        console.print("[green]リライト対象の生成物はありません。[/green]")

    saved_path = write_content_rewrite_drafts_markdown(drafts, output_path)
    console.print(f"[green]安全寄りリライト案を保存しました: {saved_path}[/green]")
    console.print("[yellow]この出力は自動公開されません。公開前に公式条件を確認してください。[/yellow]")


def read_check_target(text: str | None, file_path: Path | None) -> str:
    if text and file_path:
        raise typer.BadParameter("テキスト引数と --file は同時に指定できません。")
    if file_path:
        if not file_path.exists():
            raise typer.BadParameter(f"ファイルが見つかりません: {file_path}")
        return file_path.read_text(encoding="utf-8")
    if text:
        return text
    raise typer.BadParameter("チェック対象テキスト、または --file を指定してください。")


def parse_content_template(value: str) -> str:
    try:
        return normalize_content_template(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def parse_review_status(value: str) -> str:
    try:
        return normalize_review_status(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def parse_review_output_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"csv", "markdown"}:
        raise typer.BadParameter("出力形式は csv または markdown を指定してください。")
    return normalized


def parse_min_reward(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value.replace(",", ""))
    except InvalidOperation as exc:
        raise typer.BadParameter("数値を入力してください。例: 30000") from exc
    if parsed < 0:
        raise typer.BadParameter("0以上の数値を入力してください。")
    return parsed
