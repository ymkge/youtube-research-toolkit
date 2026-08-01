from pydantic import BaseModel
from typing import List, Optional

class MissingChannelItem(BaseModel):
    id: int
    youtube_channel_id: str
    title: str
    custom_url: Optional[str] = None
    last_recorded_at: Optional[str] = None

class SyncStatusResponse(BaseModel):
    today: str
    total_channels: int
    updated_count: int
    missing_count: int
    is_all_updated: bool
    missing_channels: List[MissingChannelItem]

class FetchMissingResponse(BaseModel):
    message: str
    fetched_count: int
    updated_channels: List[str]
