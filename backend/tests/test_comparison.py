import pytest
from datetime import datetime, timedelta
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory

def test_get_channels_comparison_success(client, db):
    """
    複数チャンネルの成長率比較APIが正常に動作し、最古の記録日(基準日=0%)からの
    累積成長率(%)が正しく算出されるかを検証。
    """
    # チャンネルA (基準日: 100人, 1,000回 ➔ 翌日: 150人, 2,000回 ➔ +50%, +100%)
    cA = Channel(youtube_channel_id="UC_COMP_A", title="Channel A", sort_order=0)
    db.add(cA)
    db.flush()

    hA1 = ChannelStatsHistory(
        channel_id=cA.id,
        subscriber_count=100,
        view_count=1000,
        recorded_at=datetime(2026, 7, 1)
    )
    hA2 = ChannelStatsHistory(
        channel_id=cA.id,
        subscriber_count=150,
        view_count=2000,
        recorded_at=datetime(2026, 7, 2)
    )
    db.add_all([hA1, hA2])

    # チャンネルB (基準日: 1000人, 10,000回 ➔ 翌日: 1100人, 11,000回 ➔ +10%, +10%)
    cB = Channel(youtube_channel_id="UC_COMP_B", title="Channel B", sort_order=1)
    db.add(cB)
    db.flush()

    hB1 = ChannelStatsHistory(
        channel_id=cB.id,
        subscriber_count=1000,
        view_count=10000,
        recorded_at=datetime(2026, 7, 1)
    )
    hB2 = ChannelStatsHistory(
        channel_id=cB.id,
        subscriber_count=1100,
        view_count=11000,
        recorded_at=datetime(2026, 7, 2)
    )
    db.add_all([hB1, hB2])

    # チャンネルC (履歴なし)
    cC = Channel(youtube_channel_id="UC_COMP_C", title="Channel C", sort_order=2)
    db.add(cC)
    db.commit()

    # APIリクエスト
    response = client.get("/api/channels/comparison")
    assert response.status_code == 200

    data = response.json()
    assert "channels" in data
    assert "timeline" in data
    assert len(data["channels"]) == 3

    # チャンネルCの has_history が False であることを検証
    c_info = next(c for c in data["channels"] if c["id"] == cC.id)
    assert c_info["has_history"] is False

    # タイムラインデータの長さ (2日分)
    timeline = data["timeline"]
    assert len(timeline) == 2

    # Day 1 (2026/07/01): 両者とも 0% 基準
    day1 = timeline[0]
    assert day1["date"] == "2026/07/01"
    assert day1[f"sub_growth_{cA.id}"] == 0.0
    assert day1[f"view_growth_{cA.id}"] == 0.0

    # Day 2 (2026/07/02): Aは +50% / +100%、Bは +10% / +10%
    day2 = timeline[1]
    assert day2["date"] == "2026/07/02"
    assert day2[f"sub_growth_{cA.id}"] == 50.0
    assert day2[f"view_growth_{cA.id}"] == 100.0
    assert day2[f"sub_growth_{cB.id}"] == 10.0
    assert day2[f"view_growth_{cB.id}"] == 10.0

def test_get_channels_comparison_zero_division_safety(client, db):
    """
    基準日の数値が 0 (subscriber_count=0) の場合に ZeroDivisionError が出ず、
    0.0% として安全に処理されるかを検証。
    """
    c = Channel(youtube_channel_id="UC_ZERO", title="Zero Channel", sort_order=0)
    db.add(c)
    db.flush()

    h1 = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=0,
        view_count=0,
        recorded_at=datetime(2026, 7, 1)
    )
    h2 = ChannelStatsHistory(
        channel_id=c.id,
        subscriber_count=10,
        view_count=100,
        recorded_at=datetime(2026, 7, 2)
    )
    db.add_all([h1, h2])
    db.commit()

    response = client.get("/api/channels/comparison")
    assert response.status_code == 200

    data = response.json()
    timeline = data["timeline"]
    assert len(timeline) == 2
    # 0除算例外が起きず 0.0% にフォールバックされていること
    assert timeline[1][f"sub_growth_{c.id}"] == 0.0
    assert timeline[1][f"view_growth_{c.id}"] == 0.0
