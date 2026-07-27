from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory

router = APIRouter()

# グラフ用カラーパレット (10色巡回)
COLOR_PALETTE = [
    "#8a2be2", # ブルーバイオレット
    "#00ff7f", # スプリンググリーン
    "#00bfff", # ディープスカイブルー
    "#ff007f", # ネオンピンク
    "#ffa500", # オレンジ
    "#ffff00", # イエロー
    "#00ffff", # シアン
    "#ff4500", # オレンジレッド
    "#da70d6", # オーキッド
    "#32cd32", # ライムグリーン
]

@router.get("/comparison")
def get_channels_comparison(db: Session = Depends(get_db)):
    """
    全登録チャンネルの統計履歴を取得し、
    最古の履歴日を基準(0%)とした「累積成長率(%)」のタイムラインデータを返します。
    """
    channels = db.query(Channel).order_by(Channel.sort_order.asc(), Channel.id.asc()).all()

    channel_list = []
    # 日付ごとの平坦化マップ { "YYYY/MM/DD": { "date": "YYYY/MM/DD", "sub_growth_1": 0.0, ... } }
    timeline_map: Dict[str, Dict[str, Any]] = {}

    for idx, channel in enumerate(channels):
        color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
        
        # 該当チャンネルの履歴データを取得 (昇順)
        histories = (
            db.query(ChannelStatsHistory)
            .filter(ChannelStatsHistory.channel_id == channel.id)
            .order_by(ChannelStatsHistory.recorded_at.asc())
            .all()
        )

        has_history = len(histories) > 0
        channel_list.append({
            "id": channel.id,
            "title": channel.title,
            "youtube_channel_id": channel.youtube_channel_id,
            "thumbnail_url": channel.thumbnail_url,
            "color": color,
            "has_history": has_history,
            "history_count": len(histories)
        })

        if not has_history:
            continue

        # 基準日 (最古データ) の数値
        base_sub = histories[0].subscriber_count or 0
        base_views = histories[0].view_count or 0

        for hist in histories:
            # 日付文字列 (YYYY/MM/DD)
            date_str = hist.recorded_at.strftime("%Y/%m/%d")

            if date_str not in timeline_map:
                timeline_map[date_str] = {"date": date_str}

            curr_sub = hist.subscriber_count or 0
            curr_views = hist.view_count or 0

            # 累積成長率 (%) の算出 (0除算安全ガード)
            sub_growth = round(((curr_sub - base_sub) / base_sub) * 100, 2) if base_sub > 0 else 0.0
            view_growth = round(((curr_views - base_views) / base_views) * 100, 2) if base_views > 0 else 0.0

            # Recharts 用に動的キーでフラットに設定
            timeline_map[date_str][f"sub_growth_{channel.id}"] = sub_growth
            timeline_map[date_str][f"view_growth_{channel.id}"] = view_growth
            timeline_map[date_str][f"subscribers_{channel.id}"] = curr_sub
            timeline_map[date_str][f"views_{channel.id}"] = curr_views

    # 日付昇順でソートされたタイムライン配列
    sorted_timeline = [timeline_map[d] for d in sorted(timeline_map.keys())]

    return {
        "channels": channel_list,
        "timeline": sorted_timeline
    }
