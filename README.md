# YouTube Research Toolkit

YouTubeの競合チャンネル分析・追跡、およびAIを用いた差別化（ポジショニング）要素の抽出を行うためのフルスタックWebアプリケーションです。

## 概要

新しくYouTubeチャンネルを立ち上げる際、あるいは既存チャンネルを成長させる際、競合チャンネル（「vidIQ」や「kamui tracker」などを想定）が「どのように成長してきたか」を追跡・分析します。
また、収集したデータを元に、AI（Gemini API）を活用して「競合がまだカバーしていないテーマ」や「独自のポジショニング」を分析・導き出します。

## 技術スタック

* **フロントエンド**: Next.js 14 (App Router) + TypeScript + Recharts (データ可視化) + Vanilla CSS (CSS Modules)
* **バックエンド**: FastAPI (Python 3.11+) + SQLAlchemy + SQLite (ローカル軽量データベース)
* **AI・外部API**: YouTube Data API v3, Gemini API
* **自動収集バッチ**: GitHub Actions (日次自動フェッチ) + CLI python バッチ

---

## プロジェクト構成

```text
youtube-research-toolkit/
├── .github/                  # GitHub Actions ワークフロー定義
│   └── workflows/
│       └── fetch_stats.yml   # 日次統計データ自動収集バッチ定義
├── backend/                  # FastAPI バックエンド
│   ├── app/                  # アプリケーションロジック
│   │   ├── models/           # DBモデル (channel, video, channel_stats_history)
│   │   ├── schemas/          # Pydantic スキーマ
│   │   ├── scripts/          # CLI実行スクリプト (fetch_stats.py)
│   │   └── services/         # YouTube API 連携等の共通サービス
│   ├── data/                 # 蓄積データ
│   │   └── history/          # GitHub Actionsから自動同期される時系列JSON
│   ├── main.py               # API エントリーポイント (起動時に自動データ同期実行)
│   └── requirements.txt      # 依存ライブラリ一覧
├── frontend/                 # Next.js フロントエンド
│   ├── src/                  # ソースコード
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

---

## 時系列データの自動収集と同期 (GitHub Actions)

PCが起動していなくても、毎日自動的に競合チャンネルの数値（登録者、再生数、動画数）を収集・蓄積する仕組みを搭載しています。

### 1. GitHub Actions の設定方法
本リポジトリを GitHub にアップロード（プッシュ）した後、リポジトリの **Settings ➔ Secrets and variables ➔ Actions** にて以下の2つの **Repository secrets** を追加します。

* **`YOUTUBE_API_KEY`**: 取得した YouTube Data API キー
* **`MONITOR_CHANNELS`**: 監視したい YouTube のチャンネルID（`UC` から始まる24文字）を、カンマ（`,`）で区切った文字列
  * *設定例*: `UCD-R2Y7wTvYMWIcBmob6a2A,UC-OzfxW-OXMuuNggpxNuTLw`

### 2. データの自動マージ（同期）
GitHub Actions は毎日日本時間の午前3時に自動で起動し、取得した数値を軽量なテキストの JSON ファイルとして `backend/data/history/` ディレクトリにプッシュします。

利用者がローカルPCで **FastAPI バックエンドを起動する（または再起動する）と、起動時イベントにより自動的に JSON データが SQLite 内の履歴テーブル（`channel_stats_history`）へ一括マージ（インポート）されます**。これにより、GitのバイナリDBファイルの衝突（競合）を一切起こすことなく、常に最新の時系列成長トレンドを同期することができます。
