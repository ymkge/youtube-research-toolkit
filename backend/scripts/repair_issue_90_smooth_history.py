import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path("backend/youtube_research.db")
HISTORY_DIR = Path("backend/data/history")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Starting Historical Stats Smoothing Repair across All 33 Channels ===")

cursor.execute("SELECT id, youtube_channel_id, title FROM channels ORDER BY title")
channels = cursor.fetchall()

repaired_channels_count = 0
total_history_records_repaired = 0

for c in channels:
    c_db_id = c["id"]
    c_str_id = c["youtube_channel_id"]
    title = c["title"]
    
    # 1. Fetch all videos for this channel
    cursor.execute("SELECT youtube_video_id, title, view_count, published_at FROM videos WHERE channel_id = ?", (c_db_id,))
    videos = cursor.fetchall()
    
    # 2. Fetch history records ordered by date
    cursor.execute("SELECT id, recorded_at, view_count, subscriber_count, video_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at", (c_db_id,))
    history_records = cursor.fetchall()
    
    if not history_records:
        continue
        
    records_updated = 0
    updated_history_entries = []
    
    # We maintain monotonic non-decreasing view count constraint across history dates
    prev_views = 0
    prev_vids = 0
    
    for h in history_records:
        rec_date = h["recorded_at"]
        rec_end_ts = f"{rec_date} 23:59:59"
        
        # Videos published on or before rec_date
        vids_up_to_date = [v for v in videos if (v["published_at"] or "") <= rec_end_ts]
        calc_views = sum(v["view_count"] or 0 for v in vids_up_to_date)
        calc_vids = len(vids_up_to_date)
        
        # Enforce monotonic & non-destructive Max Guard
        final_views = max(h["view_count"], calc_views, prev_views)
        final_vids = max(h["video_count"], calc_vids, prev_vids)
        
        prev_views = final_views
        prev_vids = final_vids
        
        if final_views != h["view_count"] or final_vids != h["video_count"]:
            cursor.execute("""
                UPDATE channel_stats_history
                SET view_count = ?, video_count = ?
                WHERE id = ?
            """, (final_views, final_vids, h["id"]))
            records_updated += 1
            
        updated_history_entries.append({
            "date": rec_date,
            "subscribers": h["subscriber_count"],
            "views": final_views,
            "videos": final_vids
        })
        
    if records_updated > 0:
        repaired_channels_count += 1
        total_history_records_repaired += records_updated
        print(f"[REPAIRED] {title:<35} | {records_updated} history records updated")
        
    # Also update JSON history file if present
    json_path = HISTORY_DIR / f"{c_str_id}.json"
    if json_path.exists():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(updated_history_entries, f, ensure_ascii=False, indent=2)

conn.commit()

# Run parent channel stats sync to ensure channels table aligns with latest history record
cursor.execute("SELECT id, view_count, video_count FROM channels")
channels_list = cursor.fetchall()

for c in channels_list:
    c_db_id = c["id"]
    cursor.execute("SELECT recorded_at, view_count, video_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at DESC LIMIT 1", (c_db_id,))
    latest = cursor.fetchone()
    if latest:
        cursor.execute("UPDATE channels SET view_count = ?, video_count = ? WHERE id = ?", (latest["view_count"], latest["video_count"], c_db_id))

conn.commit()
conn.close()

print(f"\n✅ Historical Stats Smoothing Complete!")
print(f"Total Repaired Channels: {repaired_channels_count} / {len(channels)}")
print(f"Total Repaired History Records: {total_history_records_repaired}")
