from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.channel import ChannelCreateRequest, ChannelResponse, ChannelSortRequest
from app.services.youtube import youtube_service
from typing import List
import datetime
import re

router = APIRouter()

def parse_iso8601_duration(duration_str: str) -> int:
    """
    ISO 8601 duration (e.g. PT15M30S) を秒数に変換します。
    """
    if not duration_str:
        return 0
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

def calculate_channel_metrics(db: Session, channel_id: int):
    """
    チャンネルに紐づく動画データから「平均動画時間」「平均再生数」「平均投稿頻度(週単位)」を算出します。
    """
    videos = db.query(Video).filter(Video.channel_id == channel_id).all()
    if not videos:
        return None, None, None

    # 1. 平均動画時間
    total_seconds = 0
    duration_count = 0
    for v in videos:
        if v.duration:
            total_seconds += parse_iso8601_duration(v.duration)
            duration_count += 1
    avg_duration = total_seconds / duration_count if duration_count > 0 else None

    # 2. 1動画あたりの平均視聴回数 (動画平均再生数)
    total_views = sum(v.view_count for v in videos)
    avg_views = total_views / len(videos)

    # 3. 平均動画投稿頻度 (週単位)
    if len(videos) > 1:
        sorted_videos = sorted(videos, key=lambda x: x.published_at)
        oldest = sorted_videos[0].published_at
        latest = sorted_videos[-1].published_at
        
        days = (latest - oldest).days
        weeks = max(days, 1) / 7.0
        avg_frequency = len(videos) / weeks
    else:
        avg_frequency = 0.0

    return avg_duration, avg_views, avg_frequency

@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
def register_channel(payload: ChannelCreateRequest, response: Response, db: Session = Depends(get_db)):
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

    is_new = True
    # 動画同期に必要なアップロードプレイリストIDを退避し、データ辞書から削除
    uploads_playlist_id = api_data.pop("uploads_playlist_id")

    if db_channel:
        is_new = False
        # すでに登録済みの場合は最新データで更新
        for key, value in api_data.items():
            setattr(db_channel, key, value)
        db_channel.updated_at = datetime.datetime.utcnow()
    else:
        # 新規登録時に最大 sort_order + 1 を設定して最後尾に追加
        max_order = db.query(Channel).order_by(Channel.sort_order.desc()).first()
        new_order = (max_order.sort_order + 1) if max_order else 0
        db_channel = Channel(**api_data, sort_order=new_order)
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
    
    # 統計情報の算出とスキーマ動的バインド
    avg_duration, avg_views, avg_freq = calculate_channel_metrics(db, db_channel.id)
    db_channel.average_video_duration = avg_duration
    db_channel.average_views_per_video = avg_views
    db_channel.average_upload_frequency = avg_freq
    
    # 重複更新された場合はステータスコードを 200 OK に変更
    if not is_new:
        response.status_code = status.HTTP_200_OK

    return db_channel

@router.get("/", response_model=List[ChannelResponse])
def get_all_channels(db: Session = Depends(get_db)):
    # ピン留め最優先、その後 sort_order 順
    channels = db.query(Channel).order_by(Channel.is_pinned.desc(), Channel.sort_order.asc()).all()
    for c in channels:
        avg_duration, avg_views, avg_freq = calculate_channel_metrics(db, c.id)
        c.average_video_duration = avg_duration
        c.average_views_per_video = avg_views
        c.average_upload_frequency = avg_freq
    return channels

@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    指定されたIDのチャンネルと、カスケードされたすべての紐づく動画を物理削除します。
    """
    db_channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたチャンネルが見つかりませんでした。"
        )
    db.delete(db_channel)
    db.commit()
    return

@router.patch("/{channel_id}/pin", response_model=ChannelResponse)
def update_channel_pin(channel_id: int, is_pinned: bool, db: Session = Depends(get_db)):
    """
    チャンネルのピン留め（最上部固定）状態を更新します。
    """
    db_channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたチャンネルが見つかりませんでした。"
        )
    db_channel.is_pinned = is_pinned
    db.commit()
    db.refresh(db_channel)
    
    avg_duration, avg_views, avg_freq = calculate_channel_metrics(db, db_channel.id)
    db_channel.average_video_duration = avg_duration
    db_channel.average_views_per_video = avg_views
    db_channel.average_upload_frequency = avg_freq
    return db_channel

@router.put("/sort", status_code=status.HTTP_204_NO_CONTENT)
def update_channels_sort(payload: ChannelSortRequest, db: Session = Depends(get_db)):
    """
    ドラッグ＆ドロップ後の表示順を一括保存します。
    """
    for idx, channel_id in enumerate(payload.ids):
        db_channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if db_channel:
            db_channel.sort_order = idx
    db.commit()
    return
