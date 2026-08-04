import pytest
from datetime import datetime, timedelta
from app.models.channel import Channel
from app.models.video import Video
from app.api.endpoints.channels import calculate_channel_metrics, parse_iso8601_duration

def test_parse_iso8601_duration():
    """
    ISO 8601 形式の動画時間のパース処理が正しく秒数に変換されるかをテストします。
    """
    assert parse_iso8601_duration("PT15M30S") == 15 * 60 + 30
    assert parse_iso8601_duration("PT1H20M10S") == 3600 + 20 * 60 + 10
    assert parse_iso8601_duration("PT5S") == 5
    assert parse_iso8601_duration("PT40M") == 40 * 60
    assert parse_iso8601_duration("") == 0
    assert parse_iso8601_duration(None) == 0

def test_calculate_metrics_no_videos(db):
    """
    動画が1件もない場合、すべて None/0 が返るかをテストします。
    """
    channel = Channel(
        youtube_channel_id="UC_TEST_NO_VIDEOS",
        title="Test No Videos",
        sort_order=0
    )
    db.add(channel)
    db.commit()

    avg_duration, avg_views, avg_frequency, latest_upload, s_cnt, l_cnt, r_cnt, s_rat, l_rat = calculate_channel_metrics(db, channel.id)
    assert avg_duration is None
    assert avg_views is None
    assert avg_frequency is None
    assert latest_upload is None
    assert s_cnt == 0
    assert l_cnt == 0
    assert r_cnt == 0
    assert s_rat == 0.0
    assert l_rat == 0.0

def test_calculate_metrics_single_video(db):
    """
    動画が1件のみ登録されている場合のメトリクス計算をテストします。
    """
    channel = Channel(
        youtube_channel_id="UC_TEST_SINGLE",
        title="Test Single Video",
        sort_order=1
    )
    db.add(channel)
    db.commit()

    published_date = datetime(2026, 7, 10, 12, 0, 0)
    video = Video(
        channel_id=channel.id,
        youtube_video_id="video_single_id",
        title="Single Video Title",
        duration="PT10M", # 600秒 (通常動画)
        view_count=1000,
        published_at=published_date
    )
    db.add(video)
    db.commit()

    avg_duration, avg_views, avg_frequency, latest_upload, s_cnt, l_cnt, r_cnt, s_rat, l_rat = calculate_channel_metrics(db, channel.id)
    assert avg_duration == 600
    assert avg_views == 1000.0
    assert avg_frequency == 0.0
    assert latest_upload == published_date
    assert s_cnt == 0
    assert l_cnt == 0
    assert r_cnt == 1
    assert s_rat == 0.0
    assert l_rat == 0.0

def test_calculate_metrics_multiple_videos(db):
    """
    動画が複数件登録されている場合の集計（Shorts/LIVE判別含む）をテストします。
    """
    channel = Channel(
        youtube_channel_id="UC_TEST_MULTI",
        title="Test Multi Videos",
        sort_order=2
    )
    db.add(channel)
    db.commit()

    # 1本目: 7/10 投稿 (PT10M = 600秒, views: 1000, 通常動画)
    video1 = Video(
        channel_id=channel.id,
        youtube_video_id="video1_id",
        title="Video 1",
        duration="PT10M",
        view_count=1000,
        published_at=datetime(2026, 7, 10, 10, 0, 0)
    )
    # 2本目: 7/17 投稿 (PT45S = 45秒, views: 2000, Shorts動画)
    video2 = Video(
        channel_id=channel.id,
        youtube_video_id="video2_id",
        title="Video 2 (Shorts)",
        duration="PT45S",
        is_short=True,
        view_count=2000,
        published_at=datetime(2026, 7, 17, 10, 0, 0)
    )
    db.add_all([video1, video2])
    db.commit()

    avg_duration, avg_views, avg_frequency, latest_upload, s_cnt, l_cnt, r_cnt, s_rat, l_rat = calculate_channel_metrics(db, channel.id)
    
    # 平均動画時間: (600 + 45) / 2 = 322.5秒
    assert avg_duration == 322.5
    # 平均再生数: (1000 + 2000) / 2 = 1500回
    assert avg_views == 1500.0
    # 投稿頻度: 2本 / 1.0週間 = 週2.0回
    assert avg_frequency == 2.0
    # 最新投稿日: 7/17 10:00:00
    assert latest_upload == datetime(2026, 7, 17, 10, 0, 0)
    # Shorts件数・比率: 1本 (50.0%)
    assert s_cnt == 1
    assert r_cnt == 1
    assert s_rat == 50.0
