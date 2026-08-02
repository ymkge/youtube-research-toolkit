'use client';

import React, { useState, useEffect, useMemo } from 'react';
import styles from './MilestoneModal.module.css';
import { ChannelMilestoneItem, fetchChannelMilestones } from '../utils/api';
import { Search, X, ArrowUpDown } from 'lucide-react';

interface MilestoneModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type SortKey = 'current_subscribers' | '100k_date' | '10k_date' | '1k_date' | 'days_to_10k';

export const MilestoneModal: React.FC<MilestoneModalProps> = ({ isOpen, onClose }) => {
  const [milestones, setMilestones] = useState<ChannelMilestoneItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<SortKey>('current_subscribers');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadMilestones();
    }
  }, [isOpen]);

  const loadMilestones = async () => {
    try {
      setLoading(true);
      const res = await fetchChannelMilestones();
      setMilestones(res.milestones);
      setError(null);
    } catch (err: any) {
      console.error('Milestone fetch error:', err);
      setError(err.message || 'マイルストーンデータの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  const filteredAndSorted = useMemo(() => {
    let result = [...milestones];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (m) =>
          m.title.toLowerCase().includes(q) ||
          (m.custom_url && m.custom_url.toLowerCase().includes(q))
      );
    }

    result.sort((a, b) => {
      switch (sortBy) {
        case '100k_date':
          if (!a.reached_100k_date && !b.reached_100k_date) return b.current_subscribers - a.current_subscribers;
          if (!a.reached_100k_date) return 1;
          if (!b.reached_100k_date) return -1;
          return a.reached_100k_date.localeCompare(b.reached_100k_date);

        case '10k_date':
          if (!a.reached_10k_date && !b.reached_10k_date) return b.current_subscribers - a.current_subscribers;
          if (!a.reached_10k_date) return 1;
          if (!b.reached_10k_date) return -1;
          return a.reached_10k_date.localeCompare(b.reached_10k_date);

        case '1k_date':
          if (!a.reached_1k_date && !b.reached_1k_date) return b.current_subscribers - a.current_subscribers;
          if (!a.reached_1k_date) return 1;
          if (!b.reached_1k_date) return -1;
          return a.reached_1k_date.localeCompare(b.reached_1k_date);

        case 'days_to_10k':
          const daysA = a.days_1k_to_10k ?? 999999;
          const daysB = b.days_1k_to_10k ?? 999999;
          return daysA - daysB;

        case 'current_subscribers':
        default:
          return b.current_subscribers - a.current_subscribers;
      }
    });

    return result;
  }, [milestones, searchQuery, sortBy]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* ヘッダー */}
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            <span className={styles.titleIcon}>🏆</span>
            <div>
              <h3 className={styles.title}>登録者達成マイルストーン一覧</h3>
              <p className={styles.subtitle}>
                競合チャンネルが 1,000人 / 1万人 / 10万人 に到達した日付と成長スピード（所要日数）
              </p>
            </div>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* コントロールバー */}
        <div className={styles.controls}>
          <div className={styles.searchBox}>
            <Search size={14} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="チャンネル名やハンドル名で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ArrowUpDown size={14} style={{ color: '#fbbf24' }} />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className={styles.sortSelect}
            >
              <option value="current_subscribers">並び順: 現在の登録者数順</option>
              <option value="100k_date">並び順: 10万人達成日順</option>
              <option value="10k_date">並び順: 1万人達成日順</option>
              <option value="1k_date">並び順: 1,000人達成日順</option>
              <option value="days_to_10k">並び順: 1K➔10Kスピード順</option>
            </select>
          </div>
        </div>

        {/* テーブル表示領域 */}
        <div className={styles.tableWrapper}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#9ca3af' }}>
              マイルストーンデータを集計中...
            </div>
          ) : error ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#ef4444' }}>{error}</div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>チャンネル</th>
                  <th>現在の登録者数</th>
                  <th>🥉 1,000人 (1K) 達成日</th>
                  <th>🥇 1万人 (10K) 達成日</th>
                  <th>💎 10万人 (100K) 達成日</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSorted.map((item) => {
                  const has1k = Boolean(item.reached_1k_date);
                  const has10k = Boolean(item.reached_10k_date);
                  const has100k = Boolean(item.reached_100k_date);

                  return (
                    <tr key={item.channel_id}>
                      <td>
                        <div className={styles.channelCell}>
                          {item.thumbnail_url ? (
                            <img
                              src={item.thumbnail_url}
                              alt={item.title}
                              className={styles.avatar}
                            />
                          ) : (
                            <div
                              className={styles.avatar}
                              style={{
                                background: '#374151',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                              }}
                            >
                              📺
                            </div>
                          )}
                          <div className={styles.channelNameGroup}>
                            <span className={styles.channelTitle}>{item.title}</span>
                            {item.custom_url && (
                              <span className={styles.customUrl}>{item.custom_url}</span>
                            )}
                          </div>
                        </div>
                      </td>

                      <td style={{ fontWeight: 700, color: '#f3f4f6' }}>
                        {item.current_subscribers.toLocaleString()} 人
                      </td>

                      {/* 1K 達成日 */}
                      <td>
                        {has1k ? (
                          <div className={`${styles.badge} ${styles.badge1k}`}>
                            <span>{item.reached_1k_date}</span>
                            {item.is_1k_before_tracking ? (
                              <span className={styles.beforeLabel}>(追跡開始前)</span>
                            ) : (
                              item.days_to_1k !== null &&
                              item.days_to_1k !== undefined && (
                                <span className={styles.daysLabel}>開設から {item.days_to_1k}日</span>
                              )
                            )}
                          </div>
                        ) : (
                          <div className={`${styles.badge} ${styles.badgeNotReached}`}>未達成</div>
                        )}
                      </td>

                      {/* 10K 達成日 */}
                      <td>
                        {has10k ? (
                          <div className={`${styles.badge} ${styles.badge10k}`}>
                            <span>{item.reached_10k_date}</span>
                            {item.is_10k_before_tracking ? (
                              <span className={styles.beforeLabel}>(追跡開始前)</span>
                            ) : (
                              item.days_1k_to_10k !== null &&
                              item.days_1k_to_10k !== undefined && (
                                <span className={styles.daysLabel}>1Kから {item.days_1k_to_10k}日</span>
                              )
                            )}
                          </div>
                        ) : (
                          <div className={`${styles.badge} ${styles.badgeNotReached}`}>未達成</div>
                        )}
                      </td>

                      {/* 100K 達成日 */}
                      <td>
                        {has100k ? (
                          <div className={`${styles.badge} ${styles.badge100k}`}>
                            <span>{item.reached_100k_date}</span>
                            {item.is_100k_before_tracking ? (
                              <span className={styles.beforeLabel}>(追跡開始前)</span>
                            ) : (
                              item.days_10k_to_100k !== null &&
                              item.days_10k_to_100k !== undefined && (
                                <span className={styles.daysLabel}>10Kから {item.days_10k_to_100k}日</span>
                              )
                            )}
                          </div>
                        ) : (
                          <div className={`${styles.badge} ${styles.badgeNotReached}`}>未達成</div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* フッター */}
        <div className={styles.footer}>
          <span style={{ fontSize: '0.825rem', color: '#9ca3af' }}>
            表示中: <strong>{filteredAndSorted.length}</strong> / {milestones.length} 件
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.1)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#ffffff',
              padding: '0.4rem 1.2rem',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
};
