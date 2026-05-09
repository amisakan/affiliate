from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_THEMES_PATH = Path("data") / "themes.csv"
DEFAULT_POSTS_PATH = Path("data") / "posts.csv"
DEFAULT_METRICS_PATH = Path("data") / "metrics.csv"
DEFAULT_POSTS_OUTPUT_DIR = Path("outputs") / "posts"

THEME_COLUMNS = [
    "theme_id",
    "title",
    "focus",
    "keywords",
    "audience",
    "memo",
]
POST_COLUMNS = [
    "post_id",
    "theme_id",
    "post_text",
    "image_concept",
    "image_prompt",
    "risk_notes",
    "created_at",
]
METRIC_COLUMNS = [
    "post_id",
    "theme_id",
    "posted_at",
    "impressions",
    "engagements",
    "saves",
    "notes",
]

QUIET_WORKFLOW_FORBIDDEN_PHRASES = [
    "誰でも簡単",
    "必ず稼げる",
    "月100万円確定",
    "稼げる",
    "絶対",
    "確実",
]


class QuietWorkflowTheme(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    theme_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    focus: str = "AI, Workflow, Research, Deep Work, 情報整理"
    keywords: str = ""
    audience: str = "静かに仕事の質を整えたい人"
    memo: str = ""

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> QuietWorkflowTheme:
        return cls(**row)

    def to_csv_row(self) -> dict[str, str]:
        return {
            "theme_id": self.theme_id,
            "title": self.title,
            "focus": self.focus,
            "keywords": self.keywords,
            "audience": self.audience,
            "memo": self.memo,
        }


class QuietWorkflowPostDraft(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    post_id: str
    theme_id: str
    post_text: str
    image_concept: str
    image_prompt: str
    risk_notes: str
    created_at: datetime

    def to_csv_row(self) -> dict[str, str]:
        return {
            "post_id": self.post_id,
            "theme_id": self.theme_id,
            "post_text": self.post_text,
            "image_concept": self.image_concept,
            "image_prompt": self.image_prompt,
            "risk_notes": self.risk_notes,
            "created_at": self.created_at.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> QuietWorkflowPostDraft:
        values: dict[str, Any] = dict(row)
        values["created_at"] = parse_datetime(row.get("created_at", ""))
        return cls(**values)


class QuietWorkflowMetric(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    post_id: str
    theme_id: str
    posted_at: datetime
    impressions: int = Field(ge=0)
    engagements: int = Field(ge=0)
    saves: int = Field(ge=0)
    notes: str = ""

    @property
    def engagement_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.engagements / self.impressions

    @property
    def save_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.saves / self.impressions

    def to_csv_row(self) -> dict[str, str]:
        return {
            "post_id": self.post_id,
            "theme_id": self.theme_id,
            "posted_at": self.posted_at.isoformat(timespec="seconds"),
            "impressions": str(self.impressions),
            "engagements": str(self.engagements),
            "saves": str(self.saves),
            "notes": self.notes,
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> QuietWorkflowMetric:
        values: dict[str, Any] = dict(row)
        values["posted_at"] = parse_datetime(row.get("posted_at", ""))
        values["impressions"] = parse_int(row.get("impressions", "0"))
        values["engagements"] = parse_int(row.get("engagements", "0"))
        values["saves"] = parse_int(row.get("saves", "0"))
        return cls(**values)


def ensure_csv(path: Path, columns: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
    return path


def ensure_quiet_workflow_csvs(
    themes_path: Path = DEFAULT_THEMES_PATH,
    posts_path: Path = DEFAULT_POSTS_PATH,
    metrics_path: Path = DEFAULT_METRICS_PATH,
) -> None:
    ensure_csv(themes_path, THEME_COLUMNS)
    ensure_csv(posts_path, POST_COLUMNS)
    ensure_csv(metrics_path, METRIC_COLUMNS)


def load_themes(path: Path = DEFAULT_THEMES_PATH) -> list[QuietWorkflowTheme]:
    ensure_csv(path, THEME_COLUMNS)
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [QuietWorkflowTheme.from_csv_row(row) for row in reader]


def find_theme(themes: list[QuietWorkflowTheme], theme_id: str) -> QuietWorkflowTheme | None:
    normalized = theme_id.strip()
    for theme in themes:
        if theme.theme_id == normalized:
            return theme
    return None


def filter_themes(
    themes: list[QuietWorkflowTheme],
    keyword: str | None = None,
) -> list[QuietWorkflowTheme]:
    if keyword is None:
        return themes
    normalized = keyword.strip().lower()
    if not normalized:
        return themes
    return [
        theme
        for theme in themes
        if normalized in quiet_search_text(
            [theme.theme_id, theme.title, theme.focus, theme.keywords, theme.audience, theme.memo]
        )
    ]


def load_posts(path: Path = DEFAULT_POSTS_PATH) -> list[QuietWorkflowPostDraft]:
    ensure_csv(path, POST_COLUMNS)
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [QuietWorkflowPostDraft.from_csv_row(row) for row in reader]


def append_posts(posts: list[QuietWorkflowPostDraft], path: Path = DEFAULT_POSTS_PATH) -> None:
    ensure_csv(path, POST_COLUMNS)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=POST_COLUMNS)
        for post in posts:
            writer.writerow(post.to_csv_row())


def load_metrics(path: Path = DEFAULT_METRICS_PATH) -> list[QuietWorkflowMetric]:
    ensure_csv(path, METRIC_COLUMNS)
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [QuietWorkflowMetric.from_csv_row(row) for row in reader]


def append_metric(metric: QuietWorkflowMetric, path: Path = DEFAULT_METRICS_PATH) -> None:
    ensure_csv(path, METRIC_COLUMNS)
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=METRIC_COLUMNS)
        writer.writerow(metric.to_csv_row())


def find_post(
    posts: list[QuietWorkflowPostDraft], post_id: str
) -> QuietWorkflowPostDraft | None:
    normalized = post_id.strip()
    for post in posts:
        if post.post_id == normalized:
            return post
    return None


def filter_posts(
    posts: list[QuietWorkflowPostDraft],
    theme_id: str | None = None,
    limit: int | None = None,
) -> list[QuietWorkflowPostDraft]:
    filtered = posts
    if theme_id:
        normalized_theme_id = theme_id.strip()
        filtered = [post for post in filtered if post.theme_id == normalized_theme_id]
    filtered = sorted(filtered, key=lambda post: (post.created_at, post.post_id), reverse=True)
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def next_post_number(posts: list[QuietWorkflowPostDraft]) -> int:
    max_number = 0
    for post in posts:
        try:
            number = int(post.post_id.split("-")[-1])
        except ValueError:
            continue
        max_number = max(max_number, number)
    return max_number + 1


def generate_quiet_workflow_posts(
    theme: QuietWorkflowTheme,
    count: int,
    starting_number: int = 1,
    created_at: datetime | None = None,
) -> list[QuietWorkflowPostDraft]:
    if count < 1:
        raise ValueError("count must be 1 or greater")
    created_at = created_at or datetime.now()
    drafts = []
    for index in range(count):
        variant_index = index % len(POST_TEXT_TEMPLATES)
        post_text = build_post_text(theme, variant_index)
        drafts.append(
            QuietWorkflowPostDraft(
                post_id=f"QW-{starting_number + index:04d}",
                theme_id=theme.theme_id,
                post_text=sanitize_quiet_workflow_text(post_text),
                image_concept=build_image_concept(theme, variant_index),
                image_prompt=build_image_prompt(theme, variant_index),
                risk_notes=build_risk_notes(theme),
                created_at=created_at,
            )
        )
    return drafts


def build_post_metric(
    post: QuietWorkflowPostDraft,
    impressions: int,
    engagements: int,
    saves: int,
    notes: str = "",
    posted_at: datetime | None = None,
) -> QuietWorkflowMetric:
    return QuietWorkflowMetric(
        post_id=post.post_id,
        theme_id=post.theme_id,
        posted_at=posted_at or datetime.now(),
        impressions=impressions,
        engagements=engagements,
        saves=saves,
        notes=notes,
    )


POST_TEXT_TEMPLATES = [
    (
        "{title}。\n\n"
        "AIに任せる前に、問いを一行だけ静かに置く。\n"
        "Workflowは、その問いを急がず運ぶための器になる。"
    ),
    (
        "Researchは、情報を増やす作業ではなく、余白を取り戻す作業でもある。\n\n"
        "{title}を考える日は、集める前に、何を見ないかを決める。"
    ),
    (
        "Deep Workの入口は、大きな決意よりも小さな整頓に近い。\n\n"
        "{title}。\n"
        "今日扱う情報を減らすと、判断の輪郭が少し戻ってくる。"
    ),
    (
        "Workflowを整えるとは、急ぐためではなく、静かに戻れる場所をつくること。\n\n"
        "{title}は、そのための小さな設計メモになる。"
    ),
    (
        "AIは答えを急がせる道具ではなく、思考の置き場所にもできる。\n\n"
        "{title}。\n"
        "まずは素材、判断、次の一手を分けて眺める。"
    ),
]


def build_post_text(theme: QuietWorkflowTheme, variant_index: int) -> str:
    template = POST_TEXT_TEMPLATES[variant_index]
    keyword_note = build_keyword_note(theme)
    memo_note = f"\n\nメモ: {theme.memo}" if theme.memo else ""
    return template.format(title=theme.title) + keyword_note + memo_note


def build_keyword_note(theme: QuietWorkflowTheme) -> str:
    keywords = [keyword.strip() for keyword in theme.keywords.split("|") if keyword.strip()]
    if not keywords:
        return ""
    selected = " / ".join(keywords[:3])
    return f"\n\n軸: {selected}"


def build_image_concept(theme: QuietWorkflowTheme, variant_index: int) -> str:
    concepts = [
        "黒背景に深緑の細い線で、情報が静かに整理されていくミニマルなワークフロー図",
        "余白の広い黒いデスクに、深緑のノートと小さなResearchカードが置かれている",
        "暗い背景に、AI、Workflow、Deep Workを示す小さなノードが控えめに並ぶ抽象図",
        "黒背景の中央に小さな深緑のグリッド、周囲に余白を大きく残した情報整理の場面",
        "深緑の光だけで輪郭を描いた静かな作業環境、画面には最小限のタスクだけが見える",
    ]
    return f"{theme.title}: {concepts[variant_index]}"


def build_image_prompt(theme: QuietWorkflowTheme, variant_index: int) -> str:
    return (
        f"Minimal editorial image for Quiet Workflow, theme: {theme.title}. "
        "Black background, deep green accents, generous negative space, quiet intelligence, "
        "minimal workflow diagram, subtle AI and research motifs, no hype, no money imagery, "
        "no people shouting, refined typography-like composition, calm deep work atmosphere. "
        f"Focus keywords: {theme.focus}; {theme.keywords}."
    )


def build_risk_notes(theme: QuietWorkflowTheme) -> str:
    notes = [
        "煽らない",
        "収益や成果を約束しない",
        "AIで効率化を断定しすぎない",
        "静かな知性と余白を保つ",
    ]
    if theme.memo:
        notes.append("テーマメモを事実確認してから公開する")
    return " / ".join(notes)


def sanitize_quiet_workflow_text(text: str) -> str:
    sanitized = text
    replacements = {
        "誰でも簡単": "扱いやすく",
        "必ず稼げる": "判断材料を整理できる",
        "月100万円確定": "収益を約束しない",
        "稼げる": "判断材料を整理できる",
        "絶対": "必要に応じて",
        "確実": "着実",
    }
    for phrase, replacement in replacements.items():
        sanitized = sanitized.replace(phrase, replacement)
    return sanitized.strip()


def validate_quiet_workflow_posts(posts: list[QuietWorkflowPostDraft]) -> list[str]:
    warnings = []
    for post in posts:
        joined = "\n".join(
            [post.post_text, post.image_concept, post.image_prompt, post.risk_notes]
        )
        for phrase in QUIET_WORKFLOW_FORBIDDEN_PHRASES:
            if phrase in joined:
                warnings.append(f"{post.post_id}: 避けたい表現が含まれています: {phrase}")
    return warnings


def write_posts_markdown(
    posts: list[QuietWorkflowPostDraft],
    output_dir: Path = DEFAULT_POSTS_OUTPUT_DIR,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    theme_id = posts[0].theme_id if posts else "empty"
    post_range = f"{posts[0].post_id}_{posts[-1].post_id}" if posts else "none"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = output_dir / f"quiet_workflow_{theme_id}_{post_range}_{timestamp}.md"
    output_path.write_text(format_posts_markdown(posts), encoding="utf-8")
    return output_path


def format_posts_markdown(posts: list[QuietWorkflowPostDraft]) -> str:
    lines = ["# Quiet Workflow Post Drafts", ""]
    if not posts:
        lines.append("投稿案はありません。")
        return "\n".join(lines) + "\n"

    for post in posts:
        lines.extend(
            [
                f"## {post.post_id}",
                "",
                f"- theme_id: {post.theme_id}",
                f"- created_at: {post.created_at.isoformat(timespec='seconds')}",
                "",
                "### Post Text",
                "",
                "```text",
                post.post_text,
                "```",
                "",
                "### Image Concept",
                "",
                post.image_concept,
                "",
                "### Image Prompt",
                "",
                "```text",
                post.image_prompt,
                "```",
                "",
                "### Risk Notes",
                "",
                post.risk_notes,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def format_themes_index_markdown(themes: list[QuietWorkflowTheme]) -> str:
    lines = [
        "# Quiet Workflow Themes",
        "",
        "| Theme ID | Title | Focus | Audience |",
        "| --- | --- | --- | --- |",
    ]
    if not themes:
        lines.append("| - | no themes | - | - |")
        return "\n".join(lines) + "\n"

    for theme in themes:
        lines.append(
            "| "
            f"{theme.theme_id} | "
            f"{theme.title} | "
            f"{theme.focus or '-'} | "
            f"{theme.audience or '-'} |"
        )
    lines.extend(["", "## Notes", ""])
    for theme in themes:
        if theme.keywords or theme.memo:
            lines.extend(
                [
                    f"### {theme.theme_id}",
                    "",
                    f"- keywords: {theme.keywords or '-'}",
                    f"- memo: {theme.memo or '-'}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def format_posts_index_markdown(posts: list[QuietWorkflowPostDraft]) -> str:
    lines = [
        "# Quiet Workflow Posts",
        "",
        "| Post ID | Theme | Created At | Preview |",
        "| --- | --- | --- | --- |",
    ]
    if not posts:
        lines.append("| - | - | - | no posts |")
        return "\n".join(lines) + "\n"

    for post in posts:
        lines.append(
            "| "
            f"{post.post_id} | "
            f"{post.theme_id} | "
            f"{post.created_at.isoformat(timespec='seconds')} | "
            f"{content_preview(post.post_text, max_length=80)} |"
        )

    lines.extend(["", "## Details", ""])
    for post in posts:
        lines.extend(
            [
                f"### {post.post_id}",
                "",
                f"- theme_id: {post.theme_id}",
                f"- image_concept: {post.image_concept}",
                f"- risk_notes: {post.risk_notes}",
                "",
                "```text",
                post.post_text,
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_text_markdown(markdown: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def write_metrics_summary_markdown(
    metrics: list[QuietWorkflowMetric],
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(format_metrics_summary_markdown(metrics), encoding="utf-8")
    return output_path


def format_metrics_summary_markdown(metrics: list[QuietWorkflowMetric]) -> str:
    lines = [
        "# Quiet Workflow Metrics",
        "",
        "| Post ID | Theme | Impressions | Engagements | Saves | Engagement Rate | Save Rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    if not metrics:
        lines.append("| - | - | 0 | 0 | 0 | 0.0% | 0.0% |")
        return "\n".join(lines) + "\n"

    for metric in sorted(metrics, key=metric_sort_key, reverse=True):
        lines.append(
            "| "
            f"{metric.post_id} | "
            f"{metric.theme_id} | "
            f"{metric.impressions} | "
            f"{metric.engagements} | "
            f"{metric.saves} | "
            f"{format_rate(metric.engagement_rate)} | "
            f"{format_rate(metric.save_rate)} |"
        )

    noted_metrics = [metric for metric in metrics if metric.notes]
    if noted_metrics:
        lines.extend(["", "## Notes", ""])
        for metric in noted_metrics:
            lines.append(f"- {metric.post_id}: {metric.notes}")
    return "\n".join(lines).rstrip() + "\n"


def metric_sort_key(metric: QuietWorkflowMetric) -> tuple[float, float, int]:
    return (metric.save_rate, metric.engagement_rate, metric.impressions)


def format_rate(value: float) -> str:
    return f"{value * 100:.1f}%"


def content_preview(text: str, max_length: int = 80) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip() + "..."


def quiet_search_text(values: list[str]) -> str:
    return " ".join(value for value in values if value).lower()


def parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0)


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
