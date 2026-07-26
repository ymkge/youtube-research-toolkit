from pydantic import BaseModel, Field
from typing import List
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

class AIAnalysisResponse(BaseModel):
    channel_summary: str = Field(
        description="競合チャンネルのポジショニングを1行で簡潔に紹介する日本語の要約文。150文字以内で記述してください。"
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
