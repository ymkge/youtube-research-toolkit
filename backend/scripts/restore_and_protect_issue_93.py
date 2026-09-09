import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    import dotenv
    env_path = os.path.join(backend_dir, ".env")
    if os.path.exists(env_path):
        dotenv.load_dotenv(env_path)
except Exception:
    pass
from sqlalchemy import text
from app.core.backup import restore_db_from_backup
from app.db.session import SessionLocal
from app.models.channel import Channel
from app.models.video import Video
from app.services.youtube import youtube_service
from app.api.endpoints.channels import sync_channel_videos, sync_parent_channel_stats
from app.scripts.fetch_stats import run_json_mode, run_sync_json_mode

BACKUP_FILE = os.path.join(backend_dir, "data", "backups", "youtube_research_backup_20260908_234858.db")
HISTORY_DIR = os.path.join(backend_dir, "data", "history")

def run_restore_and_protect():
    print("=== Step 1: Restoring SQLite DB from 2026-09-08 23:48:58 Backup ===")
    if not os.path.exists(BACKUP_FILE):
        raise FileNotFoundError(f"Backup file not found at: {BACKUP_FILE}")
        
    success = restore_db_from_backup(BACKUP_FILE)
    if not success:
        raise RuntimeError("Failed to restore DB from backup!")
    print("-> DB Restoration from 09/08 backup completed successfully.")

    print("\n=== Step 2: Synchronous Video Synchronization for Today ===")
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        print(f"Synchronizing video metadata for {len(channels)} channels...")
        for c in channels:
            try:
                if youtube_service.is_configured():
                    info = youtube_service.get_channel_info(c.youtube_channel_id)
                    uploads_playlist_id = info.get("uploads_playlist_id")
                    if uploads_playlist_id:
                        sync_channel_videos(db, c, uploads_playlist_id, import_limit=100)
                        db.commit()
            except Exception as ex:
                db.rollback()
                print(f"Video sync warning for {c.title}: {ex}")
    finally:
        db.close()
    print("-> Video Metadata Sync completed.")

    print("\n=== Step 3: Generating Guarded 2026-09-09 JSON Stats ===")
    run_json_mode(exit_on_anomaly=False)

    print("\n=== Step 4: Syncing Guarded JSON Stats into SQLite DB ===")
    run_sync_json_mode()

    print("\n=== Step 5: Asserting 100% Monotonic Non-Decreasing History across All Channels ===")
    db = SessionLocal()
    assertion_passed = True
    total_checked = 0
    try:
        channels = db.query(Channel).all()
        for c in channels:
            records = db.execute(text("SELECT recorded_at, view_count, video_count FROM channel_stats_history WHERE channel_id = :cid ORDER BY recorded_at"), {"cid": c.id}).fetchall()
            
            prev_v = 0
            prev_cnt = 0
            for r_date, r_v, r_cnt in records:
                total_checked += 1
                if r_v < prev_v:
                    print(f"❌ ASSERTION FAILURE for '{c.title}' on {r_date}: views decreased ({r_v:,} < prev {prev_v:,})")
                    assertion_passed = False
                if r_cnt < prev_cnt:
                    print(f"❌ ASSERTION FAILURE for '{c.title}' on {r_date}: vids decreased ({r_cnt} < prev {prev_cnt})")
                    assertion_passed = False
                prev_v = r_v
                prev_cnt = r_cnt
                
        if assertion_passed:
            print(f"✅ PERFECT! All {total_checked} history records across all {len(channels)} channels passed monotonic non-decreasing assertion check!")
        else:
            raise ValueError("Data assertion check failed! Some records decreased.")
    finally:
        db.close()

if __name__ == "__main__":
    run_restore_and_protect()
