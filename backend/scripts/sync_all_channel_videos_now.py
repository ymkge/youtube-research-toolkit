import os
import sys
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

db_path = os.path.join(backend_dir, "youtube_research.db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app.db.session import SessionLocal
from app.models.channel import Channel
from app.services.youtube import youtube_service
from app.api.endpoints.channels import sync_channel_videos, calculate_channel_metrics

def sync_all_channels_now():
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        print(f"=== 全 {len(channels)} チャンネルの最新動画一括同期 ＆ DBアップデートを開始します ===")
        
        synced_count = 0
        for channel in channels:
            try:
                if youtube_service.is_configured():
                    info = youtube_service.get_channel_info(channel.youtube_channel_id)
                    uploads_playlist_id = info.get("uploads_playlist_id") if info else None
                    
                    if uploads_playlist_id:
                        print(f"🔄 同期中 ({synced_count+1}/{len(channels)}): {channel.title} ({channel.custom_url})...")
                        sync_channel_videos(db, channel, uploads_playlist_id, import_limit=50)
                        
                        _, _, _, latest_pub, _, _, _, _, _, w_cnt = calculate_channel_metrics(db, channel.id)
                        print(f"   -> 最新投稿日: {latest_pub} | 🔥 直近7日: {w_cnt} 本")
                        synced_count += 1
                    else:
                        print(f"⚠️ プレイリスト取得不可: {channel.title}")
            except Exception as ex:
                db.rollback()
                print(f"❌ エラー発生 ({channel.title}): {ex}")
                
        print(f"\n🎉 全チャンネル最新動画一括同期完了: {synced_count}/{len(channels)} 件更新成功")
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_channels_now()
