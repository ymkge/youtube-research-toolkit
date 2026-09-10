import os
import sys
import argparse
import json
import datetime
from datetime import timezone, timedelta
from sqlalchemy.orm import Session

# 日本時間 (JST: UTC+9) の定義
JST = timezone(timedelta(hours=+9))

# backend ディレクトリをインポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

try:
    import dotenv
    env_path = os.path.join(backend_dir, ".env")
    if os.path.exists(env_path):
        dotenv.load_dotenv(env_path)
except Exception:
    pass

from app.db.session import SessionLocal, engine
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory
from app.services.youtube import youtube_service

HISTORY_DIR = os.path.join(backend_dir, "data", "history")

def ensure_history_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)

def get_stat_value(item: dict, primary_key: str, fallback_key: str, default: int = 0) -> int:
    """
    JSON履歴項目のキー表記揺れ (subscriber_count vs subscribers, view_count vs views, video_count vs videos) を
    安全に吸収して整数値を返します。
    """
    if not isinstance(item, dict):
        return default
    val = item.get(primary_key)
    if val is None:
        val = item.get(fallback_key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def fetch_channel_api_stats(youtube_channel_id: str):
    """
    YouTube APIからチャンネルの最新統計を取得します。
    """
    if not youtube_service.is_configured():
        raise RuntimeError("YouTube API Key is not configured. Set YOUTUBE_API_KEY environment variable.")
    
    info = youtube_service.get_channel_info(youtube_channel_id)
    return {
        "subscriber_count": info["subscriber_count"],
        "view_count": info["view_count"],
        "video_count": info["video_count"],
        "title": info["title"]
    }

def run_db_mode():
    """
    --db オプション: SQLite DBへ直接統計を記録（ローカルPCでのバッチ手動実行用）
    """
    print("Running in DB mode (direct database update)...")
    db: Session = SessionLocal()
    try:
        channels = db.query(Channel).all()
        if not channels:
            print("No channels registered in the database.")
            return

        today = datetime.datetime.now(JST).date()
        for channel in channels:
            try:
                print(f"Fetching stats for: {channel.title} ({channel.youtube_channel_id})")
                stats = fetch_channel_api_stats(channel.youtube_channel_id)
                
                channel.subscriber_count = stats["subscriber_count"]
                channel.view_count = stats["view_count"]
                channel.video_count = stats["video_count"]
                channel.updated_at = datetime.datetime.utcnow()

                history_record = db.query(ChannelStatsHistory).filter(
                    ChannelStatsHistory.channel_id == channel.id,
                    ChannelStatsHistory.recorded_at == today
                ).first()

                if history_record:
                    history_record.subscriber_count = stats["subscriber_count"]
                    history_record.view_count = stats["view_count"]
                    history_record.video_count = stats["video_count"]
                    print(f"-> Updated existing history record for {today}")
                else:
                    new_record = ChannelStatsHistory(
                        channel_id=channel.id,
                        subscriber_count=stats["subscriber_count"],
                        view_count=stats["view_count"],
                        video_count=stats["video_count"],
                        recorded_at=today
                    )
                    db.add(new_record)
                    print(f"-> Created new history record for {today}")
                
            except Exception as e:
                print(f"Error fetching stats for channel {channel.youtube_channel_id}: {e}")

        db.commit()
        print("Database update completed successfully.")
    finally:
        db.close()

def run_json_mode(exit_on_anomaly: bool = False):
    """
    --json オプション: 日次のJSON履歴ファイルを作成・追記（GitHub Actions用）
    Max Guard による単調非減少保護および API アノマリー検出アラートを備えます。
    """
    print("Running in JSON mode (writing to history files with Dual Max Guard & Anomaly Detection)...")
    ensure_history_dir()

    channels_to_fetch = []

    if os.path.exists(HISTORY_DIR):
        history_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
        for fname in history_files:
            cid = fname.replace(".json", "").strip()
            if cid:
                channels_to_fetch.append((cid, cid))
        if channels_to_fetch:
            print(f"Target Discovery: Found {len(channels_to_fetch)} channel history files in {HISTORY_DIR}.")

    try:
        db: Session = SessionLocal()
        db_channels = db.query(Channel).all()
        existing_ids = {item[0] for item in channels_to_fetch}
        for c in db_channels:
            if c.youtube_channel_id not in existing_ids:
                channels_to_fetch.append((c.youtube_channel_id, c.title or c.youtube_channel_id))
        db.close()
    except Exception as e:
        print(f"Database read skipped: {e}")

    env_channels = os.environ.get("MONITOR_CHANNELS", "")
    if env_channels:
        existing_ids = {item[0] for item in channels_to_fetch}
        for item in env_channels.split(","):
            cid = item.strip()
            if cid and cid not in existing_ids:
                channels_to_fetch.append((cid, cid))

    if not channels_to_fetch:
        print("No channels target found for JSON sync.")
        return

    today_str = datetime.datetime.now(JST).date().isoformat() # YYYY-MM-DD
    print(f"Starting JSON sync for {len(channels_to_fetch)} target channels for date: {today_str}...")

    channel_handles_map = {
        "UCa2jEvNQVeCS7Ual-PRSjjQ": "@KokoroMusicRoom",
        "UCrILWnc9LGNyYOCkBhOLIIQ": "@doctorfocusbgm"
    }
    try:
        db: Session = SessionLocal()
        for c in db.query(Channel).all():
            if c.custom_url:
                channel_handles_map[c.youtube_channel_id] = c.custom_url
        db.close()
    except Exception:
        pass

    target_cids = [cid for cid, title in channels_to_fetch]
    print(f"Executing Batch API Fetch (hl=ja) for {len(target_cids)} channels...")
    batch_stats_map = youtube_service.get_channels_info_batch(target_cids, channel_handles_map)

    success_count = 0
    error_count = 0
    anomalies_detected_count = 0
    anomalous_channels = []

    for youtube_channel_id, title in channels_to_fetch:
        try:
            stats = batch_stats_map.get(youtube_channel_id)
            if not stats:
                print(f"Warning: No batch stats retrieved for {youtube_channel_id} ({title}). Trying individual fallback...")
                stats = fetch_channel_api_stats(youtube_channel_id)

            file_path = os.path.join(HISTORY_DIR, f"{youtube_channel_id}.json")
            
            history_data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except Exception as ex:
                    print(f"Warning: Failed to parse existing JSON file {file_path}. Starting fresh: {ex}")

            past_entries = [item for item in history_data if item.get("date") != today_str]
            past_entries.sort(key=lambda x: x.get("date", ""))
            prev_item = past_entries[-1] if past_entries else {}

            prev_subs = get_stat_value(prev_item, "subscriber_count", "subscribers", 0)
            prev_views = get_stat_value(prev_item, "view_count", "views", 0)
            prev_vids = get_stat_value(prev_item, "video_count", "videos", 0)

            api_subs = stats["subscriber_count"]
            api_views = stats["view_count"]
            api_vids = stats["video_count"]

            view_dropped = (prev_views > 0 and api_views < prev_views)
            vid_dropped = (prev_vids > 0 and api_vids < prev_vids)

            if view_dropped:
                print(f"[CRITICAL ANOMALY] Channel '{title}' ({youtube_channel_id}): YouTube API returned lagging views "
                      f"({api_views:,} < prev: {prev_views:,}). Max Guard activated.")
                anomalies_detected_count += 1
                anomalous_channels.append({
                    "id": youtube_channel_id,
                    "title": title,
                    "api_views": api_views,
                    "prev_views": prev_views,
                    "api_vids": api_vids,
                    "prev_vids": prev_vids
                })
            elif vid_dropped:
                print(f"[NOTICE] Channel '{title}' ({youtube_channel_id}): Video count decreased "
                      f"({api_vids} < prev: {prev_vids}, videos deleted/privated). Max Guard activated.")

            guarded_subs = max(api_subs, prev_subs)
            guarded_views = max(api_views, prev_views)
            guarded_vids = max(api_vids, prev_vids)

            history_data = past_entries
            history_data.append({
                "date": today_str,
                "subscriber_count": guarded_subs,
                "view_count": guarded_views,
                "video_count": guarded_vids,
                "subscribers": guarded_subs,
                "views": guarded_views,
                "videos": guarded_vids
            })

            history_data.sort(key=lambda x: x.get("date", ""))

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            print(f"-> Successfully saved guarded stats to {file_path}")
            success_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error saving JSON stats for {youtube_channel_id}: {e}")

    print("\n=======================================================")
    print(f"JSON History Update Summary ({today_str}):")
    print(f"  Success: {success_count} / {len(channels_to_fetch)}")
    print(f"  Errors:  {error_count}")
    print(f"  API Anomalies Guarded: {anomalies_detected_count}")
    if anomalous_channels:
        print("  Anomalous Channels List:")
        for ac in anomalous_channels:
            print(f"    - {ac['title']} ({ac['id']}): API views={ac['api_views']:,} (guarded to {ac['prev_views']:,})")
    print("=======================================================\n")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"anomaly_detected={'true' if anomalies_detected_count > 0 else 'false'}\n")
                f.write(f"anomaly_count={anomalies_detected_count}\n")
        except Exception as ex:
            print(f"Warning: Failed to write to GITHUB_OUTPUT: {ex}")

    if exit_on_anomaly and anomalies_detected_count > 0:
        print(f"Exit Warning: {anomalies_detected_count} API anomalies detected. Raising exit code 1 for GitHub Actions Gmail Alert.")
        sys.exit(1)

def run_sync_json_mode(db_session: Session = None):
    """
    --sync-json オプション: JSON履歴ファイル群を SQLite DB へインポート・マージ
    過去日付は前日比単調非減少 Guard、最新日は SUM(Video) 含む 3重防護で適用。
    """
    print("Running in Sync-JSON mode (importing JSON files to SQLite with Dual Max Guard)...")
    if not os.path.exists(HISTORY_DIR):
        print(f"History directory {HISTORY_DIR} does not exist. Nothing to sync.")
        return

    db = db_session if db_session else SessionLocal()
    try:
        json_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
        if not json_files:
            print("No JSON history files found.")
            return

        for filename in json_files:
            youtube_channel_id = filename.replace(".json", "")
            
            channel = db.query(Channel).filter(Channel.youtube_channel_id == youtube_channel_id).first()
            if not channel:
                continue

            file_path = os.path.join(HISTORY_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception as e:
                print(f"Error reading JSON file {file_path}: {e}")
                continue

            print(f"Syncing stats history for channel: {channel.title} ({youtube_channel_id})")

            history_data.sort(key=lambda x: x.get("date", ""))
            latest_date_str = history_data[-1].get("date") if history_data else None

            cursor_v_sum = 0
            cursor_v_cnt = 0
            try:
                from app.models.video import Video
                v_stats = db.query(Video).filter(Video.channel_id == channel.id).all()
                if v_stats:
                    cursor_v_sum = sum(v.view_count or 0 for v in v_stats)
                    cursor_v_cnt = len(v_stats)
            except Exception:
                pass

            prev_db_views = 0
            prev_db_vids = 0

            for item in history_data:
                try:
                    date_str = item.get("date")
                    if not date_str:
                        continue
                    
                    recorded_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    item_subs = get_stat_value(item, "subscriber_count", "subscribers", 0)
                    item_views = get_stat_value(item, "view_count", "views", 0)
                    item_vids = get_stat_value(item, "video_count", "videos", 0)

                    if date_str == latest_date_str:
                        guarded_views = max(item_views, prev_db_views, cursor_v_sum)
                        guarded_vids = max(item_vids, prev_db_vids, cursor_v_cnt)
                    else:
                        guarded_views = max(item_views, prev_db_views)
                        guarded_vids = max(item_vids, prev_db_vids)
                        
                    guarded_subs = max(item_subs, 0)
                    
                    prev_db_views = guarded_views
                    prev_db_vids = guarded_vids

                    existing = db.query(ChannelStatsHistory).filter(
                        ChannelStatsHistory.channel_id == channel.id,
                        ChannelStatsHistory.recorded_at == recorded_date
                    ).first()

                    if existing:
                        if (existing.subscriber_count != guarded_subs or
                            existing.view_count != guarded_views or
                            existing.video_count != guarded_vids):
                            existing.subscriber_count = guarded_subs
                            existing.view_count = guarded_views
                            existing.video_count = guarded_vids
                            print(f"  -> Updated history for date: {date_str} (views: {guarded_views:,})")
                    else:
                        new_record = ChannelStatsHistory(
                            channel_id=channel.id,
                            subscriber_count=guarded_subs,
                            view_count=guarded_views,
                            video_count=guarded_vids,
                            recorded_at=recorded_date
                        )
                        db.add(new_record)
                        print(f"  -> Imported new history for date: {date_str} (views: {guarded_views:,})")

                except Exception as e:
                    print(f"Error processing item {item} for {youtube_channel_id}: {e}")

            from app.api.endpoints.channels import sync_parent_channel_stats
            sync_parent_channel_stats(db, channel.id)
            print(f"  -> Synchronized parent Channel stats for '{channel.title}' with latest history")

        db.commit()
        print("JSON stats history synchronization completed successfully.")
    finally:
        if not db_session:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Research Toolkit Stats Fetcher Batch")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--db", action="store_true", help="Fetch stats from API and write directly to SQLite DB")
    group.add_argument("--json", action="store_true", help="Fetch stats from API and write to daily JSON history files")
    group.add_argument("--sync-json", action="store_true", help="Import JSON history files into the SQLite DB")
    parser.add_argument("--exit-on-anomaly", action="store_true", help="Raise exit code 1 if API anomalies are detected (for GitHub Actions alert)")

    args = parser.parse_args()

    if args.db:
        run_db_mode()
    elif args.json:
        run_json_mode(exit_on_anomaly=args.exit_on_anomaly)
    elif args.sync_json:
        run_sync_json_mode()
