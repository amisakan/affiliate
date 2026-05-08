# affiliate-os

affiliate-os は、信頼型アフィリエイト運用OSのMVPです。

案件情報をCSVで管理し、スコアリング、コンプライアンスチェック、X投稿生成、note記事生成、workflow automation へ拡張していくためのAI協調開発環境を整えています。

このプロジェクトでは、煽り系コピー、虚偽実績、誇大表現、不安商法を避け、読者の意思決定支援を目的にします。

## セットアップ

Python 3.11+ と uv を使います。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11
uv sync --all-groups
```

MacBook Air M1 では、初期セットアップ用スクリプトも使えます。

```bash
bash scripts/setup.sh
```

## uv の使い方

依存関係の同期:

```bash
uv sync --all-groups
```

CLI の実行:

```bash
uv run python -m affiliate_os
```

pytest:

```bash
uv run pytest
```

ruff:

```bash
uv run ruff check .
uv run ruff format .
```

## make コマンド

```bash
make test
make lint
make format
make run
make tree
```

- `make test`: pytest を実行
- `make lint`: ruff check を実行
- `make format`: ruff format と自動修正を実行
- `make run`: CLI を起動
- `make tree`: 主要ディレクトリ構成を表示

## GitHub連携

初回はGitHubで空のリポジトリを作成してから、ローカルで以下を実行します。

```bash
git init
git checkout -b main
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

すでにローカルリポジトリがある場合は、以下の流れで作業します。

```bash
git checkout main
git pull --ff-only
git checkout -b feature/<short-topic>
```

変更後は、push前に確認します。

```bash
make lint
make test
git status --short
git diff --cached
```

問題がなければcommitしてpushします。

```bash
git add .
git commit -m "Describe the change"
git push -u origin feature/<short-topic>
```

GitHub上でPull Requestを作成し、PRテンプレートの各項目を埋めてください。CIでは `make lint` と `make test` が実行されます。

## push前の機密情報チェック

以下はGit管理しません。

- `.env`
- `.env.*`
- `secrets/`
- `secrets.*`
- `outputs/generated/`
- `.venv/`

APIキー、個人情報、未公開のASP管理画面情報、認証情報を含むログはコミットしないでください。push前に差分を確認します。

```bash
git diff
git diff --cached
```

## CLI

案件を追加:

```bash
uv run python -m affiliate_os add-offer
```

案件一覧:

```bash
uv run python -m affiliate_os list-offers
```

絞り込み:

```bash
uv run python -m affiliate_os list-offers --genre "医療者AI"
uv run python -m affiliate_os list-offers --asp "A8"
uv run python -m affiliate_os list-offers --min-reward 30000
```

スコアリング:

```bash
uv run python -m affiliate_os score-offers
```

コンプライアンスチェック:

```bash
uv run python -m affiliate_os check-text "誰でも簡単に月100万円確定です"
```

ファイルをチェック:

```bash
uv run python -m affiliate_os check-text --file docs/sample.md
```

登録済み案件CSVをまとめてチェック:

```bash
uv run python -m affiliate_os check-offers
```

別のCSVをチェック:

```bash
uv run python -m affiliate_os check-offers --data-path data/offers.csv
```

X投稿案を生成:

```bash
uv run python -m affiliate_os generate-x-posts
```

スコアリング結果を反映:

```bash
uv run python -m affiliate_os generate-x-posts --with-scores
```

特定の案件だけ生成:

```bash
uv run python -m affiliate_os generate-x-posts --offer-id OFF-0001
```

Markdownに保存:

```bash
uv run python -m affiliate_os generate-x-posts --output-path outputs/generated/x_posts.md
```

note記事下書きを生成:

```bash
uv run python -m affiliate_os generate-note-articles
```

スコアリング結果を反映:

```bash
uv run python -m affiliate_os generate-note-articles --with-scores
```

特定の案件だけ生成:

```bash
uv run python -m affiliate_os generate-note-articles --offer-id OFF-0001
```

Markdownに保存:

```bash
uv run python -m affiliate_os generate-note-articles --output-path outputs/generated/note_articles.md
```

X投稿案、note記事下書き、コンプライアンス概要をまとめて生成:

```bash
uv run python -m affiliate_os generate-content-pack
```

スコアリング結果もまとめて反映:

```bash
uv run python -m affiliate_os generate-content-pack --with-scores
```

特定の案件だけまとめて生成:

```bash
uv run python -m affiliate_os generate-content-pack --offer-id OFF-0001
```

保存先を指定:

```bash
uv run python -m affiliate_os generate-content-pack --output-dir outputs/generated/content_pack
```

検出対象の例:

- 禁止表現: 「誰でも簡単」「必ず稼げる」「月100万円確定」
- 誇大表現: 成果、安全性、収益を強く断定する表現
- 不安訴求: 読者の焦りや恐怖を過度に刺激する表現
- 医療、転職、金融領域での断定表現

画像から案件を取り込む場合は OpenAI API キーを設定します。

```bash
export OPENAI_API_KEY="your-api-key"
uv run python -m affiliate_os import-offer --from-image "./screenshot.png"
```

## ディレクトリ構成

```text
affiliate_os/            # アプリケーションコード
data/                    # 入力データ、CSV
outputs/                 # 分析結果、生成物
outputs/generated/       # Git管理しない生成物
prompts/                 # AIエージェント用プロンプト
docs/                    # 設計メモ、仕様、運用方針
experiments/             # 実験コード、検証メモ
tests/                   # pytest
scripts/                 # セットアップや運用スクリプト
.github/workflows/       # GitHub Actions
```

## AIエージェント役割分担

- Codex: 実装、CI、テスト、リポジトリ整備、設計メモ作成
- Claude Code: ローカル修正、リファクタ、小規模実装、テスト補強
- Claude Cowork: 仕様整理、レビュー、タスク分解、観点出し
- ChatGPT: 企画、プロンプト設計、ドキュメント作成、コンテンツ方針検討

共通ルールは `AGENTS.md`、Claude Code 向けの詳細は `CLAUDE.md` を参照してください。

## コンプライアンス方針

以下の表現は推奨しません。

- 「誰でも簡単」
- 「必ず稼げる」
- 「月100万円確定」

医療、転職、金融領域では断定表現を避け、条件、リスク、向き不向き、専門家確認の余地を明示します。
# affiliate
