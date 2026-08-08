# 全開発におけるサブエージェント必須自動査読・計画ブラッシュアップルール

本プロジェクトにおけるあらゆる機能追加・バグ修正・リファクタリングにおいて、以下のワークフローを 100% 厳守します。

## 📋 標準開発ワークフロー規約

```
1. 課題分析・調査 ➔ 2. 初稿実装計画書 (implementation_plan.md) 作成 (デグレ/リスク含む)
       ↓
3. 開発分野に応じた専門サブエージェントの自動起動 & 徹底セルフレビュー
       ↓
4. 専門サブエージェントの査読結果を反映した計画書の最終ブラッシュアップ
       ↓
5. ユーザーへの提示 & 計画承認受領 ➔ 6. 安全な実装 ➔ 7. 検証 (Pytest / TypeScript) & ウォークスルー
```

## 🤖 開発分野別のサブエージェント選定指針

1. **バックエンド / API / DB 開発 (FastAPI / SQLAlchemy / SQLite)**:
   - 役割: `Backend & Database Architecture Reviewer`
   - 監査項目: パフォーマンス (N+1問題, SQLクエリ効率), トランザクション・Lock問題, エラーハンドリング, スキーマ整合性, RESTful API 規格遵守。
2. **データ処理 / バッチ / 自動収集 (Python Script / GitHub Actions / Data Analysis)**:
   - 役割: `Data Engineering & Batch Automation Auditor`
   - 監査項目: 日付計算・タイムゾーン (JST/UTC), データ欠損・ゼロ除算・例外保護, 外部API (YouTube/Gemini) のレスポンスエッジケース, 冪等性 (Idempotency)。
3. **フロントエンド / UI / UX 開発 (Next.js / React / Recharts / CSS)**:
   - 役割: `UI/UX & Frontend Performance Inspector`
   - 監査項目: 画面チラツキ・無限再レンダリング防止, レンダリングパフォーマンス (60fps), レスポンシブ視認性, アクセシビリティ, ネオンダークテーマ整合性。
4. **横断的・大型開発 / リファクタリング**:
   - 役割: `Senior Full-Stack Technical Reviewer`
   - 監査項目: 全体アーキテクチャ整合性, 既存機能への回帰 (デグレ) リスクの全方位点検。
