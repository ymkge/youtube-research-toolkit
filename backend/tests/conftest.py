import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import sys
import os

# テスト実行時のフラグを環境変数に設定
os.environ["TESTING"] = "True"

# backend ディレクトリを sys.path に追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.db.session import Base, get_db

# テスト用のインメモリ SQLite データベース
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """
    テストごとにクリーンなデータベース接続（セッション）を提供するフィクスチャ。
    テスト開始時にテーブルをすべて作成し、終了時に破棄します。
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI の TestClient を提供するフィクスチャ。
    エンドポイント内で使用される get_db 依存関係をインメモリDBにオーバーライドします。
    """
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
