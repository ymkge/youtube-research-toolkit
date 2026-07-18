# YouTube Research Toolkit - プロジェクト開発ルール

本ドキュメントは、本プロジェクト（YouTube Research Toolkit）において、AIアシスタント（Antigravity）および開発者が遵守すべきコーディング標準、設計原則、および開発手順を定義します。

---

## 1. プロジェクト概要

- **目的**: YouTube競合チャンネルの分析・追跡、およびAIを用いた差別化（ポジショニング）要素の抽出。
- **構成**: フロントエンド（`frontend/`）とバックエンド（`backend/`）のモノレポ構成。

---

## 2. 技術スタック & 設計原則

### 2.1 バックエンド (Python / FastAPI)
- **バージョン**: Python 3.11+
- **フレームワーク**: FastAPI (Asynchronous endpoints)
- **データベース**: SQLite (SQLAlchemy 2.0+ & Alembic によるマイグレーション)
- **データ解析/外部API**: `pandas`, `google-api-python-client` (YouTube Data API), `google-genai` (Gemini API)
- **設計ルール**:
  - 型ヒント（Type Hints）をすべての関数と引数に明示すること。
  - スキーマ定義には `pydantic` (v2) を使用すること。
  - APIのエラーハンドリングは適切に行い、意味のあるHTTPステータスコードを返却すること。

### 2.2 フロントエンド (TypeScript / Next.js)
- **フレームワーク**: Next.js (App Router, TypeScript)
- **状態管理/データ取得**: React Context または React Hooks (`fetch` による通信)
- **スタイリング (CSS)**:
  - **原則**: **Vanilla CSS (CSS Modules)** を使用する。
  - Tailwind CSS などのユーティリティファーストCSSは、明示的な指示がない限り使用しない。
  - モダンなデザイン（ダークモード、グラデーション、滑らかなアニメーション、プレミアムなUI）を意識する。
- **データ可視化**: `recharts` を使用して、競合チャンネルの成長グラフや統計データを美しく描画する。

---

## 3. エージェントの行動指針 (Antigravity への指示)

1. **応答言語**: ユーザーおよび開発者への回答・解説はすべて **日本語** で行うこと。
2. **計画優先 (Planning Mode)**: 大きな変更や新しいファイルの作成を行う前に、必ず `implementation_plan.md` を作成または更新し、ユーザーの承認を得ること。
3. **リンク生成のルール**: ファイルやコードシンボル（クラス、関数など）に言及する際は、必ず `file://` スキームを用いたMarkdownリンク（例: `[main.py](file:///path/to/main.py)`）を作成すること。
4. **既存コードの保護**: 既存のドキュメンテーション（docstring）やコメント、意図的なロジックを不用意に削除・変更しないこと。
