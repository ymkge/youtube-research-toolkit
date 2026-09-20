import os
import sys
import datetime
from sqlalchemy.orm import Session

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

from app.db.session import SessionLocal
from app.models.channel import Channel
from app.services.youtube import youtube_service

def sync_all_metadata_cli():
    """
    全チャンネルのメタデータ（概要欄・タイトル・アイコン・ハンドル名・統計）を
    YouTube Data API (hl=ja) から一括取得して最新化するスクリプト。
    """
    print("=======================================================")
    print(" 🚀 YouTube Research Toolkit: メタデータ一括同期開始")
    print("=======================================================")

    if not youtube_service.is_configured():
        print("❌ エラー: YOUTUBE_API_KEY が設定されていません。backend/.env を確認してください。")
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        channels = db.query(Channel).all()
        if not channels:
            print("登録されているチャンネルがありません。")
            return

        print(f"対象チャンネル数: {len(channels)} 件")
        target_cids = [c.youtube_channel_id for c in channels if c.youtube_channel_id]
        channel_handles_map = {c.youtube_channel_id: c.custom_url for c in channels if c.custom_url}

        print("YouTube API (hl=ja) バッチ通信を実行中...")
        batch_info = youtube_service.get_channels_info_batch(target_cids, channel_handles_map)
        print(f"取得完了: {len(batch_info)} 件のチャンネル情報を受信しました。\n")

        updated_count = 0
        now_utc = datetime.datetime.utcnow()

        for c in channels:
            cid = c.youtube_channel_id
            info = batch_info.get(cid)
            if not info:
                print(f"⚠️ スキップ (APIレスポンスなし): {c.title} ({cid})")
                continue

            old_desc_len = len(c.description or "")
            new_desc = info.get("description") or ""
            new_desc_len = len(new_desc)
            old_title = c.title
            new_title = info.get("title") or old_title

            # 変更の適用
            c.description = new_desc
            c.title = new_title
            if info.get("thumbnail_url"):
                c.thumbnail_url = info["thumbnail_url"]
            if info.get("custom_url"):
                c.custom_url = info["custom_url"]
            if info.get("country"):
                c.country = info["country"]

            # Max Guard による統計更新
            api_subs = info.get("subscriber_count", 0)
            api_views = info.get("view_count", 0)
            api_vids = info.get("video_count", 0)

            if api_subs > (c.subscriber_count or 0):
                c.subscriber_count = api_subs
            if api_views > (c.view_count or 0):
                c.view_count = api_views
            if api_vids > (c.video_count or 0):
                c.video_count = api_vids

            c.updated_at = now_utc
            updated_count += 1

            snippet = new_desc[:40].replace('\n', ' ')
            print(f"✅ 更新: {new_title} ({c.custom_url or cid})")
            print(f"   概要欄: {old_desc_len}文字 ➔ {new_desc_len}文字 | 冒頭: {snippet}...")

        db.commit()
        print("\n=======================================================")
        print(f" 🎉 完了: 全 {updated_count} / {len(channels)} 件のメタデータを正常に同期しました。")
        print("=======================================================")

    except Exception as ex:
        db.rollback()
        print(f"❌ エラーが発生しました: {ex}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    sync_all_metadata_cli()
