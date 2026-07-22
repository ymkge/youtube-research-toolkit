import os
import sys
import argparse
import json
import datetime
from sqlalchemy.orm import Session

# backend ディレクトリをインポートパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app.db.session import SessionLocal, engine
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory
from app.services.youtube import youtube_service

HISTORY_DIR = os.path.join(backend_dir, "data", "history")

def ensure_history_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)

def fetch_channel_api_stats(youtube_channel_id: str):
    """
    YouTube APIからチャンネルの最新統計を取得します。
    """
    if not youtube_service.is_configured():
        raise RuntimeError("YouTube API Key is not configured. Set YOUTUBE_API_KEY environment variable.")
    
    # youtube_service.get_channel_info は内部で API を叩いてチャンネル情報を返します
    info = youtube_service.get_channel_info(youtube_channel_id)
    return {
        "subscriber_count": info["subscriber_count"],
        "view_count": info["view_count"],
        "video_count": info["video_count"],
        "title": info["title"] # ログ用
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

        today = datetime.date.today()
        for channel in channels:
            try:
                print(f"Fetching stats for: {channel.title} ({channel.youtube_channel_id})")
                stats = fetch_channel_api_stats(channel.youtube_channel_id)
                
                # 1. チャンネル親テーブルの最新情報を更新
                channel.subscriber_count = stats["subscriber_count"]
                channel.view_count = stats["view_count"]
                channel.video_count = stats["video_count"]
                channel.updated_at = datetime.datetime.utcnow()

                # 2. 履歴テーブルの更新または追加
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

def run_json_mode():
    """
    --json オプション: 日次のJSON履歴ファイルを作成・追記（GitHub Actions用）
    """
    print("Running in JSON mode (writing to history files)...")
    ensure_history_dir()

    # GitHub Actionsで実行する場合、SQLiteからではなくSecretsや設定ファイルから対象を特定する、
    # もしくはローカルSQLiteがある場合はそれから読み込みます。
    # どちらでも動作するように、SQLiteが存在する場合はDBから読み込み、
    # DBが無い場合でも環境変数や設定ファイルで動作するフォールバックを想定します。
    
    db: Session = SessionLocal()
    channels_to_fetch = []
    try:
        channels = db.query(Channel).all()
        for c in channels:
            channels_to_fetch.append((c.youtube_channel_id, c.title))
    except Exception as e:
        print(f"Database connection skipped or failed: {e}. Reading targets from config or environment...")
        # フォールバック: 環境変数 "MONITOR_CHANNELS" にカンマ区切りで ID リストがある場合
        env_channels = os.environ.get("MONITOR_CHANNELS", "")
        if env_channels:
            for item in env_channels.split(","):
                if item.strip():
                    channels_to_fetch.append((item.strip(), item.strip()))
    finally:
        db.close()

    if not channels_to_fetch:
        print("No channels target found for JSON sync.")
        return

    today_str = datetime.date.today().isoformat() # YYYY-MM-DD

    for youtube_channel_id, title in channels_to_fetch:
        try:
            print(f"Fetching stats for JSON: {title} ({youtube_channel_id})")
            stats = fetch_channel_api_stats(youtube_channel_id)

            file_path = os.path.join(HISTORY_DIR, f"{youtube_channel_id}.json")
            
            # 既存の履歴ファイルを読み込む
            history_data = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except Exception as ex:
                    print(f"Warning: Failed to parse existing JSON file {file_path}. Starting fresh: {ex}")

            # 同一日の重複レコードを削除（最新値へ上書きするため）
            history_data = [item for item in history_data if item.get("date") != today_str]

            # 今日のデータを追加
            history_data.append({
                "date": today_str,
                "subscriber_count": stats["subscriber_count"],
                "view_count": stats["view_count"],
                "video_count": stats["video_count"]
            })

            # 日付順にソートして保存
            history_data.sort(key=lambda x: x["date"])

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            
            print(f"-> Successfully saved to {file_path}")

        except Exception as e:
            print(f"Error saving JSON stats for {youtube_channel_id}: {e}")

    print("JSON history update completed.")

def run_sync_json_mode(db_session: Session = None):
    """
    --sync-json オプション: JSON履歴ファイル群を SQLite DB へインポート・マージ
    """
    print("Running in Sync-JSON mode (importing JSON files to SQLite)...")
    if not os.path.exists(HISTORY_DIR):
        print(f"History directory {HISTORY_DIR} does not exist. Nothing to sync.")
        return

    db = db_session if db_session else SessionLocal()
    try:
        # JSONファイルのリストを取得
        json_files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
        if not json_files:
            print("No JSON history files found.")
            return

        for filename in json_files:
            youtube_channel_id = filename.replace(".json", "")
            
            # 対応するチャンネルが DB に存在するか確認
            channel = db.query(Channel).filter(Channel.youtube_channel_id == youtube_channel_id).first()
            if not channel:
                # チャンネルがDBに無ければスキップ（削除されたチャンネルなどの履歴データ）
                continue

            file_path = os.path.join(HISTORY_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception as e:
                print(f"Error reading JSON file {file_path}: {e}")
                continue

            print(f"Syncing stats history for channel: {channel.title} ({youtube_channel_id})")

            for item in history_data:
                try:
                    date_str = item.get("date")
                    if not date_str:
                        continue
                    
                    recorded_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

                    # 同一日のレコードがすでに SQLite に存在するか確認
                    existing = db.query(ChannelStatsHistory).filter(
                        ChannelStatsHistory.channel_id == channel.id,
                        ChannelStatsHistory.recorded_at == recorded_date
                    ).first()

                    if existing:
                        # 存在する場合は、数値が違う場合のみ最新情報に更新
                        if (existing.subscriber_count != item["subscriber_count"] or
                            existing.view_count != item["view_count"] or
                            existing.video_count != item["video_count"]):
                            existing.subscriber_count = item["subscriber_count"]
                            existing.view_count = item["view_count"]
                            existing.video_count = item["video_count"]
                            print(f"  -> Updated history for date: {date_str}")
                    else:
                        # 存在しない場合は新規登録
                        new_record = ChannelStatsHistory(
                            channel_id=channel.id,
                            subscriber_count=item["subscriber_count"],
                            view_count=item["view_count"],
                            video_count=item["video_count"],
                            recorded_at=recorded_date
                        )
                        db.add(new_record)
                        print(f"  -> Imported new history for date: {date_str}")

                except Exception as e:
                    print(f"Error processing item {item} for {youtube_channel_id}: {e}")

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

    args = parser.parse_args()

    if args.db:
        run_db_mode()
    elif args.json:
        run_json_mode()
    elif args.sync_json:
        run_sync_json_mode()
