from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ThemePerformance(BaseModel):
    theme_name: str = Field(
        description="抽出された高パフォーマンスなテーマ名（例: 雨音を取り入れた超ロング作業用BGM）"
    )
    reason_for_popularity: str = Field(
        description="定量データ（再生回数や動画の長さなど）に基づく人気の理由分析。120文字以内で簡潔に記述してください。"
    )
    example_video_title: str = Field(
        description="このテーマを代表する動画タイトル"
    )

class FeaturedVideoInfo(BaseModel):
    youtube_video_id: str = Field(description="YouTube動画のID")
    title: str = Field(description="動画タイトル")
    url: str = Field(description="YouTube動画の絶対URL")
    view_count: int = Field(description="再生回数")
    spike_ratio: float = Field(description="平均再生数に対する倍率")
    thumbnail_url: Optional[str] = Field(default=None, description="サムネイル画像URL")

class GrowthFactorDetail(BaseModel):
    thumbnail_title_factors: str = Field(
        description="【全動画共通フォーマット限定】チャンネル全体で一貫して採用されているサムネイルの配色・構図・フォントやタイトルのテンプレート勝因（200文字以内）。要点を『・』による箇条書きまたは結論ファーストで簡潔に記述してください。※直近スパイク動画解説(recent_growth_analysis)や自チャンネル改善案との重複禁止。"
    )
    posting_frequency_impact: str = Field(
        description="投稿間隔や連投ペース、更新タイミングがアルゴリズム露出およびファン定着に与えている影響の分析（150文字以内）。要点を『・』による箇条書きまたは簡潔な短文で記述してください。"
    )
    conversion_rate_evaluation: str = Field(
        description="チャンネル登録率（再生数に対するチャンネル登録転換効率）の高低に関する要因分析とファン化構造の解説（150文字以内）。要点を『・』による箇条書きまたは簡潔な短文で記述してください。"
    )

class OwnChannelPrescription(BaseModel):
    gap_analysis: str = Field(
        description="急成長競合チャンネルと自チャンネルの定量指標・コンテンツ傾向の決定的な差（ギャップ）の分析（150文字以内）。"
    )
    actionable_steps: List[str] = Field(
        description="【自チャンネルA/Bテスト限定】自チャンネルが登録率向上に向けて即座にA/Bテスト検証すべき具体アクションリスト（各80文字以内、最大3項目）。※競合分析の単なる復唱・再掲は禁止。"
    )
    priority_improvement: str = Field(
        description="自チャンネルが最優先で改善・着手すべき最重要ポイント（100文字以内）。"
    )

class AIAnalysisResponse(BaseModel):
    channel_summary: str = Field(
        description="競合チャンネルのポジショニングを1行で簡潔に紹介する日本語の要約文。150文字以内で記述してください。"
    )
    recent_growth_analysis: Optional[str] = Field(
        default=None,
        description="【直近スパイク要因限定】注目フラグ時のみ生成。直近のヒット（スパイク）動画固有の一時的トリガーやサムネイルフックの個別勝因（250文字以内）。要点を『・』による箇条書きで簡潔に記述してください。注目フラグが無い場合は null。"
    )
    growth_factor_detail: Optional[GrowthFactorDetail] = Field(
        default=None,
        description="急成長チャンネルの深掘り要因分析（サムネイル/タイトル勝因、投稿頻度の影響、チャンネル登録率）。注目フラグまたは急成長チャンネルの場合に出力。"
    )
    own_channel_prescription: Optional[OwnChannelPrescription] = Field(
        default=None,
        description="自チャンネルが設定されている場合のみ出力される、自チャンネル専用の改善処方箋。自チャンネル未設定時は null としてください。"
    )
    featured_videos: List[FeaturedVideoInfo] = Field(
        default_factory=list,
        description="Pythonバックエンドで自動紐付けされた最注目・スパイク動画のリスト（上位1〜3本）"
    )
    strengths: List[str] = Field(
        description="競合チャンネル独自の強み・差別化要素のリスト。各項目は100文字以内で、最大4項目まで。"
    )
    weaknesses: List[str] = Field(
        description="競合チャンネルの弱み、またはカバーしきれていない未開拓（ブルーオーシャン）な領域のリスト。各項目は100文字以内で、最大4項目まで。"
    )
    top_performing_themes: List[ThemePerformance] = Field(
        description="再生数・エンゲージメントが高いテーマのリスト。最大3テーマまで。"
    )
    positioning_advice: List[str] = Field(
        description="自チャンネルがこの競合に対して取るべき具体的な差別化戦略やコンテンツ制作アドバイスのリスト。各項目は120文字以内で、最大4項目まで。"
    )
    generated_at: datetime = Field(
        description="分析レポートが生成された日時"
    )
