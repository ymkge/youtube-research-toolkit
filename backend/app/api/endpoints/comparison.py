from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.session import get_db
from app.models.channel import Channel
from app.models.channel_stats_history import ChannelStatsHistory

router = APIRouter()

# グラフ用カラーパレット (20色ユニークカラー)
COLOR_PALETTE = [
    "#8a2be2", # 1. パープル
    "#00ff7f", # 2. ネオングリーン
    "#00bfff", # 3. スカイブルー
    "#ff007f", # 4. ディープピンク
    "#ffa500", # 5. オレンジ
    "#ffff00", # 6. イエロー
    "#00ffff", # 7. シアン
    "#ff4500", # 8. レッドオレンジ
    "#da70d6", # 9. オーキッド
    "#32cd32", # 10. ライム
    "#ff69b4", # 11. ホットピンク
    "#1e90ff", # 12. ドジャーブルー
    "#adff2f", # 13. グリーンイエロー
    "#ff1493", # 14. マゼンタ
    "#00fa9a", # 15. ミディアムスプリンググリーン
    "#ff8c00", # 16. ダークオレンジ
    "#ba55d3", # 17. ミディアムオーキッド
    "#00e5ff", # 18. ブライトシアン
    "#ff3366", # 19. コーラルレッド
    "#76ff03", # 20. ネオンライム
]

# 線のスタイルパターン (20色を超える場合や色が近い場合に実線・破線・点線で区別)
DASH_PATTERNS = [
    "none",        # 1〜20件目: 実線
    "6 6",         # 21〜40件目: 破線
    "2 4",         # 41〜60件目: 点線
    "12 4 2 4",    # 61〜80件目: 一点鎖線
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
        dash_pattern = DASH_PATTERNS[(idx // len(COLOR_PALETTE)) % len(DASH_PATTERNS)]
        
        # 該当チャンネルの履歴データを取得 (昇順)
        histories = (
            db.query(ChannelStatsHistory)
            .filter(ChannelStatsHistory.channel_id == channel.id)
            .order_by(ChannelStatsHistory.recorded_at.asc())
            .all()
        )

        has_history = len(histories) > 0

        # 直近の前日比成長データ (daily_sub_growth / daily_view_growth_rate) の算出
        daily_sub_growth = 0
        daily_view_growth_rate = 0.0
        if len(histories) >= 2:
            prev_sub = histories[-2].subscriber_count or 0
            curr_sub = histories[-1].subscriber_count or 0
            daily_sub_growth = curr_sub - prev_sub

            prev_views = histories[-2].view_count or 0
            curr_views = histories[-1].view_count or 0
            if prev_views > 0:
                daily_view_growth_rate = round(((curr_views - prev_views) / prev_views) * 100.0, 2)

        channel_list.append({
            "id": channel.id,
            "title": channel.title,
            "youtube_channel_id": channel.youtube_channel_id,
            "custom_url": channel.custom_url,
            "thumbnail_url": channel.thumbnail_url,
            "color": color,
            "dash_pattern": dash_pattern,
            "has_history": has_history,
            "history_count": len(histories),
            "subscriber_count": channel.subscriber_count or 0,
            "is_pinned": channel.is_pinned,
            "daily_sub_growth": daily_sub_growth,
            "daily_view_growth_rate": daily_view_growth_rate,
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
