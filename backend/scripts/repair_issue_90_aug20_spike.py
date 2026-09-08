import os
import sys
import json
from datetime import date
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

db_path = os.path.join(backend_dir, "youtube_research.db")
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app.db.session import SessionLocal
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory

HISTORY_DIR = os.path.join(backend_dir, "data", "history")

def repair_aug20_spikes():
    db = SessionLocal()
    try:
        print("=== Issue #90: 2026-08-20 時系列異常スパイクデータのピンポイント安全修復を開始 ===")

        # 1. Kokoro Music Room (@kokoromusicroom) の修復
        ch_kokoro = db.query(Channel).filter(
            (Channel.custom_url == "@kokoromusicroom") | (Channel.custom_url == "kokoromusicroom")
        ).first()
        if ch_kokoro:
            hist_kokoro = db.query(ChannelStatsHistory).filter(
                ChannelStatsHistory.channel_id == ch_kokoro.id,
                ChannelStatsHistory.recorded_at == date(2026, 8, 20)
            ).first()
            if hist_kokoro:
                print(f"🔧 Kokoro Music Room (8/20): {hist_kokoro.view_count:,} -> 4,375,591")
                hist_kokoro.view_count = 4375591

            json_kokoro = os.path.join(HISTORY_DIR, f"{ch_kokoro.youtube_channel_id}.json")
            if os.path.exists(json_kokoro):
                with open(json_kokoro, "r", encoding="utf-8") as f:
                    jdata = json.load(f)
                for item in jdata:
                    if item.get("date") == "2026-08-20":
                        item["view_count"] = 4375591
                with open(json_kokoro, "w", encoding="utf-8") as f:
                    json.dump(jdata, f, indent=2, ensure_ascii=False)
                print(f"   └─ JSON ファイル修復完了: {json_kokoro}")

        # 2. Doctor Focus BGM (@doctorfocusbgm) の修復
        ch_doctor = db.query(Channel).filter(
            (Channel.custom_url == "@doctorfocusbgm") | (Channel.custom_url == "doctorfocusbgm")
        ).first()
        if ch_doctor:
            hist_doctor = db.query(ChannelStatsHistory).filter(
                ChannelStatsHistory.channel_id == ch_doctor.id,
                ChannelStatsHistory.recorded_at == date(2026, 8, 20)
            ).first()
            if hist_doctor:
                print(f"🔧 Doctor Focus BGM (8/20): {hist_doctor.view_count:,} -> 3,226")
                hist_doctor.view_count = 3226

            json_doctor = os.path.join(HISTORY_DIR, f"{ch_doctor.youtube_channel_id}.json")
            if os.path.exists(json_doctor):
                with open(json_doctor, "r", encoding="utf-8") as f:
                    jdata = json.load(f)
                for item in jdata:
                    if item.get("date") == "2026-08-20":
                        item["view_count"] = 3226
                with open(json_doctor, "w", encoding="utf-8") as f:
                    json.dump(jdata, f, indent=2, ensure_ascii=False)
                print(f"   └─ JSON ファイル修復完了: {json_doctor}")

        db.commit()
        print("\n🎉 2026-08-20 の時系列スパイクデータ安全修復が完全完了いたしました！")
    finally:
        db.close()

if __name__ == "__main__":
    repair_aug20_spikes()
