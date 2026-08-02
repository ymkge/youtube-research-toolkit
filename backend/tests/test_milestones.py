import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_channel_milestones_endpoint():
    """/api/channels/milestones エンドポイントの基本動作をテスト"""
    response = client.get("/api/channels/milestones")
    assert response.status_code == 200
    data = response.json()
    assert "total_channels" in data
    assert "milestones" in data
    assert isinstance(data["milestones"], list)

    if len(data["milestones"]) > 0:
        item = data["milestones"][0]
        assert "channel_id" in item
        assert "title" in item
        assert "current_subscribers" in item
        assert "is_1k_before_tracking" in item
