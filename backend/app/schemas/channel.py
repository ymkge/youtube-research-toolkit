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
