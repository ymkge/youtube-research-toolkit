import json
import datetime
import os
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.ai_analysis import AIAnalysisResponse

def load_domain_knowledge() -> str:
    """
    app/data/domain_knowledge.txt から専門ドメイン知識を安全に読み込みます。
    ファイルが存在しない場合は空文字を返します。
    """
    file_path = os.path.join(os.path.dirname(__file__), "..", "data", "domain_knowledge.txt")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    return ""

class AIService:
    def is_configured(self) -> bool:
        """
        Gemini API キーが設定されているかどうかを判定します。
        """
        return bool(settings.GEMINI_API_KEY)

    def analyze_channel_positioning(self, channel_data: dict, videos: list) -> AIAnalysisResponse:
        """
        Gemini API を使用して、競合チャンネルの定量・定性データからポジショニングレポートを生成します。
        構造化出力 (Structured Outputs) により、Pydantic スキーマ通りの結果を保証します。
        """
        if not self.is_configured():
            raise ValueError("Gemini APIキーが設定されていません。")

        # 1. コンテキスト（入力データ）の構造化
        # チャンネルの基本データ (None時は安全に0にフォールバック)
        subscribers = channel_data.get('subscriber_count') or 0
        total_views = channel_data.get('view_count') or 0
        avg_views = channel_data.get('average_views_per_video') or 0

        context_parts = []
        context_parts.append("=== チャンネル情報 ===")
        context_parts.append(f"チャンネル名: {channel_data.get('title')}")
        context_parts.append(f"登録者数: {subscribers:,}人")
        context_parts.append(f"総再生数: {total_views:,}回")
        context_parts.append(f"平均動画再生数: {int(avg_views):,}回")
        context_parts.append(f"説明文: {channel_data.get('description', '') or ''}")
        context_parts.append("\n=== 最新100件の動画パフォーマンス ===")
        
        for idx, video in enumerate(videos, 1):
            views = video.get('view_count') or 0
            likes = video.get('like_count') or 0
            comments = video.get('comment_count') or 0
            ratio = (views / avg_views) if avg_views > 0 else 1.0
            
            # 再生数が平均のどれくらいかをAIが評価しやすいように倍率も渡す
            perf_label = f"{ratio:.1f}倍"
            
            published_str = "N/A"
            if video.get('published_at'):
                if isinstance(video.get('published_at'), datetime.datetime):
                    published_str = video.get('published_at').strftime('%Y-%m-%d')
                else:
                    published_str = str(video.get('published_at'))

            context_parts.append(
                f"{idx}. タイトル: {video.get('title')}\n"
                f"   投稿日: {published_str}\n"
                f"   再生数: {views:,}回 (平均の{perf_label})\n"
                f"   高評価: {likes:,}回 / コメント: {comments:,}回\n"
                f"   動画長: {video.get('duration', 'N/A') or 'N/A'}\n"
                f"   タグ: {video.get('tags', '') or ''}\n"
            )

        prompt_input = "\n".join(context_parts)

        # ドメインナレッジの読み込みと注入
        domain_knowledge = load_domain_knowledge()
        knowledge_section = ""
        if domain_knowledge:
            knowledge_section = f"""
=== [Domain Knowledge & Strategic Constraints (最優先考慮すべき専門知識)] ===
以下のドメイン知識および注意点・リスク考察を【絶対的な前提知識】として分析を行ってください。
画一的なショート動画（Shorts）作成の安易な推奨は避け、BGM・作業用コンテンツとしての滞在時間（Watch Time / Retention Rate）や継続再生価値を守るための戦略アドバイスを提示してください。

{domain_knowledge}
==============================================================
"""

        # 2. プロンプト（分析指示）の構築
        prompt = f"""
あなたはYouTube競合分析およびマーケティングのプロフェッショナルです。
以下の「チャンネル情報」、「最新100件の動画パフォーマンス」、および「最優先考慮すべき専門知識」を分析し、自チャンネルの運営に役立つ「ポジショニング分析レポート」を日本語で作成してください。

{knowledge_section}

【分析の指示】
1. 競合独自の「強み（差別化要素）」および「弱み（カバーしきれていない領域）」を抽出してください。
2. 動画一覧の「再生数（平均に対する倍率）」や「動画の長さ（ロング・ショート）」、「高評価数」を比較し、特に高パフォーマンスを発揮している「主要なヒットテーマ」を最大3つ特定してください。
3. 自チャンネルがこの競合に対して、どのようなポジショニングを狙うべきか、具体的な差別化戦略のアドバイスを提示してください。
4. ドメイン知識で指定されたリスク（Shortsによる滞在時間低下等）を踏まえ、短期的ではなく長期的・本質的な成長施策を中心に提案してください。

【文字数・件数制限の厳守】
Pydanticのレスポンススキーマ（response_schema）で定義されている文字数制限を**厳格に守ってください**。
- `channel_summary`: 150文字以内
- `strengths`: 各項目100文字以内（最大4項目）
- `weaknesses`: 各項目100文字以内（最大4項目）
- 各テーマの `reason_for_popularity`: 120文字以内（最大3テーマ）
- `positioning_advice`: 各項目120文字以内（最大4項目）

【データの解釈に関する注意】
登録者数、再生数、高評価数、コメント数が 0 と表示されている項目は、実際には「非公開」または「データ未取得」を意味する場合があります。0だからといって単純に人気が無いチャンネル・動画であると決めつけることはせず、タイトルや説明文、他の動画の再生数などのデータから、総合的に強みやポジショニングを判定してください。

【入力データ】
{prompt_input}
"""

        # 3. Gemini API 呼び出し (構造化出力の設定)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIAnalysisResponse,
                temperature=0.2, # 創造性を落として、論理的にデータ分析させる
            )
        )

        # 4. JSONレスポンスのパースとスキーマオブジェクト化
        result_json = json.loads(response.text)
        
        # Pydantic スキーマでパースして返却
        return AIAnalysisResponse(**result_json)

ai_service = AIService()
