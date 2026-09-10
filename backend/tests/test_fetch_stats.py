import os
import json
import pytest
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.scripts.fetch_stats import get_stat_value, run_json_mode, run_sync_json_mode
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory
from app.models.video import Video

def test_get_stat_value_normal_and_fallback():
    item1 = {"subscriber_count": 100, "view_count": 500, "video_count": 10}
    assert get_stat_value(item1, "view_count", "views") == 500
    assert get_stat_value(item1, "video_count", "videos") == 10

    # Test fallback keys
    item2 = {"subscribers": 200, "views": 1000, "videos": 20}
    assert get_stat_value(item2, "subscriber_count", "subscribers") == 200
    assert get_stat_value(item2, "view_count", "views") == 1000
    assert get_stat_value(item2, "video_count", "videos") == 20

    # Test missing / None
    item3 = {}
    assert get_stat_value(item3, "view_count", "views", 0) == 0

def test_run_sync_json_mode_dual_max_guard(db: Session, tmp_path, monkeypatch):
    c = Channel(
        youtube_channel_id="UC_TEST_GUARD",
        title="Guard Test Channel",
        subscriber_count=100,
        view_count=5000,
        video_count=10
    )
    db.add(c)
    db.commit()

    # Add videos to DB
    v1 = Video(channel_id=c.id, youtube_video_id="v_g1", title="V1", view_count=3000, published_at=datetime.utcnow())
    v2 = Video(channel_id=c.id, youtube_video_id="v_g2", title="V2", view_count=4000, published_at=datetime.utcnow())
    db.add_all([v1, v2])
    db.commit()

    # Create dummy JSON history with lagging stats for latest entry
    history_data = [
        {"date": "2026-09-07", "subscribers": 100, "views": 6500, "videos": 10},
        {"date": "2026-09-08", "subscriber_count": 100, "view_count": 2000, "video_count": 5} # Lagging!
    ]

    history_dir = tmp_path / "history"
    history_dir.mkdir()
    json_file = history_dir / "UC_TEST_GUARD.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f)

    monkeypatch.setattr("app.scripts.fetch_stats.HISTORY_DIR", str(history_dir))

    run_sync_json_mode(db_session=db)

    # Check 09/08 DB history record: should NOT drop to 2000, should be guarded by max(2000, 6500, SUM(7000)) -> 7000
    h_0908 = db.query(ChannelStatsHistory).filter(
        ChannelStatsHistory.channel_id == c.id,
        ChannelStatsHistory.recorded_at == date(2026, 9, 8)
    ).first()

    assert h_0908 is not None
    assert h_0908.view_count >= 7000
    assert h_0908.video_count >= 10

def test_run_json_mode_anomaly_separation(tmp_path, monkeypatch):
    """
    再生数減少は CRITICAL ANOMALY として検知され、
    動画数減少のみ（再生数増加）は検知カウントに含まれないことを検証。
    """
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    monkeypatch.setattr("app.scripts.fetch_stats.HISTORY_DIR", str(history_dir))

    # Pre-populate history for 2 channels
    # Channel 1: prev views 10,000, vids 10
    ch1_file = history_dir / "UC_ANOMALY_CH1.json"
    with open(ch1_file, "w", encoding="utf-8") as f:
        json.dump([{"date": "2026-09-09", "view_count": 10000, "video_count": 10, "subscriber_count": 100}], f)

    # Channel 2: prev views 20,000, vids 20
    ch2_file = history_dir / "UC_ANOMALY_CH2.json"
    with open(ch2_file, "w", encoding="utf-8") as f:
        json.dump([{"date": "2026-09-09", "view_count": 20000, "video_count": 20, "subscriber_count": 200}], f)

    # Mock batch fetch:
    # CH1 has lagging views: 8,000 (< 10,000) -> CRITICAL ANOMALY
    # CH2 has decreased vids: 19 (< 20), but views increased: 21,000 (> 20,000) -> NOTICE ONLY
    def mock_get_batch(self, cids, handles=None):
        return {
            "UC_ANOMALY_CH1": {"subscriber_count": 100, "view_count": 8000, "video_count": 10},
            "UC_ANOMALY_CH2": {"subscriber_count": 200, "view_count": 21000, "video_count": 19}
        }
    monkeypatch.setattr("app.services.youtube.YouTubeService.get_channels_info_batch", mock_get_batch)

    # Disable db read in test
    monkeypatch.setattr("app.scripts.fetch_stats.SessionLocal", lambda: None)

    github_output_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output_file))

    # Run without exit_on_anomaly
    run_json_mode(exit_on_anomaly=False)

    # GITHUB_OUTPUT should record anomaly_detected=true and anomaly_count=1 (only CH1, not CH2)
    assert github_output_file.exists()
    content = github_output_file.read_text(encoding="utf-8")
    assert "anomaly_detected=true" in content
    assert "anomaly_count=1" in content

    # Check CH1 guarded views
    with open(ch1_file, "r") as f:
        ch1_res = json.load(f)
        assert ch1_res[-1]["view_count"] == 10000  # Guarded from 8,000 to 10,000

    # Check CH2 guarded views and vids
    with open(ch2_file, "r") as f:
        ch2_res = json.load(f)
        assert ch2_res[-1]["view_count"] == 21000  # Increased
        assert ch2_res[-1]["video_count"] == 20   # Guarded from 19 to 20
