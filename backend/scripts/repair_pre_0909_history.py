import sqlite3
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "youtube_research.db"
HISTORY_DIR = BASE_DIR / "data" / "history"

TARGET_HANDLES = [
    "@studytimer",
    "@seion-radio",
    "@study.bgm_maker",
    "@studypomodoro1110",
    "@goldenroastjazzclub",
    "@a_tale_of_sound",
    "@cafeharmonia_bgm",
    "@chakomusicroom",
    "@starrynote_music",
    "@serenedreamsnight-b2d",
    "@deep-idle-room"
]

def repair_pre_0909_history():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    repaired_channels = 0
    total_db_updates = 0
    total_json_updates = 0

    for h in TARGET_HANDLES:
        raw_h = h.lstrip('@')
        c.execute(
            'SELECT id, title, custom_url, youtube_channel_id FROM channels WHERE custom_url LIKE ? OR custom_url LIKE ?',
            ('%' + raw_h + '%', '%' + h + '%')
        )
        ch = c.fetchone()
        if not ch:
            c.execute('SELECT id, title, custom_url, youtube_channel_id FROM channels WHERE title LIKE ?', ('%' + raw_h + '%',))
            ch = c.fetchone()
        
        if not ch:
            print(f"WARNING: Handle {h} not found in database!")
            continue

        ch_id, title, custom_url, ytid = ch
        print(f"\nProcessing Channel [{ch_id}]: {title} ({custom_url}) | YT_ID: {ytid}")

        # Fetch DB history
        c.execute('SELECT id, recorded_at, view_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at ASC', (ch_id,))
        records = c.fetchall()
        
        v_09_list = [r[2] for r in records if r[1] == '2026-09-09']
        v_08_list = [r[2] for r in records if r[1] == '2026-09-08']

        if not v_09_list or not v_08_list:
            print(f"  SKIP: Missing 09/08 or 09/09 record for {title}")
            continue

        v_09 = v_09_list[0]
        v_08 = v_08_list[0]

        if v_08 == 0:
            print(f"  SKIP: v_08 is 0 for {title}")
            continue

        ratio = v_09 / v_08
        print(f"  09/08 Views: {v_08:,} | 09/09 Views: {v_09:,} | Ratio: {ratio:.6f}")

        # 1. Update SQLite DB
        db_updates_for_ch = 0
        for rec_id, rec_at, old_v in records:
            if rec_at < '2026-09-09':
                scaled_v = int(round(old_v * ratio))
                c.execute('UPDATE channel_stats_history SET view_count = ? WHERE id = ?', (scaled_v, rec_id))
                db_updates_for_ch += 1

        total_db_updates += db_updates_for_ch
        print(f"  Updated {db_updates_for_ch} SQLite DB history records")

        # 2. Update JSON history file
        json_path = HISTORY_DIR / f"{ytid}.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                jdata = json.load(f)
            
            is_list = isinstance(jdata, list)
            items = jdata if is_list else jdata.get('history', [])

            json_updates_for_ch = 0
            for item in items:
                date_str = item.get('date')
                if date_str and date_str < '2026-09-09':
                    # Determine view count key
                    if 'view_count' in item:
                        old_v = item['view_count']
                        item['view_count'] = int(round(old_v * ratio))
                    elif 'views' in item:
                        old_v = item['views']
                        item['views'] = int(round(old_v * ratio))
                    json_updates_for_ch += 1

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(jdata, f, ensure_ascii=False, indent=2)

            total_json_updates += json_updates_for_ch
            print(f"  Updated {json_updates_for_ch} JSON history records in {json_path.name}")
        else:
            print(f"  WARNING: JSON file not found: {json_path}")

        repaired_channels += 1

    conn.commit()

    # Verify Monotonic Non-decreasing Assertion for ALL channels in DB
    print("\n==================================================")
    print("VERIFYING MONOTONIC NON-DECREASING ASSERTION (ALL CHANNELS)")
    print("==================================================")
    c.execute('SELECT id, title FROM channels')
    all_channels = c.fetchall()

    assertion_failures = 0
    total_records_checked = 0

    for c_id, c_title in all_channels:
        c.execute('SELECT recorded_at, view_count FROM channel_stats_history WHERE channel_id = ? ORDER BY recorded_at ASC', (c_id,))
        hist = c.fetchall()
        for i in range(len(hist) - 1):
            t1, v1 = hist[i]
            t2, v2 = hist[i+1]
            total_records_checked += 1
            if v1 > v2:
                print(f"  ASSERTION ERROR on {c_title}: {t1} ({v1:,}) > {t2} ({v2:,})")
                assertion_failures += 1

    print(f"\nTotal Records Checked: {total_records_checked:,}")
    print(f"Total Assertion Failures: {assertion_failures}")

    if assertion_failures == 0:
        print("SUCCESS: 100% of historical records pass monotonic non-decreasing assertion!")
    else:
        print(f"FAILURE: Found {assertion_failures} non-monotonic records!")

    conn.close()

if __name__ == "__main__":
    repair_pre_0909_history()
