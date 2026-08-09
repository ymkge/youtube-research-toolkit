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

class AIAnalysisResponse(BaseModel):
    channel_summary: str = Field(
        description="競合チャンネルのポジショニングを1行で簡潔に紹介する日本語の要約文。150文字以内で記述してください。"
    )
    recent_growth_analysis: Optional[str] = Field(
        default=None,
        description="注目フラグが立っている場合のみ生成される、直近の再生数急伸び要因およびヒット動画のサムネイル画像（配色・文字・構図）の視覚解析結果（250文字以内）。注目フラグが無い場合は null としてください。"
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
