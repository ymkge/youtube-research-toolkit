from pydantic import BaseModel
from typing import List, Optional

class ChannelMilestoneItem(BaseModel):
    channel_id: int
    youtube_channel_id: str
    title: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[str] = None # YYYY-MM-DD
    current_subscribers: int
    
    # 達成日付 (YYYY-MM-DD)
    reached_1k_date: Optional[str] = None
    reached_10k_date: Optional[str] = None
    reached_100k_date: Optional[str] = None

    # 追跡開始前達成フラグ
    is_1k_before_tracking: bool = False
    is_10k_before_tracking: bool = False
    is_100k_before_tracking: bool = False

    # 経過日数
    days_to_1k: Optional[int] = None      # 開設〜1,000人達成までの日数
    days_1k_to_10k: Optional[int] = None  # 1,000人〜1万人達成までの日数
    days_10k_to_100k: Optional[int] = None # 1万人〜10万人達成までの日数

class ChannelMilestonesResponse(BaseModel):
    total_channels: int
    milestones: List[ChannelMilestoneItem]
