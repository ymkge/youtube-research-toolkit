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
from app.models.video import Video
from app.api.endpoints.channels import sync_parent_channel_stats

def repair_all_channels_data():
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        print(f"=== Issue #86: 全 {len(channels)} チャンネルの実態数値セルフヒーリング補正を開始 ===")
        
        repaired_count = 0
        for channel in channels:
            vids = db.query(Video).filter(Video.channel_id == channel.id).all()
            sum_views = sum(v.view_count for v in vids if v.view_count) if vids else 0
            vid_count = len(vids) if vids else 0

            old_views = channel.view_count or 0
            old_videos = channel.video_count or 0

            sync_parent_channel_stats(db, channel.id)

            db.refresh(channel)
            new_views = channel.view_count or 0
            new_videos = channel.video_count or 0

            if new_views != old_views or new_videos != old_videos:
                print(f"✅ 補正修復 ({channel.title}): 再生数 {old_views:,} -> {new_views:,} | 動画数 {old_videos} -> {new_videos}")
                repaired_count += 1
            else:
                print(f"ℹ️ 正常一致 ({channel.title}): 再生数 {new_views:,} | 動画数 {new_videos}")

        db.commit()
        print(f"\n🎉 補正処理完了！合計 {repaired_count} チャンネルの数値を実態に合わせて修正修復しました。")
    finally:
        db.close()

if __name__ == "__main__":
    repair_all_channels_data()
