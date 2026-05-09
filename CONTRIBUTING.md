# CONTRIBUTING.md

affiliate-os へのコントリビューション方針です。

## 基本方針

このプロジェクトは、信頼型アフィリエイト運用OSです。読者の意思決定支援を目的にし、煽り系コピー、虚偽実績、誇大表現、不安商法を避けます。

以下の表現を生成、推奨、テスト期待値として追加しないでください。

- 「誰でも簡単」
- 「必ず稼げる」
- 「月100万円確定」

医療、転職、金融領域では、効果、成功、収益、安全性を断定しないでください。

## 開発環境

```bash
uv venv --python 3.11
uv sync --all-groups
```

## ローカル確認

PR前に最低限以下を実行してください。

```bash
make lint
make test
```

整形が必要な場合:

```bash
make format
```

## ブランチとPR

- `main` へ直接pushせず、原則としてブランチを作成する
- 変更は小さく分ける
- 大きな変更は、先にIssueか `docs/` に計画を書く
- PR本文に変更内容、テスト結果、倫理・コンプライアンス確認、既知のリスクを書く

### GitHub ActionsでPRを作成する

GitHub連携ツールでPR作成権限が不足する場合は、`Create pull request` workflowを手動実行してください。

入力項目:

- `head_branch`: 変更をpushしたブランチ名
- `base_branch`: PRの向き先。通常は `main`
- `title`: PRタイトル
- `body`: PR本文
- `draft`: draft PRとして作るかどうか

このworkflowは `contents: read` と `pull-requests: write` だけを明示して、既存のCI権限とは分けています。

## 機密情報

以下はコミットしないでください。

- `.env`
- `.env.*`
- `secrets/`
- APIキー
- 個人情報
- 未公開のASP管理画面スクリーンショット
- 認証情報を含むログ

push前に以下を確認してください。

```bash
git status --short
git diff --cached
```
