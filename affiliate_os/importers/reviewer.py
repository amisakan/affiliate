from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from affiliate_os.models import Offer, OfferDraft
from affiliate_os.storage import next_offer_id
from affiliate_os.utils import ask_decimal, ask_required

REQUIRED_FIELD_PROMPTS = {
    "asp": "ASP名",
    "genre": "ジャンル",
    "offer_name": "案件名",
    "reward": "報酬単価",
}


def complete_required_fields(draft: OfferDraft) -> OfferDraft:
    data = draft.model_dump()
    for field_name in draft.missing_required_fields():
        prompt = REQUIRED_FIELD_PROMPTS[field_name]
        if field_name == "reward":
            data[field_name] = ask_decimal(prompt, required=True)
        else:
            data[field_name] = ask_required(prompt)
    return OfferDraft(**data)


def build_offer_from_draft(
    draft: OfferDraft, data_path: Path, timestamp: datetime | None = None
) -> Offer:
    timestamp = timestamp or datetime.now()
    return draft.to_offer(next_offer_id(data_path), timestamp)


def confirm_save(yes: bool) -> bool:
    if yes:
        return True
    return typer.confirm("この内容で保存しますか？", default=True)
