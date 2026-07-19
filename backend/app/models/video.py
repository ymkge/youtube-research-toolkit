from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
import datetime

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    youtube_video_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=False)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    duration = Column(String, nullable=True)  # ISO 8601 (例: PT15M30S)
    tags = Column(Text, nullable=True)        # カンマ区切りの文字列で保存
    category_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # チャンネルとの多対1リレーションシップ
    channel = relationship("Channel", back_populates="videos")
