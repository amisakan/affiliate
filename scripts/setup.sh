#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv が見つかりません。先に以下を実行してください:"
  echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

uv venv --python 3.11
uv sync --all-groups
uv run pytest

echo "affiliate-os の初期セットアップが完了しました。"
