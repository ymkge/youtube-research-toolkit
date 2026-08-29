import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta
from app.models.channel import Channel
from app.models.video import Video
from app.models.channel_stats_history import ChannelStatsHistory

# YouTube API のモックデータ
MOCK_CHANNEL_INFO = {
    "youtube_channel_id": "UC_MOCK_123",
    "title": "Mocked Channel Title",
    "description": "Mocked Channel Description",
    "custom_url": "@mockedchannel",
    "published_at": datetime(2026, 1, 1, 0, 0, 0),
    "subscriber_count": 50000,
    "view_count": 1200000,
    "video_count": 120,
    "thumbnail_url": "http://example.com/thumb.jpg",
    "country": "JP",
    "uploads_playlist_id": "uploads_playlist_mock_id"
}

MOCK_VIDEOS = [
    {
        "youtube_video_id": "video_mock_01",
        "title": "Mock Video 01 Title",
        "description": "Mock Video 01 Description",
        "published_at": datetime(2026, 7, 20, 12, 0, 0),
        "view_count": 5000,
        "like_count": 250,
        "comment_count": 15,
        "duration": "PT10M15S",
        "tags": "mock,test",
        "category_id": "27"
    },
    {
        "youtube_video_id": "video_mock_02",
        "title": "Mock Video 02 Title",
        "description": "Mock Video 02 Description",
        "published_at": datetime(2026, 7, 25, 12, 0, 0),
        "view_count": 8000,
        "like_count": 400,
        "comment_count": 30,
        "duration": "PT5M45S",
        "tags": "mock,api",
        "category_id": "27"
    }
]

@patch("app.api.endpoints.channels.youtube_service")
def test_register_channel_new(mock_youtube, client, db):
    """
    新規のYouTubeチャンネルを登録するAPIテスト。
    """
    # APIサービスのモック動作定義
    mock_youtube.is_configured.return_value = True
    mock_youtube.get_channel_info.return_value = MOCK_CHANNEL_INFO
    mock_youtube.get_recent_videos.return_value = MOCK_VIDEOS

    response = client.post("/api/channels/", json={"identifier": "@mockedchannel", "import_limit": 50})
    assert response.status_code == 201
    
    data = response.json()
    assert data["youtube_channel_id"] == "UC_MOCK_123"
    assert data["title"] == "Mocked Channel Title"
    
    # データベースに正しく保存されているか検証
    db_channel = db.query(Channel).filter(Channel.youtube_channel_id == "UC_MOCK_123").first()
    assert db_channel is not None
    assert db_channel.subscriber_count == 50000

    # 紐づく動画が登録されているか検証
    videos = db.query(Video).filter(Video.channel_id == db_channel.id).all()
    assert len(videos) == 2
    assert videos[0].youtube_video_id in ["video_mock_01", "video_mock_02"]

def test_get_all_channels(client, db):
    """
    登録済みチャンネル一覧を取得するAPIテスト。
    """
    # テストデータをインメモリDBにあらかじめ登録
    c1 = Channel(youtube_channel_id="UC_A", title="Channel A", sort_order=1, is_pinned=False, subscriber_count=100)
    c2 = Channel(youtube_channel_id="UC_B", title="Channel B", sort_order=0, is_pinned=True, subscriber_count=200)
    db.add_all([c1, c2])
    db.commit()

    # c1 (Channel A) に2件の時系列履歴を追加 (最新: 250, 1日前: 100 ➔ 差分 +150)
    h1 = ChannelStatsHistory(channel_id=c1.id, subscriber_count=100, recorded_at=datetime.utcnow() - timedelta(days=1))
    h2 = ChannelStatsHistory(channel_id=c1.id, subscriber_count=250, recorded_at=datetime.utcnow())
    db.add_all([h1, h2])
    db.commit()

    response = client.get("/api/channels/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    
    # ピン留め最優先、その後表示順でソートされているか検証
    assert data[0]["title"] == "Channel B"  # is_pinned=True が先頭
    assert data[1]["title"] == "Channel A"
    assert data[1]["daily_sub_growth"] == 150

def test_delete_channel(client, db):
    """
    チャンネルを削除した際、カスケードで動画データも一緒に消えるかを検証します。
    """
    c = Channel(youtube_channel_id="UC_DEL", title="To Delete", sort_order=0)
    db.add(c)
    db.flush()

    v = Video(channel_id=c.id, youtube_video_id="video_del_id", title="Video to Del", published_at=datetime.utcnow())
    db.add(v)
    db.commit()

    response = client.delete(f"/api/channels/{c.id}")
    assert response.status_code == 204

    # チャンネルおよび動画が消えていることを検証
    assert db.query(Channel).filter(Channel.id == c.id).first() is None
    assert db.query(Video).filter(Video.channel_id == c.id).first() is None

def test_sync_parent_channel_stats_on_kpi_mismatch(client, db):
    """
    親 Channel のカラム値が過去のままで ChannelStatsHistory の最新値と乖離している場合、
    GET /api/channels 呼び出し時に最新値へ自動同調補正（セルフヒーリング）されることを検証します。
    """
    c = Channel(
        youtube_channel_id="UC_MISMATCH",
        title="Mismatch Channel",
        subscriber_count=30,   # 古い親データ
        view_count=3240,
        video_count=64
    )
    db.add(c)
    db.flush()

    h_latest = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=38,   # 最新履歴データ
        view_count=4056,
        video_count=73,
        recorded_at=datetime.utcnow().date()
    )
    db.add(h_latest)
    db.commit()

    # GET /api/channels/ 呼び出し
    res = client.get("/api/channels/")
    assert res.status_code == 200

    data = res.json()
    target_c = next(item for item in data if item["id"] == c.id)

    # レスポンスの数値が最新履歴（38, 4056, 73）に同調補正されていることを検証
    assert target_c["subscriber_count"] == 38
    assert target_c["view_count"] == 4056
    assert target_c["video_count"] == 73

    # DB 内の親 Channel レコードも修復されていることを検証 (セッションキャッシュをクエリで再取得)
    repaired_c = db.query(Channel).filter(Channel.id == c.id).first()
    assert repaired_c.subscriber_count == 38
    assert repaired_c.view_count == 4056
    assert repaired_c.video_count == 73

def test_toggle_own_channel(client, db):
    """
    POST /api/channels/{id}/toggle-own のトグル切り替えおよび他チャンネルの単一選択排他制御を検証します。
    """
    ch1 = Channel(
        youtube_channel_id="UC_TEST_OWN_1",
        title="Test Channel 1",
        subscriber_count=1000,
        view_count=5000,
        video_count=10,
        is_own_channel=False
    )
    ch2 = Channel(
        youtube_channel_id="UC_TEST_OWN_2",
        title="Test Channel 2",
        subscriber_count=2000,
        view_count=10000,
        video_count=20,
        is_own_channel=False
    )
    db.add_all([ch1, ch2])
    db.commit()

    # ch1 を自チャンネルに設定
    res = client.post(f"/api/channels/{ch1.id}/toggle-own")
    assert res.status_code == 200
    assert res.json()["is_own_channel"] is True

    # ch2 を自チャンネルに設定 -> ch1 は自動で False に一括更新される排他制御の検証
    res2 = client.post(f"/api/channels/{ch2.id}/toggle-own")
    assert res2.status_code == 200
    assert res2.json()["is_own_channel"] is True

    db.refresh(ch1)
    assert ch1.is_own_channel is False

def test_update_channel_pin(client, db):
    """
    チャンネルのピン留め状態をPATCHリクエストで更新するAPIテスト。
    """
    c = Channel(youtube_channel_id="UC_PIN", title="Pin Test", sort_order=0, is_pinned=False)
    db.add(c)
    db.commit()

    response = client.patch(f"/api/channels/{c.id}/pin?is_pinned=true")
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True

    # DB側でも更新されたか検証
    db.refresh(c)
    assert c.is_pinned is True

def test_update_channels_sort(client, db):
    """
    ドラッグ＆ドロップ後の並び順を一括保存するAPIテスト。
    """
    c1 = Channel(youtube_channel_id="UC_1", title="Ch 1", sort_order=0)
    c2 = Channel(youtube_channel_id="UC_2", title="Ch 2", sort_order=1)
    db.add_all([c1, c2])
    db.commit()

    # IDの順序を逆にして送信
    response = client.put("/api/channels/sort", json={"ids": [c2.id, c1.id]})
    assert response.status_code == 204

    # 表示順が更新されたか検証
    db.refresh(c1)
    db.refresh(c2)
    assert c2.sort_order == 0
    assert c1.sort_order == 1

def test_get_channel_history(client, db):
    """
    時系列統計履歴データを取得するAPIテスト。
    """
    c = Channel(youtube_channel_id="UC_HIST", title="History Test", sort_order=0)
    db.add(c)
    db.flush()

    # 2日分のダミー履歴データを登録
    h1 = ChannelStatsHistory(channel_id=c.id, subscriber_count=1000, view_count=10000, video_count=10, recorded_at=date(2026, 7, 22))
    h2 = ChannelStatsHistory(channel_id=c.id, subscriber_count=1100, view_count=11000, video_count=11, recorded_at=date(2026, 7, 23))
    db.add_all([h1, h2])
    db.commit()

    response = client.get(f"/api/channels/{c.id}/history")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 2
    assert data[0]["recorded_at"] == "2026-07-22"
    assert data[1]["recorded_at"] == "2026-07-23"
