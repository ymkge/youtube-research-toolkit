import json
import datetime
import os
import time
import random
from google import genai
from google.genai import types, errors
from typing import Optional, List
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.ai_analysis import AIAnalysisResponse, FeaturedVideoInfo

from pathlib import Path

MAX_FILE_SIZE_BYTES = 100 * 1024  # 100 KB
MAX_TOTAL_CHARS = 50_000         # 50,000文字 (トークン数オーバーフロー保護)

def load_domain_knowledge() -> str:
    """
    backend/data/knowledge/ 配下の *.md および *.txt ファイルを
    ファイル名小文字昇順で安全に読み込み、RAGナレッジとして結合します。
    ディレクトリが存在しない・空の場合は旧 domain_knowledge.txt へフォールバックします。
    """
    base_dir = Path(__file__).resolve().parent.parent / "data"
    knowledge_dir = base_dir / "knowledge"
    
    knowledge_blocks = []
    
    if knowledge_dir.exists() and knowledge_dir.is_dir():
        files = [
            p for p in knowledge_dir.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in (".md", ".txt")
        ]
        files.sort(key=lambda p: p.name.lower())
        
        total_chars = 0
        for file_path in files:
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
                    print(f"[RAG Warning] Knowledge file {file_path.name} exceeds size limit (100KB). Skipping.")
                    continue
                    
                content = file_path.read_text(encoding="utf-8", errors="replace").strip()
                if not content:
                    continue
                
                if total_chars + len(content) > MAX_TOTAL_CHARS:
                    print(f"[RAG Warning] Total knowledge limit reached ({MAX_TOTAL_CHARS} chars). Skipping {file_path.name}.")
                    break
                    
                block = f"--- Knowledge Source: {file_path.name} ---\n{content}"
                knowledge_blocks.append(block)
                total_chars += len(block)
            except Exception as e:
                print(f"[RAG Error] Failed to read {file_path.name}: {e}")
                continue

    # 旧ファイルへのフォールバック
    if not knowledge_blocks:
        fallback_file = base_dir / "domain_knowledge.txt"
        if fallback_file.exists() and fallback_file.is_file():
            try:
                content = fallback_file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    knowledge_blocks.append(f"--- Knowledge Source: domain_knowledge.txt ---\n{content}")
            except Exception as e:
                print(f"[RAG Error] Failed to read fallback file: {e}")

    return "\n\n".join(knowledge_blocks)

class AIService:
    def is_configured(self) -> bool:
        """
        Gemini API キーが設定されているかどうかを判定します。
        """
        return bool(settings.GEMINI_API_KEY)

    def _generate_content_with_retry(self, client: genai.Client, contents: list, config: types.GenerateContentConfig):
        """
        Gemini API 呼び出し時に 503 (High Demand) または 429 (Rate Limit) エラーが発生した場合、
        指数バックオフ＋ジッターで自動リトライし、それでも失敗した場合はサブモデルへ自動フォールバックします。
        """
        models_to_try = [
            (settings.GEMINI_MODEL, 3),
            (settings.GEMINI_FALLBACK_MODEL, 2)
        ]

        last_exception = None

        for model_name, max_retries in models_to_try:
            # フォールバックモデル使用時は、負荷軽減のため画像 Part を除外してテキスト主体に切り替え
            current_contents = contents
            if model_name == settings.GEMINI_FALLBACK_MODEL:
                current_contents = [c for c in contents if isinstance(c, str)]

            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=current_contents,
                        config=config
                    )
                    return response
                except errors.APIError as e:
                    last_exception = e
                    if e.code in (503, 429) or isinstance(e, errors.ServerError):
                        delay = min(1.0 * (2.0 ** attempt) + random.uniform(0.1, 0.5), 8.0)
                        print(f"[Gemini API Warning] Model '{model_name}' status {e.code}. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise e
                except Exception as ex:
                    last_exception = ex
                    delay = min(1.0 * (2.0 ** attempt) + random.uniform(0.1, 0.5), 8.0)
                    print(f"[Gemini API Exception] Model '{model_name}': {ex}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)

        # 全試行失敗時
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI分析サービスが混雑しています。一時的なエラーのため時間をおいて再試行してください。(詳細: {str(last_exception)})"
        )

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

        conv_rate = (subscribers / total_views * 100.0) if total_views > 0 else 0.0
        views_per_sub = (total_views / subscribers) if subscribers > 0 else 0

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
        context_parts.append(f"=== 分析対象競合チャンネル: {channel_data.get('title')} ===")
        context_parts.append(f"登録者数: {subscribers:,}人")
        weekly_cnt = channel_data.get('weekly_video_count')
        if weekly_cnt is None:
            weekly_cnt = sum(1 for p in pub_dates if (now_date - p).days <= 7)

        context_parts.append(f"総再生数: {total_views:,}回")
        context_parts.append(f"平均動画再生数: {int(avg_views):,}回")
        context_parts.append(f"チャンネル登録率 (CV率): {conv_rate:.2f}% (再生{int(views_per_sub):,}回で1登録獲得)")
        context_parts.append(f"投稿ペーストレンド: 直近7日間で{weekly_cnt}本投稿 | 直近30日間で{recent_30d_cnt}本投稿 / 平均投稿間隔: {avg_interval_days}日")
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
                    f"・タイトル: {s_video.get('title')} | 投稿日: {days_val}日前 | 再生数: {s_video.get('view_count', 0):,}回 ({ratio_val:.1f}倍) | 高評価: {s_video.get('like_count', 0):,}"
                )

        context_parts.append("\n=== 最新動画パフォーマンス (直近50件) ===")
        for idx, video in enumerate(videos[:50], 1):
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

            tags_raw = video.get('tags', '') or ''
            tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()][:3]
            tags_str = ",".join(tags_list)

            context_parts.append(
                f"{idx}. [{published_str}] {video.get('title')} | 再生:{views:,}回({perf_label}) | 高評価:{likes:,} | 長さ:{video.get('duration', 'N/A') or 'N/A'} | タグ:{tags_str}"
            )

        prompt_input = "\n".join(context_parts)

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

        sub_growth = channel_data.get('daily_sub_growth') or 0
        decline_instruction = ""
        if sub_growth < 0:
            context_parts.append(f"\n=== ⚠️ 【衰退シグナル検知】前日比でチャンネル登録者数が減少中 ({sub_growth:,}名) ===")
            decline_instruction = f"""
【📉 登録者減少（衰退傾向）チャンネル特記事項 ＆ 反面教師分析指示】
このチャンネルは前日比で登録者数が減少 ({sub_growth:,}名) している衰退傾向にあります。
「なぜユーザーの離脱・登録解除が起きているのか（投稿頻度の低下、動画内容のマンネリ化、アルゴリズム露出低下など）」の原因分析と、
「自チャンネルが絶対に真似してはならない反面教師としての教訓アドバイス」を
`decline_reason_analysis` フィールドに250文字以内で要点を『・』箇条書きで具体的に出力してください。
"""
        else:
            decline_instruction = """
【通常チャンネル注意事項】
登録者減少フラグが立っていないため、`decline_reason_analysis` フィールドには必ず JSON の `null` を設定してください。
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

        target_subscribers = channel_data.get('subscriber_count') or 0
        own_subscribers = own_channel_data.get('subscriber_count') if own_channel_data else None

        early_stage_instruction = ""
        if target_subscribers < 100 or (own_subscribers is not None and own_subscribers < 100):
            early_stage_instruction = """
【🌱 初期立ち上げチャンネル（登録者100人未満）特記指示】
分析対象または自チャンネルは「登録者100人未満の初期立ち上げフェーズ」にあります。
ドメインナレッジ「02_zero_to_100_growth_strategy.md」を最優先で参照し、以下の点を意識してアドバイスを出力してください：
1. 「本数不足」ではなく「認知度・信頼感不足」が原因であることを踏まえ、誰に届けるか（属性＋具体悩み）を絞る『ペルソナ設定』と、同規模チャンネルで再生されている『資産テーマの横展開リサーチ』を優先的に推奨してください。
2. 義理登録やショート乱発・広告による“数字だけの登録者”ではなく、次の動画も見てくれる自然なファンを集め『勝ちパターン』を確立する具体的なアドバイスを提示してください。
"""

        prompt = f"""
あなたはYouTube競合分析およびマーケティングのプロフェッショナルです。
以下の「競合チャンネル情報」、「最新50件の動画パフォーマンス」、「最優先考慮すべき専門知識」、および「自チャンネル情報」を分析し、自チャンネルの運営に役立つ「ポジショニング分析レポート」を日本語で作成してください。

{knowledge_section}

{early_stage_instruction}

{featured_instruction}

{decline_instruction}

{own_prescription_instruction}

【分析の指示】
1. 競合独自の「強み（差別化要素）」および「弱み（カバーしきれていない領域）」を抽出してください。
2. 動画一覧の「再生数（平均に対する倍率）」や「動画の長さ（ロング・ショート）」、「高評価数」を比較し、特に高パフォーマンスを発揮している「主要なヒットテーマ」を最大3つ特定してください。
3. `growth_factor_detail` に、競合の「サムネイル・タイトルの具体的勝因 (200文字以内)」、「投稿頻度の影響 (150文字以内)」、および「チャンネル登録率評価 (150文字以内)」を出力してください。
4. 自チャンネルがこの競合に対して、どのようなポジショニングを狙うべきか、具体的な差別化戦略のアドバイスを提示してください。

【🚫 分析内容の重複禁止・排他ルール（絶対厳守）】
レポート内の各フィールドは以下の役割分担に従い、内容や文言の重複を厳格に避けてください：
1. `recent_growth_analysis` (直近伸び要因):
   - 直近30日間のスパイク動画固有の「一時的・短期的トリガー（特定企画ネタや特別フック）」に特化して記述してください。
   - チャンネル全体の普遍的な傾向や自チャンネルへのアドバイスは含めないでください。
2. `growth_factor_detail.thumbnail_title_factors` (共通サムネイル勝因):
   - チャンネル全体を通じた「普遍的・構造的なデザイン規則（配色・文字配置・ロゴ等の型）」に特化して記述してください。
   - 直近の特定動画のネタ解説や、自チャンネルへの改善案は含めないでください。
3. `own_channel_prescription` (自チャンネル改善処方箋):
   - 自チャンネルが明日から実践・検証すべき「具体A/Bテスト提案」に特化してください。
   - 競合チャンネルの分析結果をそのまま繰り返すことは厳禁です。

【📝 結論ファースト・箇条書きフォーマットルール】
- `recent_growth_analysis` および `growth_factor_detail` のテキストは、ダラダラとした長文段落を避けて【結論】を先頭に置き、要点を「・」による箇条書き（最大2〜3項目）で簡潔に出力してください。

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

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        contents_list = [prompt]
        if image_parts:
            contents_list.extend(image_parts)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AIAnalysisResponse,
            temperature=0.2,
        )

        response = self._generate_content_with_retry(client, contents_list, config)

        result_json = json.loads(response.text)
        
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
