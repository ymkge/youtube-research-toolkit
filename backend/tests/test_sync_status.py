import pytest
from fastapi.testclient import TestClient
from main import app
import datetime

client = TestClient(app)

def test_get_sync_status_endpoint():
    """/api/channels/sync-status エンドポイントの基本動作をテスト"""
    response = client.get("/api/channels/sync-status")
    assert response.status_code == 200
    data = response.json()
    assert "today" in data
    assert "total_channels" in data
    assert "updated_count" in data
    assert "missing_count" in data
    assert "is_all_updated" in data
    assert "missing_channels" in data
    assert isinstance(data["missing_channels"], list)
