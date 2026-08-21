import os
import re
import sqlite3
import datetime
from typing import List, Optional
from app.core.config import settings

# タイムゾーン定義 (JST: UTC+9)
JST = datetime.timezone(datetime.timedelta(hours=+9))

def get_backend_dir() -> str:
    """backend ディレクトリの絶対パスを返します"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_backup_dir() -> str:
    """バックアップファイル保存先ディレクトリ (backend/data/backups/) の絶対パスを返し、無ければ作成します"""
    backend_dir = get_backend_dir()
    backup_dir = os.path.join(backend_dir, "data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def get_db_path() -> str:
    """現在運用中の SQLite データベースファイルの絶対パスを返します"""
    db_url = getattr(settings, "DATABASE_URL", "sqlite:///./youtube_research.db")
    raw_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(raw_path):
        raw_path = os.path.join(get_backend_dir(), raw_path)
    return os.path.abspath(raw_path)

def create_db_backup(prefix: str = "youtube_research_backup") -> str:
    """
    sqlite3.backup API を使用して、動作中でも安全なスナップショットバックアップを作成します。
    一時ファイル (.tmp) に書き込んだ後、アトミックに目的ファイル名へリネームして破損を防止します。
    """
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found at: {db_path}")

    now_jst = datetime.datetime.now(JST)
    timestamp = now_jst.strftime("%Y%m%d_%H%M%S")
    backup_dir = get_backup_dir()
    final_filename = f"{prefix}_{timestamp}.db"
    final_path = os.path.join(backup_dir, final_filename)
    tmp_path = final_path + ".tmp"

    try:
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(tmp_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        os.replace(tmp_path, final_path)
        print(f"DB Backup: Successfully created backup at {final_path}")
        return final_path
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise RuntimeError(f"Failed to create DB backup: {e}")

def cleanup_old_backups(retention_days: int = 7) -> List[str]:
    """
    指定日数（デフォルト7日分保持、8日目以降）を超えた古くなったバックアップファイルを自動削除します。
    ファイル名 YYYYMMDD 日付文字列をパースして厳密に判定します。
    """
    backup_dir = get_backup_dir()
    deleted_files = []
    now_jst = datetime.datetime.now(JST).date()

    # 厳格なファイル名判定正規表現
    pattern = re.compile(r"^youtube_research_backup_(\d{8})_\d{6}\.db$")

    if not os.path.exists(backup_dir):
        return deleted_files

    for fname in os.listdir(backup_dir):
        match = pattern.match(fname)
        if match:
            date_str = match.group(1)
            try:
                file_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
                age_days = (now_jst - file_date).days
                # 8日目以降 (retention_days 7日を超えた分) を自動削除
                if age_days >= (retention_days + 1):
                    full_path = os.path.join(backup_dir, fname)
                    os.remove(full_path)
                    deleted_files.append(fname)
                    print(f"DB Backup Cleanup: Deleted old backup {fname} (Age: {age_days} days)")
            except ValueError:
                continue

    return deleted_files

def verify_backup_integrity(backup_path: str) -> bool:
    """
    PRAGMA quick_check によるバックアップファイルの健全性検証を行います。
    """
    if not os.path.exists(backup_path):
        return False
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA quick_check;")
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == "ok"
    except Exception:
        return False

def restore_db_from_backup(backup_path: str) -> bool:
    """
    指定のバックアップファイルから運用 DB へ安全に復元（リストア）します。
    復元直前に緊急バックアップを取得し、失敗時は自動的にロールバックします。
    """
    if not verify_backup_integrity(backup_path):
        raise ValueError(f"Backup file integrity check failed for: {backup_path}")

    db_path = get_db_path()

    # 1. 現行 DB の緊急避難バックアップを作成
    emergency_path = create_db_backup(prefix="youtube_research_emergency")
    print(f"DB Restore: Created emergency backup at {emergency_path}")

    # 2. SQLAlchemy エンジンコネクションの安全解体
    try:
        from app.db.session import engine
        engine.dispose()
    except Exception:
        pass

    # 3. リストア実行 (sqlite3.backup API)
    try:
        src_conn = sqlite3.connect(backup_path)
        dst_conn = sqlite3.connect(db_path)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        print("DB Restore: Successfully restored database.")
        return True
    except Exception as e:
        print(f"DB Restore Error: {e}. Attempting automatic rollback from emergency backup...")
        # 失敗時は緊急バックアップからロールバック試行
        try:
            src_conn = sqlite3.connect(emergency_path)
            dst_conn = sqlite3.connect(db_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            print("DB Restore: Rollback to emergency backup succeeded.")
        except Exception as rb_err:
            print(f"DB Restore CRITICAL: Rollback failed: {rb_err}")
        raise RuntimeError(f"Database restore failed: {e}")
