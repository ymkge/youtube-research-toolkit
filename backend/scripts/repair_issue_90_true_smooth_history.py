import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, date, timedelta

DB_PATH = Path("backend/youtube_research.db")
HISTORY_DIR = Path("backend/data/history")

TODAY = date(2026, 9, 8)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Running True Smooth Growth Distribution Repair across All 33 Channels ===")

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
    
    parsed_vids = []
    for v in videos:
        pub_str = (v["published_at"] or "2026-01-01").split()[0]
        try:
            pub_date = datetime.strptime(pub_str, "%Y-%m-%d").date()
        except:
            pub_date = date(2026, 1, 1)
        parsed_vids.append({
            "views": v["view_count"] or 0,
            "pub_date": pub_date
        })
        
    # 2. Fetch history records ordered by date
    cursor.execute("SELECT id, recorded_at, view_count, subscriber_count, video_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at", (c_db_id,))
    history_records = cursor.fetchall()
    
    if not history_records:
        continue
        
    records_updated = 0
    updated_history_entries = []
    
    prev_views = 0
    prev_vids = 0
    
    for h in history_records:
        rec_str = h["recorded_at"]
        rec_date = datetime.strptime(rec_str, "%Y-%m-%d").date()
        
        # Calculate video count published on or before rec_date
        vids_up_to_date = [v for v in parsed_vids if v["pub_date"] <= rec_date]
        calc_vids = len(vids_up_to_date)
        
        # Calculate smooth spread view count
        smooth_views_sum = 0
        for v in parsed_vids:
            p_date = v["pub_date"]
            total_v = v["views"]
            if rec_date < p_date:
                contrib = 0
            elif rec_date >= TODAY:
                contrib = total_v
            else:
                total_days = max(1, (TODAY - p_date).days + 1)
                active_days = max(1, (rec_date - p_date).days + 1)
                ratio = min(1.0, (active_days / total_days) ** 0.6)
                contrib = int(total_v * ratio)
            smooth_views_sum += contrib
            
        # Enforce monotonic non-decreasing view count constraint
        final_views = max(smooth_views_sum, prev_views)
        final_vids = max(calc_vids, prev_vids)
        
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
            "date": rec_str,
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

# Update parent channel table with latest history record values
cursor.execute("SELECT id FROM channels")
channels_list = cursor.fetchall()

for c in channels_list:
    c_db_id = c["id"]
    cursor.execute("SELECT view_count, video_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at DESC LIMIT 1", (c_db_id,))
    latest = cursor.fetchone()
    if latest:
        cursor.execute("UPDATE channels SET view_count = ?, video_count = ? WHERE id = ?", (latest["view_count"], latest["video_count"], c_db_id))

conn.commit()
conn.close()

print(f"\n✅ True Smooth Growth Repair Complete!")
print(f"Total Repaired Channels: {repaired_channels_count} / {len(channels)}")
print(f"Total Repaired History Records: {total_history_records_repaired}")
