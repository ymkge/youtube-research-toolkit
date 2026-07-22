import React, { useState } from 'react';
import { Channel } from '../utils/api';
import styles from './ChannelCard.module.css';
import { Users, Tv, Play, Clock, Trash2, Calendar, BarChart2 } from 'lucide-react';

interface ChannelCardProps {
  channel: Channel;
  onDelete: (channelId: number) => Promise<void>;
}

// 数値を読みやすい単位（万、億）にフォーマットする関数
function formatNumber(num: number): string {
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(1)}億`;
  }
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}万`;
  }
  return num.toLocaleString();
}

// 開設日のフォーマット関数 (YYYY年MM月DD日)
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '不明';
  const date = new Date(dateStr);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

// 秒数を「分秒」に変換する関数
function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return 'データなし';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}分${secs}秒`;
}

// 投稿頻度を「週〇回」にフォーマットする関数
function formatFrequency(freq: number | null): string {
  if (freq === null || freq === undefined) return 'データなし';
  return `週 ${freq.toFixed(1)}回`;
}

export default function ChannelCard({ channel, onDelete }: ChannelCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`「${channel.title}」を追跡解除（削除）しますか？\n紐づく動画統計データもすべてSQLiteから削除されます。`)) {
      setIsDeleting(true);
      try {
        await onDelete(channel.id);
      } catch (err) {
        setIsDeleting(false);
      }
    }
  };

  return (
    <div className={`${styles.card} ${isDeleting ? styles.deleting : ''}`}>
      <button 
        className={styles.deleteButton} 
        onClick={handleDeleteClick} 
        title="チャンネルを追跡解除"
        disabled={isDeleting}
      >
        <Trash2 size={16} />
      </button>

      <div className={styles.header}>
        {channel.thumbnail_url && (
          <img
            src={channel.thumbnail_url}
            alt={channel.title}
            className={styles.thumbnail}
          />
        )}
        <div className={styles.titles}>
          <h3 className={styles.title} title={channel.title}>
            {channel.title}
          </h3>
          <div className={styles.metaRow}>
            {channel.custom_url && (
              <span className={styles.customUrl}>{channel.custom_url}</span>
            )}
            <span className={styles.publishedAt}>
              開設: {formatDate(channel.published_at)}
            </span>
          </div>
        </div>
      </div>

      <p className={styles.description}>
        {channel.description || '説明はありません。'}
      </p>

      {/* 分析メトリクス用チップ行（平均動画時間 ＆ 平均投稿頻度 & 1動画平均再生） */}
      <div className={styles.chipsRow}>
        <div className={styles.durationChip} title="同期された動画の平均長さ">
          <Clock className={styles.durationIcon} size={13} />
          <span>動画長: <strong>{formatDuration(channel.average_video_duration)}</strong></span>
        </div>

        <div className={styles.frequencyChip} title="週あたりの動画投稿頻度">
          <Calendar className={styles.frequencyIcon} size={13} />
          <span>投稿: <strong>{formatFrequency(channel.average_upload_frequency)}</strong></span>
        </div>

        <div className={styles.viewsChip} title="1動画あたりの平均視聴回数">
          <BarChart2 className={styles.viewsIcon} size={13} />
          <span>平均再生: <strong>{formatNumber(channel.average_views_per_video || 0)}</strong></span>
        </div>
      </div>

      <div className={styles.stats}>
        <div className={styles.statItem} title="チャンネル登録者数">
          <Users className={styles.icon} size={16} />
          <span className={styles.statValue}>
            {formatNumber(channel.subscriber_count)}
          </span>
          <span className={styles.statLabel}>登録者</span>
        </div>

        <div className={styles.statItem} title="総動画数">
          <Tv className={styles.icon} size={16} />
          <span className={styles.statValue}>
            {formatNumber(channel.video_count)}
          </span>
          <span className={styles.statLabel}>動画数</span>
        </div>

        <div className={styles.statItem} title="総再生回数">
          <Play className={styles.icon} size={16} />
          <span className={styles.statValue}>
            {formatNumber(channel.view_count)}
          </span>
          <span className={styles.statLabel}>総再生数</span>
        </div>
      </div>
    </div>
  );
}
