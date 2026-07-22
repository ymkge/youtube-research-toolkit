from sqlalchemy import Column, Integer, BigInteger, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
import datetime

class ChannelStatsHistory(Base):
    __tablename__ = "channel_stats_history"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    subscriber_count = Column(Integer, default=0, nullable=False)
    view_count = Column(BigInteger, default=0, nullable=False) # 再生数は大きい数値になるため BigInteger を採用
    video_count = Column(Integer, default=0, nullable=False)
    recorded_at = Column(Date, default=datetime.date.today, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # チャンネルとのリレーションシップ
    channel = relationship("Channel", back_populates="stats_history")
