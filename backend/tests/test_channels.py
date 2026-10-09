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

def test_sync_channel_videos_sets_videos_synced_at(client, db):
    """
    sync_channel_videos 実行時に、videos_synced_at タイムスタンプが正しく自動更新されるかを検証します。
    """
    from app.api.endpoints.channels import sync_channel_videos
    c = Channel(youtube_channel_id="UC_VID_SYNC", title="Vid Sync Test", sort_order=0)
    db.add(c)
    db.commit()

    assert c.videos_synced_at is None

    # 動画同期関数を安全呼び出し (uploads_playlist_id=None の場合は API リクエストをスキップして指標のみ同期)
    sync_channel_videos(db, c, uploads_playlist_id=None)

    db.refresh(c)
    assert c.videos_synced_at is not None

def test_sync_parent_channel_stats_heals_view_and_video_count(client, db):
    """
    YouTube API からの統計データが古い過去の遅延値であっても、
    Video テーブルに保存された個別動画データの実態 (SUM of views & COUNT of videos) に基づいて
    親 Channel カラムが自動修復・補正されることを検証します。
    """
    from app.api.endpoints.channels import sync_parent_channel_stats
    c = Channel(youtube_channel_id="UC_LAG_HEAL", title="Lag Heal Test", subscriber_count=30, view_count=5000, video_count=35)
    db.add(c)
    db.flush()

    # 古い API 統計履歴 (39本 / 5115回)
    h = ChannelStatsHistory(channel_id=c.id, subscriber_count=30, view_count=5115, video_count=39, recorded_at=date(2026, 9, 7))
    db.add(h)

    # 実態の動画データ (合計 6500回 / 43本)
    v1 = Video(channel_id=c.id, youtube_video_id="v_heal_1", title="Hit Video", view_count=1500, published_at=datetime.utcnow())
    v2 = Video(channel_id=c.id, youtube_video_id="v_heal_2", title="Regular Video", view_count=5000, published_at=datetime.utcnow())
    db.add_all([v1, v2])
    db.commit()

    # 自動補正を実行
    sync_parent_channel_stats(db, c.id)

    db.refresh(c)
    # API 履歴の 5,115回 / 39本 ではなく、動画実態の 6,500回 (1500+5000) が優先採用されていること
    assert c.view_count == 6500
    assert c.video_count >= 2

def test_sync_parent_channel_stats_heals_latest_history_and_growth_rate(client, db):
    """
    latest_history (最新日履歴) も親 Channel とアトミック修復され、
    誤ったマイナス成長率が防止されて正しくプラス成長率が計算されることを検証します。
    """
    from app.api.endpoints.channels import sync_parent_channel_stats
    c = Channel(youtube_channel_id="UC_ATOMIC_HEAL", title="Atomic Heal Test", subscriber_count=48, view_count=6136, video_count=84)
    db.add(c)
    db.flush()

    # 09/07 (前日): 5880回
    h1 = ChannelStatsHistory(channel_id=c.id, subscriber_count=47, view_count=5880, video_count=83, recorded_at=date(2026, 9, 7))
    # 09/08 (本日): APIラグにより古い 5205回 が記録されたケース
    h2 = ChannelStatsHistory(channel_id=c.id, subscriber_count=48, view_count=5205, video_count=84, recorded_at=date(2026, 9, 8))
    
    v1 = Video(channel_id=c.id, youtube_video_id="v_atomic_1", title="Hit Vid", view_count=6136, published_at=datetime.utcnow())
    db.add_all([h1, h2, v1])
    db.commit()

    # アトミック補正実行
    sync_parent_channel_stats(db, c.id)

    db.refresh(h2)
    # h2 の再生数も親と同じ 6136回 へ修復されていること
    assert h2.view_count == 6136

    # API 経由での成長率取得テスト
    response = client.get("/api/channels/")
    assert response.status_code == 200
    
    target_data = next((item for item in response.json() if item["id"] == c.id), None)
    assert target_data is not None
    # 5205 vs 5880 による誤マイナス (-11.5%) ではなく、6136 vs 5880 によるプラス (+4.35%) と表示されること
    assert target_data["view_count"] == 6136
    assert target_data["daily_view_growth_rate"] > 0


@patch("app.api.endpoints.channels.youtube_service")
def test_sync_all_channel_metadata(mock_youtube, client, db):
    """
    全チャンネルのメタデータ（概要欄・タイトル等）一括同期APIのテスト。
    - 概要欄が日本語の最新データに更新されること
    - is_own_channel, is_pinned などのユーザー設定が維持されること
    - ai_analysis キャッシュが破棄されないこと
    - 統計が Max Guard で安全に更新されること
    """
    mock_youtube.is_configured.return_value = True

    # 1. チャンネルのセットアップ
    c1 = Channel(
        youtube_channel_id="UC_SYNC_META_1",
        title="Old English Title",
        description="Old English Description",
        custom_url="@oldsync1",
        subscriber_count=100,
        view_count=5000,
        video_count=10,
        is_pinned=True,
        is_own_channel=True,
        sort_order=5
    )
    # AI分析キャッシュ付きチャンネル
    gen_time = datetime(2026, 9, 20, 10, 0, 0)
    c2 = Channel(
        youtube_channel_id="UC_SYNC_META_2",
        title="Channel 2",
        description="Old Desc 2",
        subscriber_count=200,
        view_count=10000,
        video_count=20,
        ai_analysis='{"title_summary": "Test Summary"}',
        ai_analysis_generated_at=gen_time,
        videos_synced_at=gen_time
    )
    db.add_all([c1, c2])
    db.commit()

    # 2. YouTube API のバッチレスポンスをモック
    mock_youtube.get_channels_info_batch.return_value = {
        "UC_SYNC_META_1": {
            "youtube_channel_id": "UC_SYNC_META_1",
            "title": "新しい日本語タイトル",
            "description": "最新の日本語概要欄です。勉強用BGMをお届けします。",
            "custom_url": "@newsync1",
            "thumbnail_url": "http://example.com/new_thumb.jpg",
            "country": "JP",
            "subscriber_count": 120,
            "view_count": 6000,
            "video_count": 12
        },
        "UC_SYNC_META_2": {
            "youtube_channel_id": "UC_SYNC_META_2",
            "title": "Channel 2 Updated",
            "description": "最新の概要欄2",
            "custom_url": "@c2_handle",
            "thumbnail_url": "http://example.com/c2_thumb.jpg",
            "country": "JP",
            "subscriber_count": 210,
            "view_count": 12000,
            "video_count": 21
        }
    }

    # 3. エンドポイントの実行
    response = client.post("/api/channels/sync-all-metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 2

    # 4. DB内の値の検証
    db.refresh(c1)
    db.refresh(c2)

    # c1 のメタデータが正しく最新化されていること
    assert c1.title == "新しい日本語タイトル"
    assert c1.description == "最新の日本語概要欄です。勉強用BGMをお届けします。"
    assert c1.custom_url == "@newsync1"
    assert c1.thumbnail_url == "http://example.com/new_thumb.jpg"
    assert c1.subscriber_count == 120
    assert c1.view_count == 6000

    # ユーザー設定が 100% 維持されていること
    assert c1.is_pinned is True
    assert c1.is_own_channel is True
    assert c1.sort_order == 5

    # c2 の AI 分析キャッシュが保持されていること
    assert c2.ai_analysis is not None
    assert c2.ai_analysis_generated_at == gen_time
    assert c2.description == "最新の概要欄2"


def test_get_channels_includes_top_videos(client, db):
    """
    GET /api/channels/ が各チャンネルの成長牽引動画 TOP3 (再生数順、平均比付き) を
    正しく抽出して返却することを検証します。
    """
    # チャンネル作成
    c = Channel(
        youtube_channel_id="UC_TOP_VIDS_TEST",
        title="Top Videos Channel",
        subscriber_count=1000,
        view_count=17500,
        video_count=4
    )
    db.add(c)
    db.flush()

    # 動画4本作成 (再生数: 10,000, 5,000, 2,000, 500) 平均 = 4375
    now = datetime.utcnow()
    v1 = Video(channel_id=c.id, youtube_video_id="v_top_1", title="Hit Video 1", view_count=10000, published_at=now - timedelta(days=5), is_short=False)
    v2 = Video(channel_id=c.id, youtube_video_id="v_top_2", title="Hit Video 2", view_count=5000, published_at=now - timedelta(days=10), is_short=True)
    v3 = Video(channel_id=c.id, youtube_video_id="v_top_3", title="Hit Video 3", view_count=2000, published_at=now - timedelta(days=20), is_short=False)
    v4 = Video(channel_id=c.id, youtube_video_id="v_top_4", title="Normal Video", view_count=500, published_at=now - timedelta(days=30), is_short=False)

    db.add_all([v1, v2, v3, v4])
    db.commit()

    response = client.get("/api/channels/")
    assert response.status_code == 200
    channels = response.json()

    target = next((ch for ch in channels if ch["id"] == c.id), None)
    assert target is not None

    top_vids = target["top_videos"]
    # 4本中 上位3本のみ取得されていること
    assert len(top_vids) == 3

    # daily_view_growth が未設定の場合は累計再生数降順
    assert top_vids[0]["youtube_video_id"] == "v_top_1"
    assert top_vids[0]["view_count"] == 10000
    assert top_vids[0]["multiplier_vs_avg"] is not None
    assert top_vids[0]["multiplier_vs_avg"] > 1.0  # 平均4375に対して約2.3倍
    assert "https://i.ytimg.com/vi/v_top_1" in top_vids[0]["thumbnail_url"]

    assert top_vids[1]["youtube_video_id"] == "v_top_2"
    assert top_vids[1]["view_count"] == 5000
    assert top_vids[1]["is_short"] is True

    assert top_vids[2]["youtube_video_id"] == "v_top_3"
    assert top_vids[2]["view_count"] == 2000

    # 前日急増 (daily_view_growth) が発生した場合の検証:
    # 累計が低い v3 (2000 views) が前日 +1500回急増し、v1 (10000 views) が +100回の場合
    v3.daily_view_growth = 1500
    v1.daily_view_growth = 100
    v2.daily_view_growth = 500
    v4.daily_view_growth = 0
    db.commit()

    response2 = client.get("/api/channels/")
    assert response2.status_code == 200
    channels2 = response2.json()
    target2 = next((ch for ch in channels2 if ch["id"] == c.id), None)
    top_vids2 = target2["top_videos"]

    # 前日増加数 (daily_view_growth) 降順で抽出されていること: 1位: v3 (+1500), 2位: v2 (+500), 3位: v1 (+100)
    assert top_vids2[0]["youtube_video_id"] == "v_top_3"
    assert top_vids2[0]["daily_view_growth"] == 1500
    assert top_vids2[1]["youtube_video_id"] == "v_top_2"
    assert top_vids2[1]["daily_view_growth"] == 500
    assert top_vids2[2]["youtube_video_id"] == "v_top_1"
    assert top_vids2[2]["daily_view_growth"] == 100


def test_sync_channel_videos_same_day_resync_guard(db):
    """
    同日(本日)に複数回同期が行われても、前日基準値 (previous_view_count) が固定され、
    当日増分が直前差分で潰されないことを検証します。
    """
    from app.api.endpoints.channels import sync_channel_videos

    c = Channel(
        youtube_channel_id="UC_RESYNC_GUARD",
        title="Resync Guard Channel",
        subscriber_count=500,
        view_count=1000,
        video_count=1
    )
    db.add(c)
    db.commit()

    now_utc = datetime.utcnow()
    # 前日時点: view_count = 1000, previous_view_count = 800, growth = 200 (昨日の同期)
    v = Video(
        channel_id=c.id,
        youtube_video_id="v_resync_1",
        title="Resync Video",
        view_count=1000,
        previous_view_count=800,
        daily_view_growth=200,
        last_growth_updated_at=now_utc - timedelta(days=1),
        published_at=now_utc - timedelta(days=10)
    )
    db.add(v)
    db.commit()

    # 1. 本日初回同期: 1000 ➔ 1500 (前日比 +500)
    with patch("app.services.youtube.youtube_service.get_recent_videos") as mock_get_vids:
        mock_get_vids.return_value = [
            {
                "youtube_video_id": "v_resync_1",
                "title": "Resync Video",
                "view_count": 1500,
                "published_at": now_utc - timedelta(days=10)
            }
        ]
        sync_channel_videos(db, c, "uploads_guard_id")

    db.refresh(v)
    assert v.previous_view_count == 1000
    assert v.daily_view_growth == 500
    assert v.view_count == 1500

    # 2. 本日2回目の再同期 (同日内): 1500 ➔ 1550 (+50追加伸長)
    # 同日再同期ガードにより、previous_view_count (1000) が保持され、
    # daily_view_growth は 1550 - 1000 = 550 になるべき（50で上書きされない）
    with patch("app.services.youtube.youtube_service.get_recent_videos") as mock_get_vids:
        mock_get_vids.return_value = [
            {
                "youtube_video_id": "v_resync_1",
                "title": "Resync Video",
                "view_count": 1550,
                "published_at": now_utc - timedelta(days=10)
            }
        ]
        sync_channel_videos(db, c, "uploads_guard_id")

    db.refresh(v)
    assert v.previous_view_count == 1000  # 前日基準値が保護されていること
    assert v.daily_view_growth == 550      # 当日のトータル増分が保持されていること
    assert v.view_count == 1550


def test_sync_channel_videos_past_vs_fresh_upload(db):
    """
    新規動画インポート時、直近48時間以内の新着動画は初速として daily_view_growth に計上され、
    48時間以上前の過去動画は daily_view_growth=0, previous_view_count=view_count として初期化されることを検証。
    """
    from app.api.endpoints.channels import sync_channel_videos

    c = Channel(
        youtube_channel_id="UC_NEW_VID_TEST",
        title="New Vid Test Channel",
        subscriber_count=100,
        view_count=0,
        video_count=0
    )
    db.add(c)
    db.commit()

    now_utc = datetime.utcnow()
    fresh_pub = now_utc - timedelta(hours=10)
    past_pub = now_utc - timedelta(days=30)

    with patch("app.services.youtube.youtube_service.get_recent_videos") as mock_get_vids:
        mock_get_vids.return_value = [
            {
                "youtube_video_id": "v_fresh",
                "title": "Fresh Video",
                "view_count": 50,
                "published_at": fresh_pub
            },
            {
                "youtube_video_id": "v_past",
                "title": "Past Video",
                "view_count": 500,
                "published_at": past_pub
            }
        ]
        sync_channel_videos(db, c, "uploads_new_test")

    v_fresh = db.query(Video).filter(Video.youtube_video_id == "v_fresh").first()
    v_past = db.query(Video).filter(Video.youtube_video_id == "v_past").first()

    assert v_fresh is not None
    assert v_fresh.daily_view_growth == 50
    assert v_fresh.previous_view_count == 0

    assert v_past is not None
    assert v_past.daily_view_growth == 0
    assert v_past.previous_view_count == 500


def test_get_channels_prevents_growth_jump_on_past_video_import(client, db):
    """
    過去動画の初回同期によって SUM(Video.view_count) が急増した場合でも、
    動画の日次増分合計と大きく乖離した偽成長（ジャンプ）が防止され、
    オーガニックな成長率として算出されることを検証。
    """
    from app.models.channel_stats_history import ChannelStatsHistory

    c = Channel(
        youtube_channel_id="UC_JUMP_GUARD",
        title="Jump Guard Channel",
        subscriber_count=100,
        view_count=1000,
        video_count=10
    )
    db.add(c)
    db.commit()

    # 前日履歴: 10本、10,000回
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    h_prev = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=100,
        view_count=10000,
        video_count=10,
        recorded_at=yesterday
    )
    # 本日履歴: 12本（過去動画2本追加）、10,600回（過去動画分+550回、既存増+50回）
    today = datetime.utcnow().date()
    h_curr = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=100,
        view_count=10600,
        video_count=12,
        recorded_at=today
    )
    db.add_all([h_prev, h_curr])

    # 動画データ: 既存動画の増加合計は +50回
    v_existing = Video(
        channel_id=c.id,
        youtube_video_id="v_ex",
        title="Existing Video",
        view_count=10050,
        previous_view_count=10000,
        daily_view_growth=50,
        published_at=datetime.utcnow() - timedelta(days=5)
    )
    # 過去動画の初回インポート（daily_view_growth=0）
    v_past = Video(
        channel_id=c.id,
        youtube_video_id="v_past_imported",
        title="Past Imported Video",
        view_count=550,
        previous_view_count=550,
        daily_view_growth=0,
        published_at=datetime.utcnow() - timedelta(days=60)
    )
    db.add_all([v_existing, v_past])
    db.commit()

    response = client.get("/api/channels/")
    assert response.status_code == 200
    data = response.json()
    target = next((ch for ch in data if ch["id"] == c.id), None)
    assert target is not None

    # 本来のオーガニックな増分 (+50回 / 10,000回 = 0.5%) として計算され、
    # 過去動画分を含めた +600回 (+6.0%) の偽急成長になっていないこと
    assert target["daily_view_growth_rate"] == 0.5


def test_get_channel_weekday_stats(client, db):
    """
    曜日別動画平均再生数および平均日次増加量の集計API (/api/channels/{id}/weekday-stats) の検証。
    """
    from app.models.channel_stats_history import ChannelStatsHistory

    c = Channel(
        youtube_channel_id="UC_WEEKDAY_TEST",
        title="Weekday Test Channel",
        subscriber_count=100,
        view_count=5000,
        video_count=3
    )
    db.add(c)
    db.commit()

    # 動画作成:
    # 2026-10-04 (日曜日 JST: 2026-10-04 12:00:00 JST / 03:00:00 UTC) -> views: 1000
    # 2026-10-05 (月曜日 JST: 2026-10-05 12:00:00 JST / 03:00:00 UTC) -> views: 200
    # 2026-10-05 (月曜日 JST: 2026-10-05 18:00:00 JST / 09:00:00 UTC) -> views: 400
    v_sun = Video(
        channel_id=c.id,
        youtube_video_id="v_w_sun",
        title="Sunday Video",
        view_count=1000,
        published_at=datetime(2026, 10, 4, 3, 0, 0)
    )
    v_mon1 = Video(
        channel_id=c.id,
        youtube_video_id="v_w_mon1",
        title="Monday Video 1",
        view_count=200,
        published_at=datetime(2026, 10, 5, 3, 0, 0)
    )
    v_mon2 = Video(
        channel_id=c.id,
        youtube_video_id="v_w_mon2",
        title="Monday Video 2",
        view_count=400,
        published_at=datetime(2026, 10, 5, 9, 0, 0)
    )
    db.add_all([v_sun, v_mon1, v_mon2])

    # 履歴作成 (日曜日 ➔ 月曜日):
    # 2026-10-04 (日): 4000
    # 2026-10-05 (月): 4500 (+500 on Mon)
    h_sun = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=100,
        view_count=4000,
        video_count=2,
        recorded_at=datetime(2026, 10, 4).date()
    )
    h_mon = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=100,
        view_count=4500,
        video_count=3,
        recorded_at=datetime(2026, 10, 5).date()
    )
    db.add_all([h_sun, h_mon])
    db.commit()

    response = client.get(f"/api/channels/{c.id}/weekday-stats")
    assert response.status_code == 200
    data = response.json()

    assert data["channel_id"] == c.id
    assert data["channel_title"] == "Weekday Test Channel"
    assert data["best_upload_day"] == "日"  # 日曜日は1本で1000回
    assert data["worst_upload_day"] == "月" # 月曜日は2本で平均300回
    assert data["best_growth_day"] == "月"  # 月曜日に日次+500回

    items = data["items"]
    assert len(items) == 7

    # 月曜日 (index 0)
    mon = items[0]
    assert mon["day_name"] == "月"
    assert mon["video_count"] == 2
    assert mon["total_views"] == 600
    assert mon["average_views"] == 300.0
    assert mon["average_daily_growth"] == 500.0

    # 日曜日 (index 6)
    sun = items[6]
    assert sun["day_name"] == "日"
    assert sun["video_count"] == 1
    assert sun["total_views"] == 1000
    assert sun["average_views"] == 1000.0

    # 火曜日 (index 1: 動画なし)
    tue = items[1]
    assert tue["day_name"] == "火"
    assert tue["video_count"] == 0
    assert tue["average_views"] == 0.0




