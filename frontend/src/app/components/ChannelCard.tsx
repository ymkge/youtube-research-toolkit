import React, { useState, useEffect } from 'react';
import { Channel, fetchChannelHistory, ChannelStatsHistory, updateChannelPin, deleteChannel, toggleOwnChannel } from '../utils/api';
import styles from './ChannelCard.module.css';
import ChannelHistoryChart from './ChannelHistoryChart';
import { Users, Tv, Play, Clock, Trash2, Calendar, BarChart2, Pin, MoreVertical, GripVertical, TrendingUp, Brain, Sparkles, AlertCircle, CheckCircle2, Trophy, ArrowRight, Flame, Home } from 'lucide-react';

interface ChannelCardProps {
  channel: Channel;
  onDelete: (channelId: number) => Promise<void>;
  onPinToggle: (channelId: number, isPinned: boolean) => Promise<void>;
  onUpdateChannel?: (updatedChannel: Channel) => void;
  onDragStart: (e: React.DragEvent, id: number) => void;
  onDragOver: (e: React.DragEvent, id: number) => void;
  onDragEnd: (e: React.DragEvent) => void;
  isDraggingNow?: boolean;
  onShowAIAnalysis: (channel: Channel) => void;
  onToggleOwnChannel?: (channelId: number) => void;
  isAllTrendExpanded?: boolean;
  allTrendMetric?: 'subscribers' | 'views' | 'videos';
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

// 日付のフォーマット関数 (YYYY/MM/DD)
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '不明';
  const date = new Date(dateStr);
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}/${mm}/${dd}`;
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

// 国コード（ISO 3166-1 alpha-2）から国旗絵文字を生成する関数
function getCountryEmoji(countryCode: string | null): string {
  if (!countryCode || countryCode === 'UNKNOWN') return '';
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}

export default function ChannelCard({ 
  channel, 
  onDelete, 
  onPinToggle,
  onUpdateChannel,
  onDragStart,
  onDragOver,
  onDragEnd,
  isDraggingNow = false,
  onShowAIAnalysis,
  onToggleOwnChannel,
  isAllTrendExpanded,
  allTrendMetric
}: ChannelCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPinning, setIsPinning] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  // トレンドグラフ表示用ステート
  const [showChart, setShowChart] = useState(false);
  const [history, setHistory] = useState<ChannelStatsHistory[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [isHistoryLoaded, setIsHistoryLoaded] = useState(false);

  // channel.id が変わった場合は履歴ステートをリセット
  useEffect(() => {
    setHistory([]);
    setIsHistoryLoaded(false);
  }, [channel.id]);

  // 親からの一括開閉フラグ変化を検知して同期
  useEffect(() => {
    if (isAllTrendExpanded !== undefined) {
      setShowChart(isAllTrendExpanded);
    }
  }, [isAllTrendExpanded]);

  // showChart が true になった時、未ロードであれば自動的に履歴データをフェッチ (1回のみ)
  useEffect(() => {
    if (showChart && !isHistoryLoaded && !isHistoryLoading) {
      const loadHistory = async () => {
        setIsHistoryLoading(true);
        try {
          const data = await fetchChannelHistory(channel.id);
          setHistory(data);
          setIsHistoryLoaded(true);
        } catch (err) {
          console.error('統計履歴データのロードに失敗しました:', err);
        } finally {
          setIsHistoryLoading(false);
        }
      };
      loadHistory();
    }
  }, [showChart, channel.id, isHistoryLoaded, isHistoryLoading]);

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

  const handlePinClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsPinning(true);
    try {
      await onPinToggle(channel.id, !channel.is_pinned);
    } finally {
      setIsPinning(false);
    }
  };

  const handleTrendClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowChart(!showChart);
  };



  // 登録者数に応じたランククラスを取得する関数
  const getCardRankClass = (subscriberCount: number): string => {
    if (subscriberCount >= 100000) return styles.cardDiamond;
    if (subscriberCount >= 10000) return styles.cardGold;
    if (subscriberCount >= 1000) return styles.cardSilver;
    return styles.cardBronze;
  };

  // YouTube チャンネルへのリンクURLを構築
  const channelUrl = channel.custom_url
    ? `https://www.youtube.com/${channel.custom_url}`
    : `https://www.youtube.com/channel/${channel.youtube_channel_id}`;

  const rankClass = getCardRankClass(channel.subscriber_count || 0);

  return (
    <div 
      className={`${styles.card} ${rankClass} ${channel.is_pinned ? styles.pinnedCard : ''} ${channel.is_own_channel ? styles.ownChannelCard : ''} ${isDeleting ? styles.deleting : ''} ${isDraggingNow ? styles.dragging : ''} ${showChart ? styles.expanded : ''}`}
      onMouseLeave={() => setIsMenuOpen(false)}
    >
      <div className={styles.actionButtons}>
        {/* トレンド表示（グラフ）ボタン */}
        <button 
          className={`${styles.trendButton} ${showChart ? styles.trendActive : ''}`} 
          onClick={handleTrendClick} 
          title={showChart ? "トレンド表示を閉じる" : "統計トレンドを表示"}
          disabled={isDeleting}
        >
          <TrendingUp size={14} />
        </button>

        {/* AI分析ボタン */}
        <button 
          className={styles.aiButton} 
          onClick={(e) => { e.stopPropagation(); onShowAIAnalysis(channel); }} 
          title="AIポジショニング分析を表示"
          disabled={isDeleting}
        >
          <Brain size={14} />
        </button>

        {/* 自チャンネル切り替えボタン */}
        <button 
          className={`${styles.ownButton} ${channel.is_own_channel ? styles.ownActive : ''}`} 
          onClick={async (e) => {
            e.stopPropagation();
            if (isDeleting) return;
            try {
              const updated = await toggleOwnChannel(channel.id);
              if (onUpdateChannel) {
                onUpdateChannel(updated);
              } else if (onToggleOwnChannel) {
                onToggleOwnChannel(channel.id);
              }
            } catch (err) {
              console.error("自チャンネル切り替えエラー:", err);
              alert("自チャンネル設定の更新に失敗しました。");
            }
          }} 
          title={channel.is_own_channel ? "自チャンネル設定を解除" : "このチャンネルを自分のチャンネルに設定"}
          disabled={isDeleting}
        >
          <Home size={14} className={channel.is_own_channel ? styles.ownIconActive : ''} />
        </button>

        {/* ピン留めボタン */}
        <button 
          className={`${styles.pinButton} ${channel.is_pinned ? styles.pinned : ''}`} 
          onClick={handlePinClick} 
          title={channel.is_pinned ? "ピン留めを解除" : "ピン留めする"}
          disabled={isPinning || isDeleting}
        >
          <Pin size={14} className={channel.is_pinned ? styles.pinIconActive : ''} />
        </button>

        {/* メニューボタン */}
        <button 
          className={`${styles.menuButton} ${isMenuOpen ? styles.menuActive : ''}`} 
          onClick={(e) => { e.stopPropagation(); setIsMenuOpen(!isMenuOpen); }} 
          title="メニューを開く"
          disabled={isDeleting}
        >
          <MoreVertical size={16} />
        </button>

        {isMenuOpen && (
          <div className={styles.dropdownMenu} onClick={(e) => e.stopPropagation()}>
            <button 
              className={styles.dropdownItemDelete}
              onClick={(e) => { setIsMenuOpen(false); handleDeleteClick(e); }}
            >
              <Trash2 size={14} className={styles.menuDeleteIcon} />
              <span>追跡解除（削除）</span>
            </button>
          </div>
        )}
      </div>

      <div className={styles.header}>
        {/* ドラッグ専用のGripハンドル */}
        <div 
          className={styles.dragHandle}
          draggable="true"
          onDragStart={(e) => onDragStart(e, channel.id)}
          onDragOver={(e) => onDragOver(e, channel.id)}
          onDragEnd={onDragEnd}
          title="ドラッグして並び替え"
        >
          <GripVertical size={18} />
        </div>

        {channel.thumbnail_url && (
          <img
            src={channel.thumbnail_url}
            alt={channel.title}
            className={styles.thumbnail}
            draggable="false"
          />
        )}
        <div className={styles.titles}>
          <div className={styles.titleRow}>
            <h3 className={styles.title} title={channel.title}>
              <a href={channelUrl} target="_blank" rel="noopener noreferrer" className={styles.titleLink}>
                {channel.title}
              </a>
            </h3>
            {channel.country && channel.country !== 'UNKNOWN' && (
              <span className={styles.countryFlag} title={`国: ${channel.country}`}>
                {getCountryEmoji(channel.country)}
              </span>
            )}
          </div>

          {/* バッジ群 (自チャンネル & 急成長シグナル) */}
          {(channel.is_own_channel ||
            (channel.daily_sub_growth !== undefined && channel.daily_sub_growth >= 100) ||
            (channel.daily_view_growth_rate !== undefined && channel.daily_view_growth_rate >= 2.0)) && (
            <div className={styles.badgeRow}>
              {channel.is_own_channel && (
                <div className={styles.ownBadge} title="比較基準の自チャンネル">
                  <Home size={11} className={styles.ownBadgeIcon} />
                  <span>自チャンネル</span>
                </div>
              )}
              {channel.daily_sub_growth !== undefined && channel.daily_sub_growth >= 100 && (
                <div className={styles.hotBadge} title="前日比で登録者数が100名以上急増中！">
                  <Flame size={12} className={styles.hotIcon} />
                  <span>登録者 +{channel.daily_sub_growth.toLocaleString()}名</span>
                </div>
              )}
              {channel.daily_view_growth_rate !== undefined && channel.daily_view_growth_rate >= 2.0 && (
                <div className={`${styles.hotBadge} ${styles.viewHotBadge}`} title="前日比で総再生数が2.0%以上急増中！">
                  <Flame size={12} className={styles.viewHotIcon} />
                  <span>再生数 +{channel.daily_view_growth_rate.toFixed(1)}%</span>
                </div>
              )}
            </div>
          )}
          <div className={styles.metaRow}>
            {channel.custom_url && (
              <span className={styles.customUrl}>{channel.custom_url}</span>
            )}
            <div className={styles.dateRow}>
              <span className={styles.publishedAt}>
                開設: {formatDate(channel.published_at)}
              </span>
              {channel.latest_video_published_at && (
                <>
                  <span className={styles.separator}>|</span>
                  <span className={styles.latestUpload}>
                    最新: {formatDate(channel.latest_video_published_at)}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <p className={styles.description}>
        {channel.description || '説明はありません。'}
      </p>

      {/* 分析メトリクス用チップ行 */}
      <div className={styles.chipsRow}>
        <div 
          className={`${styles.weeklyChip} ${(channel.weekly_video_count || 0) > 0 ? styles.weeklyActive : ''}`} 
          title="直近7日間 (168時間) に投稿された動画本数"
        >
          <Flame className={styles.weeklyIcon} size={13} />
          <span>直近7日: <strong>{channel.weekly_video_count ?? 0}本</strong></span>
        </div>

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

      {/* 投稿フォーマット比率可視化エリア (Shorts / LIVE / 通常動画) */}
      {(channel.short_ratio !== undefined || channel.live_ratio !== undefined) && (
        <div 
          className={styles.formatRatioSection} 
          title={`直近動画内訳: Shorts ${channel.short_video_count || 0}本 (${channel.short_ratio || 0}%) / LIVE ${channel.live_stream_count || 0}回 (${channel.live_ratio || 0}%) / 通常 ${channel.regular_video_count || 0}本`}
        >
          <div className={styles.formatRatioHeader}>
            <span className={styles.formatRatioTitle}>動画タイプ内訳</span>
            <div className={styles.formatRatioBadges}>
              {(channel.short_video_count || 0) > 0 && (
                <span className={styles.shortBadge} title={`Shorts: ${channel.short_video_count}本`}>🩳 Shorts {channel.short_ratio}%</span>
              )}
              {(channel.live_stream_count || 0) > 0 && (
                <span className={styles.liveBadge} title={`LIVE: ${channel.live_stream_count}回`}>🔴 LIVE {channel.live_ratio}%</span>
              )}
              <span className={styles.regularBadge} title={`通常動画: ${channel.regular_video_count || 0}本`}>
                🎬 通常 {Math.max(0, 100 - (channel.short_ratio || 0) - (channel.live_ratio || 0)).toFixed(1)}%
              </span>
            </div>
          </div>
          <div className={styles.formatProgressBar}>
            <div 
              className={styles.shortBarSegment} 
              style={{ width: `${channel.short_ratio || 0}%` }}
            />
            <div 
              className={styles.liveBarSegment} 
              style={{ width: `${channel.live_ratio || 0}%` }}
            />
            <div 
              className={styles.regularBarSegment} 
              style={{ width: `${Math.max(0, 100 - (channel.short_ratio || 0) - (channel.live_ratio || 0))}%` }}
            />
          </div>
        </div>
      )}

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

      {/* ★ トレンド折れ線グラフコンポーネント (アコーディオン展開されるエリア) */}
      {showChart && (
        <ChannelHistoryChart history={history} isLoading={isHistoryLoading} initialMetric={allTrendMetric} />
      )}
    </div>
  );
}
