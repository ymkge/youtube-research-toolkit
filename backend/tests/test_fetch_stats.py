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
