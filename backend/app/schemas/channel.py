from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class ChannelCreateRequest(BaseModel):
    identifier: str  # チャンネルID (UC...) またはハンドル (@...)
    import_limit: int = 50  # 同期する動画の件数

class TopVideoResponse(BaseModel):
    id: int
    youtube_video_id: str
    title: str
    view_count: int
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    published_at: datetime
    is_short: bool = False
    duration: Optional[str] = None
    thumbnail_url: Optional[str] = None
    multiplier_vs_avg: Optional[float] = None
    daily_view_growth: int = 0

class ChannelResponse(BaseModel):
    id: int
    youtube_channel_id: str
    title: str
    description: Optional[str] = None
    custom_url: Optional[str] = None
    published_at: Optional[datetime] = None
    subscriber_count: int
    view_count: int
    video_count: int
    thumbnail_url: Optional[str] = None
    average_video_duration: Optional[float] = None
    average_views_per_video: Optional[float] = None
    average_upload_frequency: Optional[float] = None
    country: Optional[str] = None
    sort_order: int
    is_pinned: bool
    is_own_channel: bool = False
    latest_video_published_at: Optional[datetime] = None
    daily_sub_growth: int = 0
    daily_view_growth_rate: float = 0.0
    short_video_count: int = 0
    live_stream_count: int = 0
    regular_video_count: int = 0
    short_ratio: float = 0.0
    live_ratio: float = 0.0
    weekly_video_count: int = 0
    anomaly_type: Optional[str] = None
    anomaly_score: Optional[float] = None
    anomaly_reason: Optional[str] = None
    top_videos: List[TopVideoResponse] = []
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChannelSortRequest(BaseModel):
    ids: List[int]

class WeekdayStatItem(BaseModel):
    weekday: int  # 0: 月, 1: 火, 2: 水, 3: 木, 4: 金, 5: 土, 6: 日
    day_name: str  # "月", "火", "水", "木", "金", "土", "日"
    video_count: int  # 該当曜日に投稿された動画本数
    average_views: float  # 該当曜日投稿動画の平均再生数
    total_views: int  # 該当曜日投稿動画の合計再生数
    average_daily_growth: float  # 該当曜日の平均日次再生数増加量 (履歴ベース)

class ChannelWeekdayStatsResponse(BaseModel):
    channel_id: int
    channel_title: str
    best_upload_day: Optional[str] = None  # 最も動画平均再生数が高い曜日 (例: "日")
    worst_upload_day: Optional[str] = None  # 最も動画平均再生数が低い曜日 (例: "金")
    best_growth_day: Optional[str] = None  # 最も日次増加が大きい曜日 (例: "木")
    items: List[WeekdayStatItem]

