from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ChannelCreateRequest(BaseModel):
    identifier: str  # チャンネルID (UC...) またはハンドル (@...)
    import_limit: int = 50  # 同期する動画の件数

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
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
