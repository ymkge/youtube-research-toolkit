import pytest
import datetime
from app.models.channel import Channel
from app.models.video import Video
from app.models.channel_stats_history import ChannelStatsHistory
from app.services.anomaly_detection import detect_channel_anomalies, parse_iso8601_duration

def test_parse_iso8601_duration():
    assert parse_iso8601_duration("PT15M30S") == 930
    assert parse_iso8601_duration("PT1H2M3S") == 3723
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration("") == 0
    assert parse_iso8601_duration(None) == 0

def test_detect_ad_suspected_normal_video():
    """通常動画で再生数が突出(10,000回)しているが、Like率0.2%、Comment率0.005%と極低の場合は広告疑い"""
    channel = Channel(id=1, title="テストチャンネル", subscriber_count=1000, view_count=20000)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="普通動画1", view_count=500, like_count=20, comment_count=5, duration="PT10M"),
        Video(id=2, channel_id=1, youtube_video_id="v2", title="普通動画2", view_count=600, like_count=25, comment_count=4, duration="PT10M"),
        Video(id=3, channel_id=1, youtube_video_id="v3", title="広告プロモーション動画", view_count=10000, like_count=20, comment_count=1, duration="PT5M"),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type == "ad_suspected"
    assert res.anomaly_score is not None
    assert "広告出稿" in res.anomaly_reason
    assert res.target_video_id == "v3"

def test_detect_ad_suspected_shorts():
    """Shorts動画で再生数20,000回、Like率0.5%(<0.8%)、Comment率0.005%(<0.01%)で広告疑い"""
    channel = Channel(id=1, title="テストチャンネル", subscriber_count=1000, view_count=30000)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="Shorts1", view_count=1000, like_count=50, comment_count=5, duration="PT30S", is_short=True),
        Video(id=2, channel_id=1, youtube_video_id="v2", title="Shorts広告", view_count=20000, like_count=100, comment_count=1, duration="PT30S", is_short=True),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type == "ad_suspected"
    assert res.target_video_id == "v2"

def test_bgm_long_video_not_falsely_flagged():
    """長尺BGM動画 (60分) でLike率0.3%(長尺閾値0.2%以上)、Comment率0.02%の場合は誤検知されない"""
    channel = Channel(id=1, title="作業用BGM", subscriber_count=5000, view_count=50000)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="作業用BGM 1時間", view_count=15000, like_count=45, comment_count=3, duration="PT60M"),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type is None

def test_detect_artificial_sub_growth():
    """前日比で登録者が+500名急増しているが、再生数は+100回しか増えていない場合は登録者購入疑い"""
    channel = Channel(id=1, title="テストチャンネル", subscriber_count=2500, view_count=10100)
    videos = []
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    histories = [
        ChannelStatsHistory(id=1, channel_id=1, subscriber_count=2500, view_count=10100, recorded_at=today),
        ChannelStatsHistory(id=2, channel_id=1, subscriber_count=2000, view_count=10000, recorded_at=yesterday),
    ]
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type == "artificial_sub_growth"
    assert "登録者購入" in res.anomaly_reason

def test_detect_ghost_views():
    """再生数20,000回に対してコメント0件、高評価率0.02% (<0.05%) の場合は幽霊再生"""
    channel = Channel(id=1, title="テストチャンネル", subscriber_count=1000, view_count=30000)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="機械的再生動画", view_count=20000, like_count=4, comment_count=0, duration="PT10M"),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type == "ghost_views"
    assert "機械的再生" in res.anomaly_reason

def test_organic_high_engagement_no_anomaly():
    """自然なバズ動画 (再生数20,000回、Like 800 (4.0%)、Comment 30 (0.15%)) は正常判定"""
    channel = Channel(id=1, title="優良チャンネル", subscriber_count=5000, view_count=50000)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="大ヒット企画", view_count=20000, like_count=800, comment_count=30, duration="PT12M"),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type is None

def test_edge_cases_safety():
    """like_count や comment_count が None、view_count が 0 でもエラーにならず安全に動作する"""
    channel = Channel(id=1, title="安全テスト", subscriber_count=0, view_count=0)
    videos = [
        Video(id=1, channel_id=1, youtube_video_id="v1", title="非公開設定", view_count=0, like_count=None, comment_count=None, duration=None),
        Video(id=2, channel_id=1, youtube_video_id="v2", title="高評価非公開", view_count=10000, like_count=None, comment_count=None, duration="PT10M"),
    ]
    histories = []
    
    res = detect_channel_anomalies(channel, videos, histories)
    assert res.anomaly_type is None
