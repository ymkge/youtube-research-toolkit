from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import inspect, text

from app.db.session import engine, Base, SessionLocal
from app.api.endpoints.channels import router as channels_router
# app.models を読み込ませることで、Base にモデルスキーマをバインドし、テーブルを自動生成する
import app.models

# 環境変数の読み込み
load_dotenv()

# アプリケーション起動時にDBテーブルを自動作成 (SQLite用)
Base.metadata.create_all(bind=engine)

# 既存データ保護：country カラムがなければ自動追加するマイグレーションロジック
def add_country_column_if_not_exists():
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('channels')]
        if 'country' not in columns:
            print("Migration: Adding 'country' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN country VARCHAR"))
            db.commit()
            print("Migration: 'country' column added successfully.")
    except Exception as e:
        print(f"Migration warning: {e}")
        db.rollback()
    finally:
        db.close()

# 既存の country が NULL のチャンネルに対して YouTube API から再フェッチして補完するデータパッチ
def populate_missing_countries():
    from app.models.channel import Channel
    from app.services.youtube import youtube_service
    
    db = SessionLocal()
    try:
        # country が NULL のチャンネルを検索
        missing_channels = db.query(Channel).filter(Channel.country == None).all()
        if missing_channels:
            print(f"Data Patch: Found {len(missing_channels)} channels missing country info. Fetching from API...")
            for channel in missing_channels:
                try:
                    if youtube_service.is_configured():
                        info = youtube_service.get_channel_info(channel.youtube_channel_id)
                        country = info.get("country")
                        # API側で国が未設定の場合は 'UNKNOWN' をセットして重複フェッチを回避
                        channel.country = country if country else "UNKNOWN"
                        db.add(channel)
                        print(f"Updated country for channel '{channel.title}': {channel.country}")
                except Exception as e:
                    print(f"Failed to fetch country for {channel.title}: {e}")
            db.commit()
            print("Data Patch: Missing countries populated successfully.")
    except Exception as e:
        print(f"Data Patch warning: {e}")
        db.rollback()
    finally:
        db.close()

add_country_column_if_not_exists()
populate_missing_countries()

app = FastAPI(
    title="YouTube Research Toolkit API",
    description="YouTube競合分析およびポジショニング分析用APIサービス",
    version="1.0.0"
)

# CORS設定
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(channels_router, prefix="/api/channels", tags=["channels"])

@app.get("/")
def read_root():
    return {"message": "Welcome to YouTube Research Toolkit API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
