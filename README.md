# YouTube Research Toolkit

YouTubeの競合チャンネル分析・追跡、およびAIを用いた差別化（ポジショニング）要素の抽出を行うためのフルスタックWebアプリケーションです。

## 概要

新しくYouTubeチャンネルを立ち上げる際、あるいは既存チャンネルを成長させる際、競合チャンネル（「vidIQ」や「kamui tracker」などを想定）が「どのように成長してきたか」を追跡・分析します。
また、収集したデータを元に、AI（Gemini API）を活用して「競合がまだカバーしていないテーマ」や「独自のポジショニング」を分析・導き出します。

## 技術スタック

* **フロントエンド**: Next.js 14 (App Router) + TypeScript + Recharts (データ可視化) + Vanilla CSS (CSS Modules)
* **バックエンド**: FastAPI (Python 3.11+) + SQLAlchemy + SQLite (ローカル軽量データベース)
* **AI・外部API**: YouTube Data API v3, Gemini API

---

## プロジェクト構成

```text
youtube-research-toolkit/
├── .agents/                  # Antigravity用のエージェント指示書
│   └── rules/
│       └── project_rules.md  # プロジェクトのコーディングルール
├── backend/                  # FastAPI バックエンド
│   ├── app/                  # アプリケーションロジック (今後実装)
│   ├── main.py               # API エントリーポイント
│   └── requirements.txt      # 依存ライブラリ一覧
├── frontend/                 # Next.js フロントエンド
│   ├── src/                  # ソースコード (今後実装)
│   ├── package.json          # 依存パッケージ一覧
│   ├── tsconfig.json         # TypeScript 設定
│   └── next.config.js        # Next.js 設定
└── README.md                 # 本ドキュメント
```

---

## セットアップ方法

### 必要な環境変数
プロジェクトの実行には、以下のAPIキーが必要です。
それぞれのディレクトリ、またはルート直下に `.env` ファイルを作成し、設定してください（※ `.gitignore` でGit管理からは除外されています）。

```env
# YouTube Data API キー
YOUTUBE_API_KEY=your_youtube_api_key_here

# Gemini API キー (AI分析用)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 1. バックエンド (FastAPI) の起動

`backend/` ディレクトリで以下の手順を実行します。

```bash
cd backend

# 仮想環境の作成 (初回のみ)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 依存パッケージのインストール
pip install -r requirements.txt

# 開発サーバーの起動
uvicorn main:app --reload
```

起動後、 [http://localhost:8000/docs](http://localhost:8000/docs) で API Swagger UI にアクセスできます。

### 2. フロントエンド (Next.js) の起動

`frontend/` ディレクトリで以下の手順を実行します。

```bash
cd frontend

# 依存パッケージのインストール
npm install

# 開発サーバーの起動
npm run dev
```

起動後、 [http://localhost:3000](http://localhost:3000) でダッシュボード画面にアクセスできます。
