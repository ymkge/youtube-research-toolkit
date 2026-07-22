import React from 'react';
import { Channel } from '../utils/api';
import styles from './ChannelCard.module.css';
import { Users, Tv, Play } from 'lucide-react';

interface ChannelCardProps {
  channel: Channel;
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

export default function ChannelCard({ channel }: ChannelCardProps) {
  return (
    <div className={styles.card}>
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
          {channel.custom_url && (
            <span className={styles.customUrl}>{channel.custom_url}</span>
          )}
        </div>
      </div>

      <p className={styles.description}>
        {channel.description || '説明はありません。'}
      </p>

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
          <span className={styles.statLabel}>再生回数</span>
        </div>
      </div>
    </div>
  );
}
