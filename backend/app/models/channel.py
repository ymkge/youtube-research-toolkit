from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base
import datetime

class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    youtube_channel_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    custom_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    subscriber_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    thumbnail_url = Column(String, nullable=True)
    country = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 1対多のリレーションシップ (チャンネル削除時に紐づく動画も削除)
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")
