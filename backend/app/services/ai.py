import json
import datetime
import os
from google import genai
from google.genai import types
from typing import Optional, List
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

    def analyze_channel_positioning(self, channel_data: dict, videos: list, is_featured: bool = False, own_channel_data: Optional[dict] = None) -> AIAnalysisResponse:
        """
        Gemini API を使用して、競合チャンネルの定量・定性データからポジショニングレポートを生成します。
        注目・急成長チャンネルの場合は、サムネイル勝因・投稿頻度の影響・登録率評価・自チャンネル改善処方箋を出力します。
        """
        if not self.is_configured():
            raise ValueError("Gemini APIキーが設定されていません。")

        # 1. コンテキスト（入力データ）の構造化
        subscribers = channel_data.get('subscriber_count') or 0
        total_views = channel_data.get('view_count') or 0
        avg_views = channel_data.get('average_views_per_video') or 0

        # 定量メトリクスの事前計算 (チャンネル登録率 & 登録獲得効率)
        conv_rate = (subscribers / total_views * 100.0) if total_views > 0 else 0.0
        views_per_sub = (total_views / subscribers) if subscribers > 0 else 0

        # 投稿頻度・ペースの事前計算
        now_date = datetime.datetime.utcnow()
        pub_dates = []
        for v in videos:
            p = v.get('published_at')
            if p:
                if not isinstance(p, datetime.datetime):
                    try:
                        p = datetime.datetime.fromisoformat(str(p).replace('Z', ''))
                    except Exception:
                        p = None
                if isinstance(p, datetime.datetime):
                    pub_dates.append(p)
        pub_dates.sort(reverse=True)

        recent_30d_cnt = sum(1 for p in pub_dates if (now_date - p).days <= 30)
        avg_interval_days = 0.0
        if len(pub_dates) >= 2:
            intervals = [(pub_dates[i] - pub_dates[i+1]).days for i in range(len(pub_dates)-1)]
            avg_interval_days = round(sum(intervals) / len(intervals), 1)

        # 直近30日間のスパイク動画 (再生数 >= 平均 * 1.5) の抽出
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
        context_parts.append("=== 競合チャンネル情報 ===")
        context_parts.append(f"チャンネル名: {channel_data.get('title')}")
        context_parts.append(f"登録者数: {subscribers:,}人")
        context_parts.append(f"総再生数: {total_views:,}回")
        context_parts.append(f"平均動画再生数: {int(avg_views):,}回")
        context_parts.append(f"チャンネル登録率 (CV率): {conv_rate:.2f}% (再生{int(views_per_sub):,}回で1登録獲得)")
        context_parts.append(f"投稿ペーストレンド: 直近30日間で{recent_30d_cnt}本投稿 / 平均投稿間隔: {avg_interval_days}日")
        context_parts.append(f"説明文: {channel_data.get('description', '') or ''}")

        if own_channel_data:
            o_sub = own_channel_data.get('subscriber_count') or 0
            o_views = own_channel_data.get('view_count') or 0
            o_avg = own_channel_data.get('average_views_per_video') or 0
            o_conv = (o_sub / o_views * 100.0) if o_views > 0 else 0.0
            context_parts.append("\n=== 🏠 自チャンネル情報 (比較基準データ) ===")
            context_parts.append(f"自チャンネル名: {own_channel_data.get('title')}")
            context_parts.append(f"登録者数: {o_sub:,}人 | 総再生数: {o_views:,}回 | 平均再生数: {int(o_avg):,}回 | 登録率: {o_conv:.2f}%")
            context_parts.append(f"説明文: {own_channel_data.get('description', '') or ''}")

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

        own_prescription_instruction = ""
        if own_channel_data:
            own_prescription_instruction = """
【💊 自チャンネル改善処方箋の出力指示】
「🏠 自チャンネル情報 (比較基準データ)」が入力されています。競合と自チャンネルを直接対比し、最重要KPIである「チャンネル登録率」を最大化するための具体的アドバイスを `own_channel_prescription` に出力してください：
- `gap_analysis`: 競合と自チャンネルの定量指標・コンテンツの決定的な差（150文字以内）。
- `actionable_steps`: 自チャンネルでチャンネル登録率を高めるため、サムネイルやタイトルで今すぐ試せる具体的A/Bテスト改善案のリスト（最大3項目、各80文字以内）。
- `priority_improvement`: 自チャンネルが最優先で改善・着手すべき最重要ポイント（100文字以内）。
"""
        else:
            own_prescription_instruction = """
【自チャンネル未設定の注意事項】
自チャンネル情報が入力されていないため、`own_channel_prescription` フィールドには必ず JSON の `null` を設定してください。
"""

        # 2. プロンプト（分析指示）の構築
        prompt = f"""
あなたはYouTube競合分析およびマーケティングのプロフェッショナルです。
以下の「競合チャンネル情報」、「最新100件の動画パフォーマンス」、「最優先考慮すべき専門知識」、および「自チャンネル情報」を分析し、自チャンネルの運営に役立つ「ポジショニング分析レポート」を日本語で作成してください。

{knowledge_section}

{featured_instruction}

{own_prescription_instruction}

【分析の指示】
1. 競合独自の「強み（差別化要素）」および「弱み（カバーしきれていない領域）」を抽出してください。
2. 動画一覧の「再生数（平均に対する倍率）」や「動画の長さ（ロング・ショート）」、「高評価数」を比較し、特に高パフォーマンスを発揮している「主要なヒットテーマ」を最大3つ特定してください。
3. `growth_factor_detail` に、競合の「サムネイル・タイトルの具体的勝因 (200文字以内)」、「投稿頻度の影響 (150文字以内)」、および「チャンネル登録率評価 (150文字以内)」を出力してください。
4. 自チャンネルがこの競合に対して、どのようなポジショニングを狙うべきか、具体的な差別化戦略のアドバイスを提示してください。

【文字数・件数制限の厳守】
Pydanticのレスポンススキーマ（response_schema）で定義されている文字数制限を**厳格に守ってください**。
- `channel_summary`: 150文字以内
- `recent_growth_analysis`: 注目フラグ時250文字以内（注目なし時は null）
- `growth_factor_detail.thumbnail_title_factors`: 200文字以内
- `growth_factor_detail.posting_frequency_impact`: 150文字以内
- `growth_factor_detail.conversion_rate_evaluation`: 150文字以内
- `own_channel_prescription.gap_analysis`: 150文字以内
- `own_channel_prescription.actionable_steps`: 各80文字以内 (最大3項目)
- `own_channel_prescription.priority_improvement`: 100文字以内
- `strengths`: 各項目100文字以内（最大4項目）
- `weaknesses`: 各項目100文字以内（最大4項目）
- 各テーマの `reason_for_popularity`: 120文字以内（最大3テーマ）
- `positioning_advice`: 各項目120文字以内（最大4項目）

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
