from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import click
import typer

from affiliate_os.models import OfferDraft

DEFAULT_MODEL = "gpt-4o-mini"


def nullable_schema(schema_type: str) -> dict[str, Any]:
    return {"anyOf": [{"type": schema_type}, {"type": "null"}]}


OFFER_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "asp": {"type": "string"},
        "genre": {"type": "string"},
        "offer_name": {"type": "string"},
        "reward": nullable_schema("number"),
        "price": nullable_schema("number"),
        "commission_rate": {"type": "string"},
        "approval_rate": {"type": "string"},
        "cookie_days": nullable_schema("integer"),
        "target": {"type": "string"},
        "problem": {"type": "string"},
        "benefit": {"type": "string"},
        "risk_level": {"type": "string"},
        "brand_fit": {"type": "string"},
        "lp_url": {"type": "string"},
        "memo": {"type": "string"},
    },
    "required": [
        "asp",
        "genre",
        "offer_name",
        "reward",
        "price",
        "commission_rate",
        "approval_rate",
        "cookie_days",
        "target",
        "problem",
        "benefit",
        "risk_level",
        "brand_fit",
        "lp_url",
        "memo",
    ],
}


def extract_offer_from_image(image_path: Path, model: str | None = None) -> OfferDraft:
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            AuthenticationError,
            OpenAI,
            RateLimitError,
        )
    except ImportError as exc:
        raise typer.BadParameter(
            "openai パッケージが必要です。pip install -r requirements.txt を実行してください。"
        ) from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise typer.BadParameter(
            "OPENAI_API_KEY が未設定です。環境変数にAPIキーを設定してください。"
        )

    client = OpenAI()
    try:
        response = client.responses.create(
            model=model or os.getenv("AFFILIATE_OS_OPENAI_MODEL", DEFAULT_MODEL),
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": build_extraction_instructions(),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "このアフィリエイト案件スクリーンショットからCSV登録用のJSONを抽出してください。",
                        },
                        {
                            "type": "input_image",
                            "image_url": image_to_data_url(image_path),
                            "detail": "high",
                        },
                    ],
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "affiliate_offer_draft",
                    "schema": OFFER_DRAFT_SCHEMA,
                    "strict": True,
                }
            },
        )
    except AuthenticationError as exc:
        raise click.ClickException(
            "OpenAI APIキーを認証できませんでした。OPENAI_API_KEY の値を確認してください。"
        ) from exc
    except RateLimitError as exc:
        raise click.ClickException(
            "OpenAI APIの利用上限またはクォータに達しています。OpenAI PlatformのBilling/Usageを確認するか、"
            "別のプロジェクト/APIキーを設定して再実行してください。"
        ) from exc
    except APIConnectionError as exc:
        raise click.ClickException(
            "OpenAI APIに接続できませんでした。ネットワーク接続を確認して再実行してください。"
        ) from exc
    except APIStatusError as exc:
        raise click.ClickException(
            f"OpenAI APIエラーが発生しました: HTTP {exc.status_code}"
        ) from exc
    return OfferDraft(**json.loads(response.output_text))


def image_to_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise typer.BadParameter(f"画像ファイルが見つかりません: {image_path}")
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_extraction_instructions() -> str:
    return """
あなたは信頼型アフィリエイト運用OSのデータ入力アシスタントです。
スクリーンショット内の事実だけを抽出し、指定JSONスキーマで返してください。

方針:
- 煽り系、虚偽実績、誇大表現を補完しない。
- 画像にない情報は推測せず、文字列は ""、数値は null にする。
- asp は A8.net なら "A8" のように短く正規化する。
- reward は成果報酬や報酬単価の金額を数値で入れる。
- cookie_days は再訪問期間やCookie期間の日数を整数で入れる。
- approval_rate は確定率や承認率が表示されていれば入れる。"-" は "" にする。
- memo にはプログラムID、広告主、成果条件、否認条件、EPC、成果確定目安、注意アイコンなどを簡潔にまとめる。
- risk_level は医療・転職・金融、本人NG、リスティング制限、否認条件の多さを踏まえ、低/中/高/要確認のいずれかを入れる。
- brand_fit は画面だけでは判断できない場合 "要確認" にする。
""".strip()
