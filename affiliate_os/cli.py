from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import typer

from affiliate_os.compliance import check_compliance, check_offers_compliance
from affiliate_os.content import (
    DEFAULT_CONTENT_PACK_DIR,
    filter_offers_by_id,
    generate_content_pack,
    generate_note_articles_for_offers,
    generate_x_posts_for_offers,
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
from affiliate_os.scoring import DEFAULT_SCORES_PATH, score_offers, write_scores_csv
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
    render_note_article_drafts,
    render_offer_detail,
    render_offer_draft,
    render_offer_table,
    render_offers_compliance_reports,
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
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="Markdown保存先。未指定時は保存しません"
    ),
) -> None:
    """登録済み案件から信頼型のX投稿案を生成します。"""
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    drafts = generate_x_posts_for_offers(offers)
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
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_path: Path | None = typer.Option(
        None, "--output-path", help="Markdown保存先。未指定時は保存しません"
    ),
) -> None:
    """登録済み案件からnote記事下書きを生成します。"""
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    drafts = generate_note_articles_for_offers(offers)
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
    data_path: Path = typer.Option(
        DEFAULT_DATA_PATH, "--data-path", help="offers.csv の読み込み先"
    ),
    output_dir: Path = typer.Option(
        DEFAULT_CONTENT_PACK_DIR, "--output-dir", help="生成物の保存先ディレクトリ"
    ),
) -> None:
    """X投稿案、note記事下書き、コンプライアンス概要をまとめて生成します。"""
    offers = filter_offers_by_id(load_offers(data_path), offer_id)
    if offer_id and not offers:
        console.print(f"[yellow]案件IDが見つかりません: {offer_id}[/yellow]")
        return
    pack = generate_content_pack(offers, output_dir)
    render_content_pack(pack)


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
