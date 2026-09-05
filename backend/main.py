from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os

from app.db.session import engine, Base, SessionLocal
from app.api.endpoints.channels import router as channels_router
from app.api.endpoints.comparison import router as comparison_router

# app.models を読み込ませることで、Base にモデルスキーマをバインドし、テーブルを自動生成する
import app.models

# 環境変数の読み込み
load_dotenv()

# アプリケーション起動時にDBテーブルを自動作成 (SQLite用)
Base.metadata.create_all(bind=engine)

# 既存データ保護：必要なカラムがなければ自動追加するマイグレーションロジック
def run_migrations():
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('channels')]
        
        # country カラムの追加
        if 'country' not in columns:
            print("Migration: Adding 'country' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN country VARCHAR"))
            db.commit()
            print("Migration: 'country' column added successfully.")
            
        # sort_order カラムの追加
        if 'sort_order' not in columns:
            print("Migration: Adding 'sort_order' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN sort_order INTEGER DEFAULT 0"))
            db.commit()
            print("Migration: 'sort_order' column added successfully.")
            
        # is_pinned カラムの追加
        if 'is_pinned' not in columns:
            print("Migration: Adding 'is_pinned' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN is_pinned BOOLEAN DEFAULT 0"))
            db.commit()
            print("Migration: 'is_pinned' column added successfully.")
            
        # ai_analysis カラムの追加
        if 'ai_analysis' not in columns:
            print("Migration: Adding 'ai_analysis' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN ai_analysis TEXT"))
            db.commit()
            print("Migration: 'ai_analysis' column added successfully.")

        # ai_analysis_generated_at カラムの追加
        if 'ai_analysis_generated_at' not in columns:
            print("Migration: Adding 'ai_analysis_generated_at' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN ai_analysis_generated_at DATETIME"))
            db.commit()
            print("Migration: 'ai_analysis_generated_at' column added successfully.")

        # is_own_channel カラムの追加
        if 'is_own_channel' not in columns:
            print("Migration: Adding 'is_own_channel' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN is_own_channel BOOLEAN DEFAULT 0"))
            db.commit()
            print("Migration: 'is_own_channel' column added successfully.")

        # videos_synced_at カラムの追加
        if 'videos_synced_at' not in columns:
            print("Migration: Adding 'videos_synced_at' column to 'channels' table...")
            db.execute(text("ALTER TABLE channels ADD COLUMN videos_synced_at DATETIME"))
            db.commit()
            print("Migration: 'videos_synced_at' column added successfully.")
            
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

run_migrations()
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
app.include_router(comparison_router, prefix="/api/channels", tags=["comparison"])

@app.get("/")
def read_root():
    return {"message": "Welcome to YouTube Research Toolkit API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

async def auto_sync_videos_background():
    """
    起動後にバックグラウンドで全チャンネルの動画データを YouTube API から非同期に同期します。
    API 制限 (Quota) 回避のため、動画が最後に同期されてから (videos_synced_at) 12時間以上経過したチャンネルのみ同期。
    """
    import asyncio
    import datetime
    from app.models.channel import Channel
    from app.services.youtube import youtube_service
    from app.api.endpoints.channels import sync_channel_videos
    
    print("Auto-Sync: Background video synchronization task started.")
    await asyncio.sleep(5)  # サーバー起動完了を待つディレイ

    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        now = datetime.datetime.utcnow()
        threshold = now - datetime.timedelta(hours=12)
        
        for channel in channels:
            # 動画専用の最終同期日時 (videos_synced_at) が 12時間以上古い場合のみ実行
            if not channel.videos_synced_at or channel.videos_synced_at < threshold:
                print(f"Auto-Sync: Automatically synchronizing videos for channel '{channel.title}'...")
                try:
                    if youtube_service.is_configured():
                        info = youtube_service.get_channel_info(channel.youtube_channel_id)
                        uploads_playlist_id = info.get("uploads_playlist_id")
                        
                        if uploads_playlist_id:
                            # 最新100件の動画を非同期マージ
                            sync_channel_videos(db, channel, uploads_playlist_id, import_limit=100)
                            db.commit()
                            print(f"Auto-Sync: Successfully synchronized videos for '{channel.title}'.")
                except Exception as ex:
                    db.rollback()
                    print(f"Auto-Sync: Failed to synchronize videos for '{channel.title}': {ex}")
                
                # APIクォータ保護のため、1チャンネルごとに3秒待機
                await asyncio.sleep(3)
    except Exception as e:
        print(f"Auto-Sync: Background task encountered error: {e}")
    finally:
        db.close()
        print("Auto-Sync: Background video synchronization task completed.")

def ensure_db_migrations():
    """SQLite DB に新カラム (is_short, is_live) が無ければ自動で追加するマイグレーション関数"""
    import sqlite3
    from app.core.config import settings
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            cols = [row[1] for row in c.execute("PRAGMA table_info(videos)").fetchall()]
            if "is_short" not in cols:
                c.execute("ALTER TABLE videos ADD COLUMN is_short BOOLEAN DEFAULT 0")
            if "is_live" not in cols:
                c.execute("ALTER TABLE videos ADD COLUMN is_live BOOLEAN DEFAULT 0")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Migration warning: {e}")

@app.on_event("startup")
def startup_event():
    """
    サーバー起動時に DB マイグレーションと JSON 履歴ファイル（GitHub Actionsからプッシュされた時系列統計）を SQLite DB にマージします。
    また、バックグラウンドで動画データの自動同期タスクを開始します。
    """
    import os
    if os.getenv("TESTING") == "True":
        print("Startup: Running in test mode. Skipping JSON sync and background tasks.")
        return

    ensure_db_migrations()

    # DB 自動バックアップ ＆ 7日ローテーション処理
    try:
        from app.core.backup import create_db_backup, cleanup_old_backups
        create_db_backup()
        cleanup_old_backups(retention_days=7)
    except Exception as e:
        print(f"Startup warning (DB Backup failed): {e}")

    try:
        from app.scripts.fix_video_types import run_fix_video_types
        run_fix_video_types()
    except Exception as e:
        print(f"Startup warning (Video Types Backfill failed): {e}")

    import asyncio
    from app.scripts.fetch_stats import run_sync_json_mode
    print("Startup: Synchronizing JSON stats history files into SQLite database...")
    try:
        run_sync_json_mode()
        print("Startup: Synchronization completed.")
    except Exception as e:
        print(f"Startup warning (JSON Sync failed): {e}")

    # 本日分のデータに未取得が存在する場合の全自動レスキュー補テン
    try:
        ensure_today_stats_rescued()
    except Exception as e:
        print(f"Startup warning (Rescue failed): {e}")

    # バックグラウンドタスクとして非同期起動（ノンブロッキング）
    asyncio.create_task(auto_sync_videos_background())

def ensure_today_stats_rescued():
    """
    サーバー起動時、本日(JST)の時系列統計が未取得のチャンネルが存在する場合、
    自動的にYouTube APIから最新統計を補填取得してSQLite DBおよびJSON履歴の両方に即座に補正保存します。
    """
    import datetime
    from app.models.channel import Channel
    from app.models.channel_stats_history import ChannelStatsHistory
    from app.services.youtube import youtube_service
    if not youtube_service.is_configured():
        return

    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        JST = datetime.timezone(datetime.timedelta(hours=+9))
        today_date = datetime.datetime.now(JST).date()
        today_str = today_date.isoformat()

        all_channels = db.query(Channel).all()
        missing_channels = []
        for channel in all_channels:
            hist = db.query(ChannelStatsHistory).filter(
                ChannelStatsHistory.channel_id == channel.id,
                ChannelStatsHistory.recorded_at == today_date
            ).first()
            if not hist:
                missing_channels.append(channel)

        if not missing_channels:
            print("Startup Rescue: All channels already updated for today. No rescue needed.")
            return

        print(f"Startup Rescue: Found {len(missing_channels)} missing channels for today ({today_str}). Executing auto-rescue fetch...")

        missing_cids = [c.youtube_channel_id for c in missing_channels]
        channel_handles_map = {c.youtube_channel_id: c.custom_url for c in missing_channels if c.custom_url}
        batch_stats = youtube_service.get_channels_info_batch(missing_cids, channel_handles_map)

        import os, json
        history_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "history"))
        os.makedirs(history_dir, exist_ok=True)

        for channel in missing_channels:
            stats = batch_stats.get(channel.youtube_channel_id)
            if not stats:
                try:
                    stats = youtube_service.get_channel_info(channel.youtube_channel_id)
                except Exception as ex:
                    if channel.custom_url and channel.custom_url.startswith("@"):
                        try:
                            stats = youtube_service.get_channel_info(channel.custom_url)
                        except Exception:
                            stats = None
                    else:
                        stats = None

            if not stats:
                print(f"Startup Rescue failed for {channel.title}")
                continue

            sub_count = stats["subscriber_count"]
            view_count = stats["view_count"]
            video_count = stats["video_count"]

            channel.subscriber_count = sub_count
            channel.view_count = view_count
            channel.video_count = video_count

            new_record = ChannelStatsHistory(
                channel_id=channel.id,
                subscriber_count=sub_count,
                view_count=view_count,
                video_count=video_count,
                recorded_at=today_date
            )
            db.add(new_record)
            print(f"Startup Rescue: Successfully rescued and updated '{channel.title}' in DB for {today_str}.")

        db.commit()
    except Exception as e:
        print(f"Startup Rescue warning: {e}")
    finally:
        db.close()
