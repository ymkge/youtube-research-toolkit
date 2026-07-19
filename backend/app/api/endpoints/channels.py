from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.channel import ChannelCreateRequest, ChannelResponse
from app.services.youtube import youtube_service
from typing import List
import datetime

router = APIRouter()

@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def register_channel(payload: ChannelCreateRequest, db: Session = Depends(get_db)):
    # 1. YouTube API から情報を取得
    try:
        api_data = youtube_service.get_channel_info(payload.identifier)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"YouTube APIエラー: {str(e)}"
        )

    # 2. データベース内にすでに同一チャンネルIDが存在するか確認
    db_channel = db.query(Channel).filter(
        Channel.youtube_channel_id == api_data["youtube_channel_id"]
    ).first()

    # 動画同期に必要なアップロードプレイリストIDを退避し、データ辞書から削除
    uploads_playlist_id = api_data.pop("uploads_playlist_id")

    if db_channel:
        # すでに登録済みの場合は最新データで更新
        for key, value in api_data.items():
            setattr(db_channel, key, value)
        db_channel.updated_at = datetime.datetime.utcnow()
    else:
        # 新規登録
        db_channel = Channel(**api_data)
        db.add(db_channel)
        db.flush()  # DB上のIDを確定させる

    # 3. チャンネルの最新動画を同期
    if uploads_playlist_id:
        try:
            recent_videos = youtube_service.get_recent_videos(
                uploads_playlist_id, limit=payload.import_limit
            )
            for video_data in recent_videos:
                db_video = db.query(Video).filter(
                    Video.youtube_video_id == video_data["youtube_video_id"]
                ).first()

                if db_video:
                    # 既存動画の統計データ更新
                    for key, value in video_data.items():
                        setattr(db_video, key, value)
                    db_video.updated_at = datetime.datetime.utcnow()
                else:
                    # 新規動画の追加
                    new_video = Video(channel_id=db_channel.id, **video_data)
                    db.add(new_video)
        except Exception as e:
            # 動画取得でエラーが発生した場合、それまでのチャンネル追加はコミットしつつ一部エラーを通知
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                detail=f"チャンネル情報は登録されましたが、動画の同期に失敗しました: {str(e)}"
            )

    db.commit()
    db.refresh(db_channel)
    return db_channel

@router.get("/", response_model=List[ChannelResponse])
def get_all_channels(db: Session = Depends(get_db)):
    return db.query(Channel).all()
