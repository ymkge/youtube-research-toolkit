'use client';

import React, { useState, useEffect } from 'react';
import styles from './SyncStatusBanner.module.css';
import { SyncStatusResponse, fetchSyncStatus, fetchMissingTodayStats } from '../utils/api';

interface SyncStatusBannerProps {
  onRefreshData?: () => void;
}

export const SyncStatusBanner: React.FC<SyncStatusBannerProps> = ({ onRefreshData }) => {
  const [statusData, setStatusData] = useState<SyncStatusResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchingMissing, setFetchingMissing] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await fetchSyncStatus();
      setStatusData(data);
      setErrorMessage(null);
    } catch (err: any) {
      console.warn('Sync status fetch error (handled safely):', err);
      setErrorMessage(err.message || '同期ステータスの確認に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleFetchMissing = async () => {
    try {
      setFetchingMissing(true);
      const result = await fetchMissingTodayStats();
      alert(result.message);
      setShowModal(false);
      await loadStatus();
      if (onRefreshData) {
        onRefreshData();
      }
    } catch (err: any) {
      alert(`データ取得エラー: ${err.message || '失敗しました。'}`);
    } finally {
      setFetchingMissing(false);
    }
  };

  if (loading || !statusData) {
    return null;
  }

  return (
    <div className={styles.container}>
      {statusData.is_all_updated ? (
        <div className={styles.successBanner}>
          <div className={styles.leftGroup}>
            <span className={styles.statusIcon}>🟢</span>
            <span>
              本日 ({statusData.today}) のデータ同期完了 ({statusData.updated_count} / {statusData.total_channels} 件)
            </span>
          </div>
        </div>
      ) : (
        <div className={styles.warningBanner}>
          <div className={styles.leftGroup}>
            <span className={styles.statusIcon}>⚠️</span>
            <span>
              本日 ({statusData.today}) のデータが未取得のチャンネルが{' '}
              <strong>{statusData.missing_count} 件</strong> あります
            </span>
          </div>

          <div className={styles.actionGroup}>
            <button
              onClick={() => setShowModal(true)}
              className={styles.detailsBtn}
              title="未取得チャンネルの一覧を確認"
            >
              🔍 対象チャンネルを表示 ({statusData.missing_count})
            </button>

            <button
              onClick={handleFetchMissing}
              disabled={fetchingMissing}
              className={styles.fetchBtn}
            >
              <span className={fetchingMissing ? styles.spinning : ''}>🔄</span>
              {fetchingMissing ? 'データを取得中...' : '今すぐデータを取得'}
            </button>
          </div>
        </div>
      )}

      {/* 未取得チャンネル詳細モーダル */}
      {showModal && (
        <div className={styles.modalOverlay} onClick={() => setShowModal(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <div className={styles.modalTitle}>
                <span>⚠️</span>
                <span>当日データ未取得のチャンネル一覧</span>
              </div>
              <button className={styles.closeBtn} onClick={() => setShowModal(false)}>
                ✕
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: '#9ca3af', marginBottom: '1rem' }}>
              以下のチャンネルは本日 ({statusData.today}) の日次統計データがまだ記録されていません。
            </p>

            <div className={styles.channelList}>
              {statusData.missing_channels.map((item) => (
                <div key={item.id} className={styles.channelItem}>
                  <div className={styles.channelInfo}>
                    <span className={styles.channelTitle}>{item.title}</span>
                    {item.custom_url && <span className={styles.channelHandle}>{item.custom_url}</span>}
                  </div>
                  <span className={styles.lastDate}>
                    最終取得: {item.last_recorded_at || '記録なし'}
                  </span>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                onClick={() => setShowModal(false)}
                className={styles.detailsBtn}
                style={{ borderColor: 'rgba(255, 255, 255, 0.2)', color: '#d1d5db' }}
              >
                閉じる
              </button>
              <button
                onClick={handleFetchMissing}
                disabled={fetchingMissing}
                className={styles.fetchBtn}
              >
                <span className={fetchingMissing ? styles.spinning : ''}>🔄</span>
                {fetchingMissing ? '取得中...' : '今すぐデータを取得'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
