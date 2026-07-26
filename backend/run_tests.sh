#!/bin/bash
# テスト環境フラグをセットして pytest を実行するヘルパースクリプト

# このスクリプトがあるディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境が有効化されていない場合は有効化
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Warning: Python virtual environment (venv) not found. Running with global python."
    fi
fi

# テスト実行
echo "Running pytest with coverage..."
pytest --cov=app tests/ "$@"
