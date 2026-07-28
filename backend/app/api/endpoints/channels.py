from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.channel import Channel
from app.models.video import Video
from app.models.channel_stats_history import ChannelStatsHistory
from app.schemas.channel import ChannelCreateRequest, ChannelResponse, ChannelSortRequest
from app.schemas.channel_stats_history import ChannelStatsHistoryResponse
from app.schemas.ai_analysis import AIAnalysisResponse
from app.services.ai import ai_service
from app.services.youtube import youtube_service
from typing import List
import json
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
    チャンネルに紐づく動画データから「平均動画時間」「平均再生数」「平均投稿頻度(週単位)」「最新投稿日時」を算出します。
    """
    videos = db.query(Video).filter(Video.channel_id == channel_id).all()
    if not videos:
        return None, None, None, None

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

    # 3. 平均動画投稿頻度 (週単位) & 4. 最新動画の投稿日時
    sorted_videos = sorted(videos, key=lambda x: x.published_at)
    latest_upload = sorted_videos[-1].published_at if sorted_videos else None

    if len(videos) > 1:
        oldest = sorted_videos[0].published_at
        latest = sorted_videos[-1].published_at
        
        days = (latest - oldest).days
        weeks = max(days, 1) / 7.0
        avg_frequency = len(videos) / weeks
    else:
        avg_frequency = 0.0

    return avg_duration, avg_views, avg_frequency, latest_upload

def sync_channel_videos(db: Session, channel: Channel, uploads_playlist_id: str, import_limit: int = 100):
    """
    指定されたチャンネルの最新動画データを YouTube API から同期し、
    メトリクスを再計算して親の Channel レコードを更新します。
    """
    if uploads_playlist_id:
        recent_videos = youtube_service.get_recent_videos(
            uploads_playlist_id, limit=import_limit
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
                new_video = Video(channel_id=channel.id, **video_data)
                db.add(new_video)
        db.flush()

    # 統計情報の算出と親テーブルへの保存
    avg_duration, avg_views, avg_freq, latest_upload = calculate_channel_metrics(db, channel.id)
    channel.average_video_duration = avg_duration
    channel.average_views_per_video = avg_views
    channel.average_upload_frequency = avg_freq
    channel.latest_video_published_at = latest_upload
    channel.updated_at = datetime.datetime.utcnow()
    db.commit()

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
            sync_channel_videos(db, db_channel, uploads_playlist_id, payload.import_limit)
        except Exception as e:
            # 動画取得でエラーが発生した場合、それまでのチャンネル追加はコミットしつつ一部エラーを通知
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                detail=f"チャンネル情報は登録されましたが、動画の同期に失敗しました: {str(e)}"
            )

    db.commit()
    db.refresh(db_channel)
    
    # 重複更新された場合はステータスコードを 200 OK に変更
    if not is_new:
        response.status_code = status.HTTP_200_OK

    return db_channel

@router.get("/", response_model=List[ChannelResponse])
def get_all_channels(db: Session = Depends(get_db)):
    # ピン留め最優先、その後 sort_order 順
    channels = db.query(Channel).order_by(Channel.is_pinned.desc(), Channel.sort_order.asc()).all()
    if not channels:
        return []

    channel_ids = [c.id for c in channels]

    # たった1回のSQLクエリで全チャンネルの時系列履歴を降順取得 (N+1問題の排除)
    all_histories = (
        db.query(ChannelStatsHistory)
        .filter(ChannelStatsHistory.channel_id.in_(channel_ids))
        .order_by(ChannelStatsHistory.channel_id.asc(), ChannelStatsHistory.recorded_at.desc())
        .all()
    )

    # チャンネルIDごとに履歴をグループ化
    history_map = {}
    for h in all_histories:
        if h.channel_id not in history_map:
            history_map[h.channel_id] = []
        history_map[h.channel_id].append(h)

    for c in channels:
        avg_duration, avg_views, avg_freq, latest_upload = calculate_channel_metrics(db, c.id)
        c.average_video_duration = avg_duration
        c.average_views_per_video = avg_views
        c.average_upload_frequency = avg_freq
        c.latest_video_published_at = latest_upload

        # 前日比登録者増加数の計算 (直近2件の差分)
        ch_histories = history_map.get(c.id, [])
        if len(ch_histories) >= 2:
            latest_sub = ch_histories[0].subscriber_count or 0
            prev_sub = ch_histories[1].subscriber_count or 0
            c.daily_sub_growth = latest_sub - prev_sub
        else:
            c.daily_sub_growth = 0

    return channels

@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """
    指定されたID of チャンネルと、カスケードされたすべての紐づく動画を物理削除します。
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
    
    avg_duration, avg_views, avg_freq, latest_upload = calculate_channel_metrics(db, db_channel.id)
    db_channel.average_video_duration = avg_duration
    db_channel.average_views_per_video = avg_views
    db_channel.average_upload_frequency = avg_freq
    db_channel.latest_video_published_at = latest_upload
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

@router.get("/{channel_id}/history", response_model=List[ChannelStatsHistoryResponse])
def get_channel_history(channel_id: int, db: Session = Depends(get_db)):
    """
    指定されたチャンネルの時系列統計データを日付昇順で取得します。
    """
    db_channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたチャンネルが見つかりませんでした。"
        )
    
    history = db.query(ChannelStatsHistory).filter(
        ChannelStatsHistory.channel_id == channel_id
    ).order_by(ChannelStatsHistory.recorded_at.asc()).all()
    
    return history

@router.post("/{channel_id}/analyze", response_model=AIAnalysisResponse)
def analyze_channel(channel_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    """
    指定されたチャンネルのAIポジショニング分析レポートを生成、またはキャッシュから返却します。
    force=True の場合はキャッシュを無視して最新のドメインナレッジで強制再分析を行います。
    """
    # 1. チャンネルの存在チェック
    db_channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not db_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたチャンネルが見つかりませんでした。"
        )
    
    # 2. 最新100件の動画を取得
    videos = db.query(Video).filter(
        Video.channel_id == channel_id
    ).order_by(Video.published_at.desc()).limit(100).all()
    
    if not videos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分析に必要な動画データがありません。先にチャンネル動画を同期してください。"
        )

    # 3. インテリジェントキャッシュの判定 (force=False の場合のみ試行)
    if not force and db_channel.ai_analysis and db_channel.ai_analysis_generated_at:
        video_sync_time = db_channel.updated_at
        analysis_gen_time = db_channel.ai_analysis_generated_at
        
        # タイムゾーン情報を剥いで比較
        if video_sync_time and analysis_gen_time:
            video_sync_time = video_sync_time.replace(tzinfo=None)
            analysis_gen_time = analysis_gen_time.replace(tzinfo=None)
            
            if analysis_gen_time >= video_sync_time:
                try:
                    cached_data = json.loads(db_channel.ai_analysis)
                    # キャッシュデータに生成日時を追加して返却
                    cached_data["generated_at"] = db_channel.ai_analysis_generated_at
                    return AIAnalysisResponse(**cached_data)
                except Exception as e:
                    print(f"Failed to parse cached AI analysis: {e}")

    # 4. API キーの設定チェックとエラーハンドリング
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini APIキーが設定されていません。バックエンドの環境変数 GEMINI_API_KEY を設定してください。"
        )

    # 5. コンテキストデータの整形
    avg_duration, avg_views, avg_freq, latest_upload = calculate_channel_metrics(db, db_channel.id)
    
    channel_dict = {
        "title": db_channel.title,
        "subscriber_count": db_channel.subscriber_count,
        "view_count": db_channel.view_count,
        "average_views_per_video": avg_views or 0,
        "description": db_channel.description
    }
    
    videos_list = [
        {
            "title": v.title,
            "published_at": v.published_at,
            "view_count": v.view_count,
            "like_count": v.like_count,
            "comment_count": v.comment_count,
            "duration": v.duration,
            "tags": v.tags
        }
        for v in videos
    ]

    # 6. AI分析の実行とエラーハンドリング
    try:
        analysis_result = ai_service.analyze_channel_positioning(channel_dict, videos_list)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI分析サービスに一時的に接続できません: {str(e)}"
        )

    # 7. 結果をキャッシュ保存
    generated_at_val = datetime.datetime.utcnow()
    analysis_result.generated_at = generated_at_val
    
    # model_dump_json() は datetime も適切にシリアライズします
    db_channel.ai_analysis = analysis_result.model_dump_json()
    db_channel.ai_analysis_generated_at = generated_at_val
    # commit時のonupdateによるミリ秒のズレを防ぐため、updated_at も同一の値を明示的に代入
    db_channel.updated_at = generated_at_val
    db.commit()

    return analysis_result
