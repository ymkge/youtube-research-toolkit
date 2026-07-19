from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings
import datetime
from typing import Dict, Any, List, Optional

class YouTubeService:
    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self.youtube = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            # APIクライアントのビルド (開発者キーを利用)
            self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def is_configured(self) -> bool:
        # クライアントが正しく初期化されているか、または環境変数が再設定された場合に再初期化
        if not self.youtube and settings.YOUTUBE_API_KEY:
            self.api_key = settings.YOUTUBE_API_KEY
            self._init_client()
        return self.youtube is not None

    def get_channel_info(self, identifier: str) -> Dict[str, Any]:
        """
        チャンネルID (UC...) またはハンドル名 (@...) からチャンネル情報を取得します。
        """
        if not self.is_configured():
            raise ValueError("YouTube APIキーが設定されていません。backend/.env ファイルを確認してください。")

        # ハンドル指定の場合
        if identifier.startswith("@"):
            try:
                # API v3 は forHandle をサポートしています
                request = self.youtube.channels().list(
                    part="snippet,statistics,contentDetails",
                    forHandle=identifier
                )
                response = request.execute()
            except HttpError:
                # forHandle が動作しない場合のフォールバック (検索による特定)
                request = self.youtube.search().list(
                    part="snippet",
                    q=identifier,
                    type="channel",
                    maxResults=1
                )
                search_response = request.execute()
                items = search_response.get("items", [])
                if not items:
                    raise ValueError(f"ハンドル名に対応するチャンネルが見つかりませんでした: {identifier}")
                channel_id = items[0]["snippet"]["channelId"]
                return self.get_channel_info(channel_id)
        else:
            # チャンネルID指定の場合
            request = self.youtube.channels().list(
                part="snippet,statistics,contentDetails",
                id=identifier
            )
            response = request.execute()

        items = response.get("items", [])
        if not items:
            raise ValueError(f"チャンネルが見つかりませんでした: {identifier}")

        channel_data = items[0]
        snippet = channel_data.get("snippet", {})
        stats = channel_data.get("statistics", {})
        content_details = channel_data.get("contentDetails", {})

        # 開設日のパース
        published_at_str = snippet.get("publishedAt")
        published_at = None
        if published_at_str:
            # Z をタイムゾーン表記に置換してパース
            published_at = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

        return {
            "youtube_channel_id": channel_data.get("id"),
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "custom_url": snippet.get("customUrl"),
            "published_at": published_at,
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads")
        }

    def get_recent_videos(self, uploads_playlist_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        アップロード用プレイリストIDから最新の動画リストと各動画の統計詳細を取得します。
        """
        if not self.is_configured():
            raise ValueError("YouTube APIキーが設定されていません。")

        videos = []
        next_page_token = None

        while len(videos) < limit:
            request = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=min(50, limit - len(videos)),
                pageToken=next_page_token
            )
            response = request.execute()

            items = response.get("items", [])
            if not items:
                break

            for item in items:
                snippet = item.get("snippet", {})
                video_id = snippet.get("resourceId", {}).get("videoId")
                published_at_str = snippet.get("publishedAt")
                published_at = None
                if published_at_str:
                    published_at = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

                videos.append({
                    "youtube_video_id": video_id,
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "published_at": published_at
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        if not videos:
            return []

        # 各動画の統計情報を一括取得 (50件ごと)
        video_ids = [v["youtube_video_id"] for v in videos]
        chunk_size = 50
        details_map = {}

        for i in range(0, len(video_ids), chunk_size):
            chunk = video_ids[i:i + chunk_size]
            request = self.youtube.videos().list(
                part="statistics,contentDetails,snippet",
                id=",".join(chunk)
            )
            response = request.execute()

            for item in response.get("items", []):
                vid = item.get("id")
                stats = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                snippet = item.get("snippet", {})

                # タグをカンマ区切りに連結
                tags_list = snippet.get("tags", [])
                tags_str = ",".join(tags_list) if tags_list else None

                details_map[vid] = {
                    "view_count": int(stats.get("viewCount", 0)),
                    "like_count": int(stats.get("likeCount", 0)) if "likeCount" in stats else None,
                    "comment_count": int(stats.get("commentCount", 0)) if "commentCount" in stats else None,
                    "duration": content_details.get("duration"),
                    "tags": tags_str,
                    "category_id": snippet.get("categoryId")
                }

        # 元の動画リストに統計情報をマージ
        for v in videos:
            vid = v["youtube_video_id"]
            if vid in details_map:
                v.update(details_map[vid])

        return videos

youtube_service = YouTubeService()
