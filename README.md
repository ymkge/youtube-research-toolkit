# YouTube Research Toolkit

YouTubeの競合チャンネル分析・追跡、およびAIを用いた差別化（ポジショニング）要素の抽出を行うためのフルスタックWebアプリケーションです。

---

## 概要

新しくYouTubeチャンネルを立ち上げる際、あるいは既存チャンネルを成長させる際、競合チャンネルが「どのように成長してきたか」を定量・定性的に追跡・分析します。
収集したデータを元に、AI（Gemini API）を活用して「競合がまだカバーしていないテーマ」や「独自のポジショニング」を分析・導き出すほか、ドメインナレッジ（RAG）を用いた高度なリスク分析と PDF / 画像レポート保存機能を提供します。

---

## ✨ 主な機能

### 📊 ダッシュボード (メイン画面)
* **🏆 登録者達成マイルストーン一覧機能 (#46, #50)**:
  * **最上部ナビボタン**: 最上部メインナビゲーションタブのすぐ隣に「🏆 達成マイルストーン」ボタンを設置。
  * **到達日 ＆ 成長スピード分析**: 競合チャンネルが登録者数 **1,000人 (1K)**、**10,000人 (10K)**、**100,000人 (100K)** に到達した日付と、到達にかかった経過日数（開設〜1K、1K〜10K、10K〜100K）をモーダルで一覧表示。
  * **多角ソート ＆ 検索**: 「10万人達成日順」「1万人達成日順」「1K➔10K成長スピード順」での並び替えやリアルタイムキーワード検索。
* **⚠️ 当日データ未取得警告 ＆ 起動時全自動補填レスキュー機能 (#45, #47, #52)**:
  * **未取得自動検知バナー**: 当日 (JST) の時系列データが未取得のチャンネルが存在する場合、ダッシュボード上部に警告バナーを自動表示 (`🟢 全件同期完了` / `⚠️ 本日のデータ未取得あり`)。
  * **🛡️ 起動時全自動レスキュー補填 (#52)**: アプリ起動時に本日分のデータ未取得チャンネルが存在する場合、サーバー起動時に裏側で全自動で YouTube API からデータを取得して DB および JSON 履歴の両方に即座に自動補填・保存。
  * **🔄 ワンクリック即時フェッチ**: 「今すぐデータを取得」ボタンで画面から直接手動補填・DB保存可能。
* **🔥 2大急成長注目シグナルバッジ ＆ ワンタップ急成長トグル (#36, #51, #55)**:
  * **登録者数急増**: 前日比で登録者数が **+100名以上** 急増中のチャンネルにバッジ表示 (`🔥 登録者 +XXX名`)。
  * **総再生数急増 (#51)**: 前日比で総再生数が **+2.0% 以上** 急増中のチャンネルにバッジ表示 (`🔥 再生数 +X.X%`)。
  * **`🔥 急成長のみ` ネオントグルボタン (#55)**: 下段コントロールバーにワンタップ絞り込みトグルを設置。上段のトレンド一括グループの改行・分散を100%回避したまま注目チャンネルのみを一瞬で抽出。
* **🩳 Shorts / 🔴 LIVE / 🎬 通常動画の頻度 ＆ 割合可視化機能 (#56, #57)**:
  * **3色プログレスバー ＆ フォーマットバッジ**: 各競合チャンネルカードの平均再生数エリアに **`🩳 Shorts XX%` `🔴 LIVE XX%` `🎬 通常 XX%`** の内訳とプログレスバーを表示。
  * **100% 高精度判別 ＆ API 一括自動補正 (#57)**: 配信終了後のライブアーカイブ (`liveStreamingDetails`)、24/7ストリーム (`P0D`)、プレミア公開の除外を網羅した多角的判別アルゴリズムを導入。既存 DB 内 2,132 件の動画データも 50件チャンク API 一括通信で 100% 正確に自動補正。
* **🛡️ 米国IP地域除外対策 (`hl="ja"`) ＆ ハンドル名自動二重フォールバック (#54)**:
  * **`hl="ja"` 明示**: GitHub Actions (米国IP) からの地域限定チャンネルの自動除外・漏れを回避。
  * **二重フォールバック**: チャンネルID一括取得 ➔ ID個別取得 ➔ ハンドル名 (`forHandle="@..."`) 個別取得の3段階補正により100%確実な自動取得を実現。
* **📈 視覚的一体化トレンド制御グループ (#43, #44, #50)**:
  * **一体化グループコントロール**: 「📈 トレンド一括表示 ⇄ 📉 一括閉じる」ボタンと「📊 指標選択ドロップダウン」を1つのペアグループとして統合し、改行による離れ離れを完全防止。
  * **指標連動切り替え**: 🎬 総再生数 / 👥 登録者数 / 📹 動画数 の一括切り替え。
* **✨ 超シンプル登録フォーム ＆ 最新100件一括同期 (#49)**:
  * 競合のチャンネルID または ハンドル (`@...`) のみで一瞬で登録完了。
  * 動画同期は一律「最新100件」に自動統一され、常に最高精度の分析データを維持。
* **登録者数規模に応じたランク別グラデーションカード**:
  * 💎 **Diamond** (10万人〜) / 🥇 **Gold** (1万人〜) / 🥈 **Silver** (1,000人〜) / 🥉 **Bronze** (< 1,000人)
* **🔍 リアルタイム・キーワード検索 ＆ 規模ランク切り替えチップ (#40)**:
  * `すべて` / `💎 10万+` / `🥇 1万+` / `🥈 1千+` / `🥉 1千未満` / `📌 ピン留め` のワンタップ切り替え。
* **🔃 インタラクティブな多角ソート機能 (#34)**:
  * 「カスタム順 (手動ドラッグ順)」「登録者数順」「総再生数順」「動画数順」「平均再生数順」の優先配置ソート。

---

### 📈 成長率比較分析画面 (#28, #35, #42, #48)
* **🏆 直近累積成長率 (%) Top 5 / Top 10 自動選択機能 (#48)**:
  * 左サイドバーに **`🏆 成長率 Top 5`** および **`🔥 Top 10`** ワンタップボタンを新設。
  * 最新日付時点での登録者累積成長率 (%) が最も高い上位 5 チャンネル（または 10 チャンネル）を一瞬で自動抽出し、グラフ上に絞り込み表示。
  * 抽出後も個別チェックボックスで自由に追加選択・解除が可能。
* **累積成長率 (%) 比較 2連並列グラフ**:
  * 追跡開始日を `0.0%` とした累積成長率 (%) を算出・可視化（上段: 登録者数 / 下段: 総再生数）。
* **🔍 左サイドバー文字列検索フィルター (#42)**:
  * チャンネル名やハンドル名（`@...`）の入力で比較対象リストをリアルタイム抽出。
* **📌 スクロール追従型 (Sticky) 左サイドバー**:
  * スクロール中も比較フィルターパネルが画面上部に固定追従。

---

### 🤖 ドメイン知識注入型 AIポジショニング分析 (#37, #49)
* **ℹ️ 100文字以内の生成仕組み解説バナー (#49)**:
  * モーダルのタイトル直下に、AI分析レポートがどのような仕組み・データソースで生成されているかを示す解説バナーを表示。
  * *「本レポートは、チャンネルの統計・直近100件の動画(100件未満は全動画)・ドメインナレッジ(RAG)を元に、Gemini AIが競合の強み・弱み・ヒットテーマ・差別化戦略を自動分析して生成しています。」*
* **Gemini API 構造化出力 (Structured Outputs)**:
  * 競合の「強み」「弱み」「ヒットテーマ」「差別化・ポジショニング戦略アドバイス」を精密に抽出・レポート出力。
* **🧠 外部ドメインナレッジファイル (`backend/app/data/domain_knowledge.txt`) によるRAG拡張**:
  * BGM/作業用コンテンツ特有の「連続視聴維持時間（Retention Rate）」や「Shorts流入によるアルゴリズム評価悪化リスク」を考慮した分析。
* **📄 PDF ＆ 🖼️ 高画質画像 (PNG/SVG) 保存・ダウンロード機能 (#37)**:
  * `html2canvas` + `jspdf` による高解像度 (`scale: 2`) レポートローカル保存。

---

## 技術スタック

* **フロントエンド**: Next.js 14 (App Router) + TypeScript + Recharts (データ可視化) + Lucide React + html2canvas + jspdf + Vanilla CSS (CSS Modules)
* **バックエンド**: FastAPI (Python 3.12) + SQLAlchemy + SQLite (ローカルデータベース)
* **AI・外部API**: YouTube Data API v3, Gemini API (`google-genai` SDK / Structured Outputs)
* **自動収集バッチ**: GitHub Actions (日次自動フェッチ) + CLI python バッチ

---

## プロジェクト構成

```text
youtube-research-toolkit/
├── .github/                  # GitHub Actions ワークフロー定義
│   └── workflows/
│       └── fetch_stats.yml   # 日次統計データ自動収集バッチ定義 (日本時間 午前10:00 JST 実行)
├── backend/                  # FastAPI バックエンド
│   ├── app/                  # アプリケーションロジック
│   │   ├── api/endpoints/    # APIルート (channels.py, comparison.py)
│   │   ├── core/             # 設定ファイル (config.py : DATABASE_URL 絶対パス固定)
│   │   ├── data/             # ナレッジファイル (domain_knowledge.txt) & 時系列JSON
│   │   ├── models/           # DBモデル (channel, video, channel_stats_history)
│   │   ├── schemas/          # Pydantic スキーマ
│   │   └── services/         # YouTube API (1リクエスト一括フェッチ対応) & Gemini API 連携サービス
│   ├── main.py               # API エントリーポイント (起動時自動レスキュー補填対応)
│   └── requirements.txt      # 依存ライブラリ一覧
├── frontend/                 # Next.js フロントエンド
│   ├── src/app/
│   │   ├── components/       # UIコンポーネント (ChannelCard, GrowthComparisonView, AIAnalysisModal, MilestoneModal)
│   │   ├── utils/            # API通信関数 (api.ts)
│   │   └── page.tsx          # メインページ (タブ切替・ソートコントロール)
│   └── package.json          # 依存パッケージ一覧
└── README.md                 # 本ドキュメント
```

---

## セットアップ方法

### 必要な環境変数
`backend/.env` ファイルを作成し、以下のキーを設定してください。

```env
# YouTube Data API キー
YOUTUBE_API_KEY=your_youtube_api_key_here

# Gemini API キー (AI分析用)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 1. バックエンド (FastAPI) の起動

```bash
cd backend
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```
[http://localhost:8001/docs](http://localhost:8001/docs) で API Swagger UI にアクセスできます。

### 2. フロントエンド (Next.js) の起動

```bash
cd frontend
npm install
npm run dev
```
[http://localhost:3000](http://localhost:3000) でダッシュボード画面にアクセスできます。

---

## 🔄 データ取得・自動レスキュー構成アーキテクチャ

本システムにおける「日次自動バッチ」「起動時全自動レスキュー」「画面手動取得」のデータフロー全体図です。

```mermaid
flowchart TD
    subgraph Remote["1. リモート自動バッチ (GitHub Actions)"]
        Cron["⏰ 毎日 10:00 JST 起動"] --> GHA_Fetch["fetch_stats.py --json\n(全26チャンネル一括フェッチ)"]
        GHA_Fetch --> GHA_JSON["backend/data/history/{cid}.json\nへ自動保存"]
        GHA_JSON --> Git_Push["git commit & push\n(リポジトリへ自動更新)"]
    end

    subgraph LocalApp["2. ローカルアプリ起動時 (FastAPI 起動)"]
        User_Start["🚀 uvicorn main:app 起動"] --> Git_Pull["git pull (最新JSONを取得)"]
        Git_Pull --> Sync_DB["run_sync_json_mode()\nJSON履歴 ➔ SQLite DBへマージ"]
        Sync_DB --> Rescue_Check{"本日(JST)未取得の\nチャンネルが存在するか？"}
        
        Rescue_Check -- "YES (未取得あり)" --> Auto_Rescue["🛡️ ensure_today_stats_rescued()\n(日本国内IPからYouTube API即時レスキュー)"]
        Auto_Rescue --> Save_Both["SQLite DB ＆ JSON履歴の\n両方に自動補填・保存"]
        
        Rescue_Check -- "NO (全件同期済み)" --> Ready["🟢 全件同期完了 (ダッシュボード表示)"]
        Save_Both --> Ready
    end

    subgraph Manual["3. 画面UIからの手動フェッチ"]
        Btn["🔄 「今すぐデータを取得」ボタン"] --> Fetch_All["POST /api/channels/fetch-all-stats"]
        Fetch_All --> Direct_API["YouTube API 直接フェッチ (日本IP)"]
        Direct_API --> UI_Save["SQLite DB ＆ JSON履歴を即時更新"]
    end
```

---

## 時系列データの自動収集と同期 (GitHub Actions)

PCが起動していなくても、毎日自動的（日本時間 午前10:00 JST / YouTube日次集計確定後の安全時間帯）に競合チャンネルの数値（登録者、再生数、動画数）を収集・蓄積する仕組みを搭載しています。

* **`YOUTUBE_API_KEY` (Secrets)**: YouTube Data API キー（※設定必須）
* **全自動チャンネル検出 (`data/history/*.json`)**:
  * リポジトリ内の `backend/data/history/*.json` ファイル一覧から対象チャンネルを100%全自動検出します。
  * 25チャンネルの最新統計データを **たった1回の API リクエストで一括高速取得** (`get_channels_info_batch`) し、通信成功率100%を維持します。
  * アプリ上で新しいチャンネルを追加・コミットするだけで、GitHub Secrets を手動更新することなく完全自動で日次自動追跡が開始されます。

---

## 💡 日次運用・Git同期ガイドライン

日常的なアプリ利用における `git pull` およびデータ同期のおすすめ運用ルールです。

### 1. おすすめのデイリー運用ルール
* **基本ルール (アプリ起動前)**:
  * アプリ（バックエンド）を起動する前に **`git pull`** を実行していただく運用が最もおすすめです。
  * 毎朝 10:00 (JST) に GitHub Actions が裏側で自動収集してくれた最新の時系列データをローカルに取り込み、API クォータを無駄遣いすることなく同期できます。
* **起動しない日があった場合**:
  * 数日ぶりにアプリを動かす際は `git pull` をしていただくと、過去数日分の蓄積データが一括でローカルにマージされます。
* **`git pull` をし忘れた場合**:
  * 万が一 `git pull` を忘れられても、アプリ起動時に**「起動時全自動レスキュー機能」**が動作し、本日分の未取得チャンネルを自動検知して即座に補填・保存します。

### 2. `git pull` 時にコンフリクト（衝突エラー）が発生した場合の対処
ローカルでアプリを起動した後に `git pull` を実行した際、`Your local changes to the following files would be overwritten by merge` エラーが出た場合は、以下の **1行コマンド** で安全・一瞬に最新化できます：

```bash
git restore backend/data/history/ && git pull origin main
```
ローカルの自動保存ファイルを最新状態へ安全にリセットし、GitHub Actions が取得した最新データを取り込むことができます。
