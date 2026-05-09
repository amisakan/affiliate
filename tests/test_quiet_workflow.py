from datetime import datetime

from affiliate_os.quiet_workflow import (
    METRIC_COLUMNS,
    POST_COLUMNS,
    THEME_COLUMNS,
    QuietWorkflowTheme,
    append_metric,
    append_posts,
    build_post_metric,
    ensure_quiet_workflow_csvs,
    filter_posts,
    filter_themes,
    find_theme,
    format_metrics_summary_markdown,
    format_post_detail_markdown,
    format_posts_index_markdown,
    format_posts_markdown,
    format_themes_index_markdown,
    generate_quiet_workflow_posts,
    load_metrics,
    load_posts,
    load_themes,
    next_post_number,
    sanitize_quiet_workflow_text,
    validate_quiet_workflow_posts,
    write_metrics_summary_markdown,
    write_posts_markdown,
)


def make_theme() -> QuietWorkflowTheme:
    return QuietWorkflowTheme(
        theme_id="001",
        title="静かなAIワークフローの作り方",
        focus="AI, Workflow, Research, Deep Work, 情報整理",
        keywords="AI|Workflow|Research|Deep Work|情報整理",
        audience="静かに仕事の質を整えたい人",
        memo="余白のある投稿にする",
    )


def test_ensure_quiet_workflow_csvs_creates_required_headers(tmp_path):
    themes_path = tmp_path / "data" / "themes.csv"
    posts_path = tmp_path / "data" / "posts.csv"
    metrics_path = tmp_path / "data" / "metrics.csv"

    ensure_quiet_workflow_csvs(themes_path, posts_path, metrics_path)

    assert themes_path.read_text(encoding="utf-8").strip() == ",".join(THEME_COLUMNS)
    assert posts_path.read_text(encoding="utf-8").strip() == ",".join(POST_COLUMNS)
    assert metrics_path.read_text(encoding="utf-8").strip() == ",".join(METRIC_COLUMNS)


def test_load_themes_and_find_theme(tmp_path):
    themes_path = tmp_path / "themes.csv"
    themes_path.write_text(
        ",".join(THEME_COLUMNS)
        + "\n"
        + "001,静かなAIワークフロー,AIと情報整理,AI|Workflow,研究者,余白を残す\n",
        encoding="utf-8",
    )

    themes = load_themes(themes_path)

    assert len(themes) == 1
    assert find_theme(themes, "001") == themes[0]
    assert find_theme(themes, "999") is None


def test_filter_themes_searches_title_keywords_and_memo():
    themes = [
        make_theme(),
        QuietWorkflowTheme(
            theme_id="002",
            title="Researchログ",
            focus="Research",
            keywords="reading|notes",
            audience="調査する人",
            memo="問いを残す",
        ),
    ]

    filtered = filter_themes(themes, keyword="reading")

    assert [theme.theme_id for theme in filtered] == ["002"]


def test_generate_quiet_workflow_posts_creates_required_fields():
    created_at = datetime(2026, 5, 9, 9, 0)
    posts = generate_quiet_workflow_posts(
        make_theme(),
        count=3,
        starting_number=7,
        created_at=created_at,
    )

    assert [post.post_id for post in posts] == ["QW-0007", "QW-0008", "QW-0009"]
    assert all(post.theme_id == "001" for post in posts)
    assert all(post.post_text for post in posts)
    assert all(post.image_concept for post in posts)
    assert all("Black background" in post.image_prompt for post in posts)
    assert all("収益や成果を約束しない" in post.risk_notes for post in posts)
    assert all(post.created_at == created_at for post in posts)
    assert validate_quiet_workflow_posts(posts) == []


def test_append_load_posts_and_next_post_number(tmp_path):
    posts_path = tmp_path / "posts.csv"
    posts = generate_quiet_workflow_posts(
        make_theme(),
        count=2,
        created_at=datetime(2026, 5, 9, 9, 0),
    )

    append_posts(posts, posts_path)
    loaded = load_posts(posts_path)

    assert [post.post_id for post in loaded] == ["QW-0001", "QW-0002"]
    assert next_post_number(loaded) == 3


def test_filter_posts_by_theme_and_limit_sorts_newest_first():
    first_theme_posts = generate_quiet_workflow_posts(
        make_theme(),
        count=2,
        starting_number=1,
        created_at=datetime(2026, 5, 9, 9, 0),
    )
    second_theme = QuietWorkflowTheme(theme_id="002", title="Researchログ")
    second_theme_posts = generate_quiet_workflow_posts(
        second_theme,
        count=1,
        starting_number=3,
        created_at=datetime(2026, 5, 10, 9, 0),
    )

    filtered = filter_posts(first_theme_posts + second_theme_posts, theme_id="001", limit=1)

    assert [post.post_id for post in filtered] == ["QW-0002"]


def test_build_append_load_metric_and_rates(tmp_path):
    metrics_path = tmp_path / "metrics.csv"
    post = generate_quiet_workflow_posts(
        make_theme(),
        count=1,
        created_at=datetime(2026, 5, 9, 9, 0),
    )[0]
    metric = build_post_metric(
        post,
        impressions=1000,
        engagements=45,
        saves=12,
        notes="保存率が高め",
        posted_at=datetime(2026, 5, 10, 9, 0),
    )

    append_metric(metric, metrics_path)
    loaded = load_metrics(metrics_path)

    assert loaded == [metric]
    assert loaded[0].engagement_rate == 0.045
    assert loaded[0].save_rate == 0.012


def test_write_metrics_summary_markdown_sorts_by_save_rate(tmp_path):
    posts = generate_quiet_workflow_posts(
        make_theme(),
        count=2,
        created_at=datetime(2026, 5, 9, 9, 0),
    )
    first = build_post_metric(
        posts[0],
        impressions=1000,
        engagements=50,
        saves=10,
        posted_at=datetime(2026, 5, 10, 9, 0),
    )
    second = build_post_metric(
        posts[1],
        impressions=100,
        engagements=8,
        saves=5,
        notes="静かな保存が多い",
        posted_at=datetime(2026, 5, 10, 10, 0),
    )
    output_path = tmp_path / "metrics_summary.md"

    saved_path = write_metrics_summary_markdown([first, second], output_path)
    text = output_path.read_text(encoding="utf-8")

    assert saved_path == output_path
    assert format_metrics_summary_markdown([first, second]) == text
    assert text.index("QW-0002") < text.index("QW-0001")
    assert "5.0%" in text
    assert "静かな保存が多い" in text


def test_write_posts_markdown(tmp_path):
    posts = generate_quiet_workflow_posts(
        make_theme(),
        count=1,
        created_at=datetime(2026, 5, 9, 9, 0),
    )

    saved_path = write_posts_markdown(posts, tmp_path)
    text = saved_path.read_text(encoding="utf-8")

    assert saved_path.parent == tmp_path
    assert format_posts_markdown(posts) == text
    assert "# Quiet Workflow Post Drafts" in text
    assert "### Image Prompt" in text
    assert "自動投稿" not in text


def test_format_themes_and_posts_index_markdown():
    theme = make_theme()
    posts = generate_quiet_workflow_posts(
        theme,
        count=1,
        created_at=datetime(2026, 5, 9, 9, 0),
    )

    themes_markdown = format_themes_index_markdown([theme])
    posts_markdown = format_posts_index_markdown(posts)

    assert "# Quiet Workflow Themes" in themes_markdown
    assert "静かなAIワークフローの作り方" in themes_markdown
    assert "# Quiet Workflow Posts" in posts_markdown
    assert "QW-0001" in posts_markdown
    assert "### QW-0001" in posts_markdown


def test_format_post_detail_markdown_includes_publish_check():
    post = generate_quiet_workflow_posts(
        make_theme(),
        count=1,
        created_at=datetime(2026, 5, 9, 9, 0),
    )[0]

    markdown = format_post_detail_markdown(post)

    assert "# Quiet Workflow Post: QW-0001" in markdown
    assert "## Post Text" in markdown
    assert "## Image Prompt" in markdown
    assert "## Publishing Check" in markdown
    assert "自動投稿しない" in markdown


def test_sanitize_quiet_workflow_text_removes_forbidden_phrases():
    text = "誰でも簡単に稼げる。絶対に月100万円確定。"

    sanitized = sanitize_quiet_workflow_text(text)

    assert "誰でも簡単" not in sanitized
    assert "稼げる" not in sanitized
    assert "絶対" not in sanitized
    assert "月100万円確定" not in sanitized
