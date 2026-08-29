import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from app.db.session import SessionLocal
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory
from app.api.endpoints.channels import sync_parent_channel_stats

def repair_all_channels():
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        print(f"=== DB修復開始: 全 {len(channels)} チャンネルの親 Channel カラムを最新 ChannelStatsHistory と 100% 強制同期します ===")
        
        repaired_count = 0
        for channel in channels:
            latest_history = (
                db.query(ChannelStatsHistory)
                .filter(ChannelStatsHistory.channel_id == channel.id)
                .order_by(ChannelStatsHistory.recorded_at.desc())
                .first()
            )
            
            if latest_history:
                is_mismatched = (
                    channel.subscriber_count != latest_history.subscriber_count or
                    channel.view_count != latest_history.view_count or
                    channel.video_count != latest_history.video_count
                )
                
                if is_mismatched:
                    print(f"🔧 修復実行: {channel.title} ({channel.custom_url})")
                    print(f"   [旧] 登録者: {channel.subscriber_count}, 総再生: {channel.view_count}, 動画数: {channel.video_count}")
                    
                    sync_parent_channel_stats(db, channel.id)
                    
                    print(f"   [新] 登録者: {channel.subscriber_count}, 総再生: {channel.view_count}, 動画数: {channel.video_count}")
                    repaired_count += 1
                else:
                    print(f"✅ 正常 (同期済み): {channel.title} (登録者: {channel.subscriber_count})")
        
        db.commit()
        print(f"\n🎉 修復完了: 合計 {repaired_count} 件のチャンネルの不整合を修復・同調いたしました！")
    except Exception as e:
        db.rollback()
        print(f"❌ エラー発生: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    repair_all_channels()
