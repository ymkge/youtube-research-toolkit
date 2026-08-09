import json
import datetime
import os
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.ai_analysis import AIAnalysisResponse, FeaturedVideoInfo

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

    def analyze_channel_positioning(self, channel_data: dict, videos: list, is_featured: bool = False) -> AIAnalysisResponse:
        """
        Gemini API を使用して、競合チャンネルの定量・定性データからポジショニングレポートを生成します。
        注目フラグ (is_featured=True) の場合は、サムネイル画像のマルチモーダル解析と直近再生数急増要因を出力します。
        """
        if not self.is_configured():
            raise ValueError("Gemini APIキーが設定されていません。")

        # 1. コンテキスト（入力データ）の構造化
        subscribers = channel_data.get('subscriber_count') or 0
        total_views = channel_data.get('view_count') or 0
        avg_views = channel_data.get('average_views_per_video') or 0

        # 直近30日間のスパイク動画 (再生数 >= 平均 * 1.5) の抽出
        now_date = datetime.datetime.utcnow()
        recent_spikes = []
        for v in videos:
            pub = v.get('published_at')
            v_views = v.get('view_count') or 0
            if pub:
                if not isinstance(pub, datetime.datetime):
                    try:
                        pub = datetime.datetime.fromisoformat(str(pub).replace('Z', ''))
                    except Exception:
                        pub = None
                if isinstance(pub, datetime.datetime):
                    days_ago = (now_date - pub).days
                    if days_ago <= 30 and avg_views > 0 and (v_views >= avg_views * 1.5):
                        recent_spikes.append((v_views / avg_views, days_ago, v))

        recent_spikes.sort(key=lambda x: x[0], reverse=True)

        context_parts = []
        context_parts.append("=== チャンネル情報 ===")
        context_parts.append(f"チャンネル名: {channel_data.get('title')}")
        context_parts.append(f"登録者数: {subscribers:,}人")
        context_parts.append(f"総再生数: {total_views:,}回")
        context_parts.append(f"平均動画再生数: {int(avg_views):,}回")
        context_parts.append(f"説明文: {channel_data.get('description', '') or ''}")

        if is_featured and recent_spikes:
            context_parts.append("\n=== 🔥 【特筆データ】直近30日間のヒット・スパイク動画 ===")
            for ratio_val, days_val, s_video in recent_spikes[:5]:
                context_parts.append(
                    f"・タイトル: {s_video.get('title')}\n"
                    f"  投稿日: {days_val}日前 | 再生数: {s_video.get('view_count', 0):,}回 (平均の{ratio_val:.1f}倍)\n"
                    f"  高評価: {s_video.get('like_count', 0):,}回 | タグ: {s_video.get('tags', '') or ''}\n"
                )

        context_parts.append("\n=== 最新100件の動画パフォーマンス ===")
        
        for idx, video in enumerate(videos, 1):
            views = video.get('view_count') or 0
            likes = video.get('like_count') or 0
            comments = video.get('comment_count') or 0
            ratio = (views / avg_views) if avg_views > 0 else 1.0
            
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

        # サムネイル画像の安全なダウンロード (注目チャンネルかつスパイク動画存在時)
        image_parts = []
        if is_featured and recent_spikes:
            import httpx
            with httpx.Client(timeout=3.0) as http_client:
                for _, _, video_item in recent_spikes[:3]:
                    thumb_url = video_item.get("thumbnail_url")
                    if thumb_url:
                        try:
                            res = http_client.get(thumb_url)
                            if res.status_code == 200:
                                image_parts.append(
                                    types.Part.from_bytes(
                                        data=res.content,
                                        mime_type=res.headers.get("content-type", "image/jpeg")
                                    )
                                )
                        except Exception as ex:
                            print(f"Thumbnail fetch warning: {ex}")

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

        featured_instruction = ""
        if is_featured:
            featured_instruction = """
【🔥 注目チャンネル特記事項 ＆ 直近急伸び要因の深掘り指示】
このチャンネルは【注目フラグ（ピン留め・直近急成長中）】が設定された最重要分析対象です。
添付されている直近のヒット（スパイク）動画のテキストデータおよび画像（サムネイル画像）を分析し、
「なぜ直近で再生数が急激に伸びたのか？」その理由・要因（ヒットテーマ、タイトルキーワード、サムネイルの視覚的勝因：配色・大文字表記・構図など）を
`recent_growth_analysis` フィールドに250文字以内で具体的に出力してください。
"""
        else:
            featured_instruction = """
【通常チャンネル注意事項】
注目フラグが立っていないため、`recent_growth_analysis` フィールドには必ず JSON の `null` を設定してください（文字入力は不要です）。
"""

        # 2. プロンプト（分析指示）の構築
        prompt = f"""
あなたはYouTube競合分析およびマーケティングのプロフェッショナルです。
以下の「チャンネル情報」、「最新100件の動画パフォーマンス」、および「最優先考慮すべき専門知識」を分析し、自チャンネルの運営に役立つ「ポジショニング分析レポート」を日本語で作成してください。

{knowledge_section}

{featured_instruction}

【分析の指示】
1. 競合独自の「強み（差別化要素）」および「弱み（カバーしきれていない領域）」を抽出してください。
2. 動画一覧の「再生数（平均に対する倍率）」や「動画の長さ（ロング・ショート）」、「高評価数」を比較し、特に高パフォーマンスを発揮している「主要なヒットテーマ」を最大3つ特定してください。
3. 自チャンネルがこの競合に対して、どのようなポジショニングを狙うべきか、具体的な差別化戦略のアドバイスを提示してください。
4. ドメイン知識で指定されたリスク（Shortsによる滞在時間低下等）を踏まえ、短期的ではなく長期的・本質的な成長施策を中心に提案してください。

【文字数・件数制限の厳守】
Pydanticのレスポンススキーマ（response_schema）で定義されている文字数制限を**厳格に守ってください**。
- `channel_summary`: 150文字以内
- `recent_growth_analysis`: 注目フラグ時250文字以内（注目なし時は null）
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
        
        contents_list = [prompt]
        if image_parts:
            contents_list.extend(image_parts)

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents_list,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIAnalysisResponse,
                temperature=0.2,
            )
        )

        # 4. JSONレスポンスのパースとスキーマオブジェクト化
        result_json = json.loads(response.text)
        
        # 最注目・スパイク動画オブジェクトの構築と自動注入
        featured_video_objects = []
        if is_featured and recent_spikes:
            for ratio_val, _, s_video in recent_spikes[:3]:
                v_id = s_video.get("youtube_video_id") or ""
                v_url = f"https://www.youtube.com/watch?v={v_id}" if v_id else ""
                featured_video_objects.append(
                    FeaturedVideoInfo(
                        youtube_video_id=v_id,
                        title=s_video.get("title", ""),
                        url=v_url,
                        view_count=s_video.get("view_count", 0),
                        spike_ratio=round(ratio_val, 1),
                        thumbnail_url=s_video.get("thumbnail_url")
                    )
                )

        analysis_obj = AIAnalysisResponse(**result_json)
        analysis_obj.featured_videos = featured_video_objects
        return analysis_obj

ai_service = AIService()
