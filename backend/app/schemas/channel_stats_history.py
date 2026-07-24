from pydantic import BaseModel, ConfigDict
from datetime import date

class ChannelStatsHistoryResponse(BaseModel):
    id: int
    channel_id: int
    subscriber_count: int
    view_count: int
    video_count: int
    recorded_at: date

    model_config = ConfigDict(from_attributes=True)
