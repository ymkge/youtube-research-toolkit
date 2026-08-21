import os
import pytest
import datetime
import sqlite3
from app.core.backup import (
    create_db_backup,
    cleanup_old_backups,
    verify_backup_integrity,
    restore_db_from_backup,
    get_backup_dir,
    get_db_path,
    JST
)

def test_create_db_backup_success(db):
    """
    バックアップ生成テスト:
    create_db_backup() が正常に実行され、backend/data/backups/ 内に .db ファイルが作成されること。
    """
    backup_path = create_db_backup(prefix="test_backup")
    assert os.path.exists(backup_path)
    assert backup_path.endswith(".db")
    assert verify_backup_integrity(backup_path) is True

    # 後後片付け
    if os.path.exists(backup_path):
        os.remove(backup_path)

def test_cleanup_old_backups_retention(db):
    """
    7日保持・8日目自動削除テスト:
    直近7日以内のファイルは保持され、8日以上前のファイルのみが自動削除されること。
    """
    backup_dir = get_backup_dir()
    now_jst = datetime.datetime.now(JST).date()

    # テスト用ダミーファイルの準備 (5日前, 7日前, 8日前, 10日前)
    date_5d = (now_jst - datetime.timedelta(days=5)).strftime("%Y%m%d")
    date_7d = (now_jst - datetime.timedelta(days=7)).strftime("%Y%m%d")
    date_8d = (now_jst - datetime.timedelta(days=8)).strftime("%Y%m%d")
    date_10d = (now_jst - datetime.timedelta(days=10)).strftime("%Y%m%d")

    file_5d = os.path.join(backup_dir, f"youtube_research_backup_{date_5d}_120000.db")
    file_7d = os.path.join(backup_dir, f"youtube_research_backup_{date_7d}_120000.db")
    file_8d = os.path.join(backup_dir, f"youtube_research_backup_{date_8d}_120000.db")
    file_10d = os.path.join(backup_dir, f"youtube_research_backup_{date_10d}_120000.db")

    dummy_paths = [file_5d, file_7d, file_8d, file_10d]
    for p in dummy_paths:
        with open(p, "w", encoding="utf-8") as f:
            f.write("dummy content")

    deleted = cleanup_old_backups(retention_days=7)

    # 5日・7日目は保持されていること
    assert os.path.exists(file_5d)
    assert os.path.exists(file_7d)

    # 8日・10日目は削除されていること
    assert not os.path.exists(file_8d)
    assert not os.path.exists(file_10d)
    assert os.path.basename(file_8d) in deleted
    assert os.path.basename(file_10d) in deleted

    # 後片付け
    if os.path.exists(file_5d):
        os.remove(file_5d)
    if os.path.exists(file_7d):
        os.remove(file_7d)

def test_verify_backup_integrity():
    """
    バックアップファイルの健全性検証テスト:
    正常な DB ファイルでは True、破損ファイル・存在しないファイルでは False を返すこと。
    """
    assert verify_backup_integrity("non_existent_file.db") is False

    backup_dir = get_backup_dir()
    corrupted_path = os.path.join(backup_dir, "corrupted_test_backup.db")
    with open(corrupted_path, "w", encoding="utf-8") as f:
        f.write("this is not a sqlite database")

    assert verify_backup_integrity(corrupted_path) is False

    if os.path.exists(corrupted_path):
        os.remove(corrupted_path)

def test_restore_db_from_backup(db):
    """
    安全なリストア（復元）テスト:
    バックアップからの復元が正常に行われ、復元直前に emergency バックアップが作られること。
    """
    # 正常なバックアップを作成
    valid_backup = create_db_backup(prefix="test_restore_source")

    # リストアの実行
    success = restore_db_from_backup(valid_backup)
    assert success is True

    # 復元時に緊急避難用バックアップ (youtube_research_emergency_...) が生成されていること
    backup_dir = get_backup_dir()
    emergencies = [f for f in os.listdir(backup_dir) if f.startswith("youtube_research_emergency_")]
    assert len(emergencies) > 0

    # 後片付け
    if os.path.exists(valid_backup):
        os.remove(valid_backup)
    for em in emergencies:
        em_path = os.path.join(backup_dir, em)
        if os.path.exists(em_path):
            os.remove(em_path)
