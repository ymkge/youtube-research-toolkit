from typing import List, Optional
from dataclasses import dataclass
import re

from app.models.channel import Channel
from app.models.video import Video
from app.models.channel_stats_history import ChannelStatsHistory

@dataclass
class AnomalyResult:
    anomaly_type: Optional[str] = None      # "ad_suspected" | "artificial_sub_growth" | "ghost_views" | None
    anomaly_score: Optional[float] = None    # 0.0 ~ 1.0 (疑わしさの度合い)
    anomaly_reason: Optional[str] = None    # ユーザー表示用理由
    target_video_id: Optional[str] = None   # 起因となった動画ID (広告疑い等の場合)

def parse_iso8601_duration(duration_str: Optional[str]) -> int:
    """ISO 8601 duration (e.g. PT15M30S) を秒数に変換します。"""
    if not duration_str:
        return 0
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

def detect_channel_anomalies(
    channel: Channel,
    videos: List[Video],
    histories: List[ChannelStatsHistory]
) -> AnomalyResult:
    """
    チャンネルの動画および時系列履歴データから、
    広告出稿（プロモーション）や外部ブースト（登録者・再生数購入）による
    不自然な上昇アノマリーを統計的に検知します。
    """
    # -------------------------------------------------------------
    # 1. 登録者急増アノマリー (artificial_sub_growth) の判定
    # -------------------------------------------------------------
    if len(histories) >= 2:
        latest_sub = histories[0].subscriber_count or 0
        prev_sub = histories[1].subscriber_count or 0
        sub_growth = latest_sub - prev_sub

        latest_view = histories[0].view_count or 0
        prev_view = histories[1].view_count or 0
        view_growth = latest_view - prev_view

        # 条件: 登録者が前日比200名以上急増しているが、再生数の伸びが極めて少ない (登録増の5倍未満)
        if sub_growth >= 200 and view_growth < sub_growth * 5:
            reason = (
                f"前日比で登録者が +{sub_growth:,}名 急増していますが、"
                f"再生数増加（+{max(view_growth, 0):,}回）が伴っておらず、"
                f"外部ブースト・登録者購入の疑いがあります。"
            )
            return AnomalyResult(
                anomaly_type="artificial_sub_growth",
                anomaly_score=0.90,
                anomaly_reason=reason
            )

    if not videos:
        return AnomalyResult()

    # -------------------------------------------------------------
    # 2. 広告出稿疑い (ad_suspected) および 幽霊再生 (ghost_views) の判定
    # -------------------------------------------------------------
    valid_videos = [v for v in videos if v.view_count and v.view_count > 0]
    if not valid_videos:
        return AnomalyResult()

    for video in valid_videos:
        views = video.view_count
        likes = video.like_count
        comments = video.comment_count
        dur_sec = parse_iso8601_duration(video.duration)
        is_short = getattr(video, "is_short", False) or (dur_sec > 0 and dur_sec <= 60)
        is_long_bgm = dur_sec >= 1800  # 30分以上の長尺BGM・作業用動画

        # 他の動画群の再生数中央値（自身を除く）
        other_views = [v.view_count for v in valid_videos if v != video]
        if other_views:
            sorted_other = sorted(other_views)
            median_views = sorted_other[len(sorted_other) // 2]
        else:
            median_views = views

        # --- 2a. 幽霊再生 (ghost_views) 判定 ---
        if views >= 10000 and comments is not None and comments == 0:
            like_rate = (likes / views * 100.0) if likes is not None else 0.0
            if like_rate < 0.05:
                reason = (
                    f"動画「{video.title[:25]}...」の再生数が {views:,}回 に対して "
                    f"コメント0件・高評価率 {like_rate:.2f}% と皆無であり、機械的再生の疑いがあります。"
                )
                return AnomalyResult(
                    anomaly_type="ghost_views",
                    anomaly_score=0.95,
                    anomaly_reason=reason,
                    target_video_id=video.youtube_video_id
                )

        # --- 2b. 広告出稿疑い (ad_suspected) 判定 ---
        # 突出したスパイク動画（5,000再生以上 かつ 他の動画の中央値の3倍以上、または他動画がない場合10,000再生以上）
        is_spike = (views >= 5000 and (len(other_views) == 0 or views >= median_views * 3)) or views >= 30000
        if is_spike and likes is not None and comments is not None:
            like_rate = (likes / views) * 100.0
            comment_rate = (comments / views) * 100.0

            if is_short:
                like_thresh = 0.80
                comment_thresh = 0.010
            elif is_long_bgm:
                like_thresh = 0.20
                comment_thresh = 0.010
            else:
                like_thresh = 0.35
                comment_thresh = 0.015

            if like_rate < like_thresh and comment_rate < comment_thresh:
                reason = (
                    f"動画「{video.title[:25]}...」の再生急増（{views:,}回）に対し、"
                    f"高評価率 {like_rate:.2f}%・コメント率 {comment_rate:.3f}% と極めて低く、"
                    f"広告出稿（プロモーション流入）の可能性が高いです。"
                )
                return AnomalyResult(
                    anomaly_type="ad_suspected",
                    anomaly_score=0.85,
                    anomaly_reason=reason,
                    target_video_id=video.youtube_video_id
                )

    return AnomalyResult()
