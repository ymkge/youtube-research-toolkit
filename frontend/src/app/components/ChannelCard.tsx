import React, { useState } from 'react';
import { Channel, fetchChannelHistory, ChannelStatsHistory, fetchChannelAIAnalysis, AIAnalysisResponse } from '../utils/api';
import styles from './ChannelCard.module.css';
import ChannelHistoryChart from './ChannelHistoryChart';
import { Users, Tv, Play, Clock, Trash2, Calendar, BarChart2, Pin, MoreVertical, GripVertical, TrendingUp, Brain, Sparkles, AlertCircle, CheckCircle2, Trophy, ArrowRight } from 'lucide-react';

interface ChannelCardProps {
  channel: Channel;
  onDelete: (channelId: number) => Promise<void>;
  onPinToggle: (channelId: number, isPinned: boolean) => Promise<void>;
  onDragStart: (e: React.DragEvent, channelId: number) => void;
  onDragOver: (e: React.DragEvent, channelId: number) => void;
  onDragEnd: (e: React.DragEvent) => void;
  isDraggingNow?: boolean;
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

// 国名コード (JP, US) から国旗絵文字に変換する関数
function getCountryEmoji(countryCode: string | null): string {
  if (!countryCode) return '';
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
  onDragStart,
  onDragOver,
  onDragEnd,
  isDraggingNow = false
}: ChannelCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isPinning, setIsPinning] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  // トレンドグラフ表示用ステート
  const [showChart, setShowChart] = useState(false);
  const [history, setHistory] = useState<ChannelStatsHistory[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);

  // AI分析表示用ステート
  const [showAI, setShowAI] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [isAILoading, setIsAILoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

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

  const handleTrendClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const nextState = !showChart;
    setShowChart(nextState);

    // グラフを表示する際、未ロードの場合のみAPIから履歴データをフェッチ
    if (nextState && history.length === 0) {
      setIsHistoryLoading(true);
      try {
        const data = await fetchChannelHistory(channel.id);
        setHistory(data);
      } catch (err) {
        console.error('統計履歴データのロードに失敗しました:', err);
      } finally {
        setIsHistoryLoading(false);
      }
    }
  };

  const handleAIClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const nextState = !showAI;
    setShowAI(nextState);
    setAiError(null);

    // AIレポートを表示する際、未ロードの場合のみAPIから分析レポートをフェッチ
    if (nextState && !aiAnalysis) {
      setIsAILoading(true);
      try {
        const data = await fetchChannelAIAnalysis(channel.id);
        setAiAnalysis(data);
      } catch (err: any) {
        setAiError(err.message || 'AI分析の生成に失敗しました。');
        console.error('AI分析のロードに失敗しました:', err);
      } finally {
        setIsAILoading(false);
      }
    }
  };

  // YouTube チャンネルへのリンクURLを構築
  const channelUrl = channel.custom_url
    ? `https://www.youtube.com/${channel.custom_url}`
    : `https://www.youtube.com/channel/${channel.youtube_channel_id}`;

  return (
    <div 
      className={`${styles.card} ${isDeleting ? styles.deleting : ''} ${isDraggingNow ? styles.dragging : ''} ${showChart || showAI ? styles.expanded : ''}`}
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
          className={`${styles.aiButton} ${showAI ? styles.aiActive : ''}`} 
          onClick={handleAIClick} 
          title={showAI ? "AI分析を閉じる" : "AIポジショニング分析を表示"}
          disabled={isDeleting}
        >
          <Brain size={14} />
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

      {/* ★ トレンド折れ線グラフコンポーネント (アコーディオン展開されるエリア) */}
      {showChart && (
        <ChannelHistoryChart history={history} isLoading={isHistoryLoading} />
      )}

      {/* 🤖 AI分析結果エリア (アコーディオン展開) */}
      {showAI && (
        <div className={styles.aiReportArea}>
          {isAILoading && (
            <div className={styles.aiSkeletonContainer}>
              <div className={styles.aiSkeletonTitle}>
                <Sparkles className={styles.aiSkeletonIcon} size={16} />
                <span>AIが競合データを分析中...</span>
              </div>
              <div className={styles.aiSkeletonLine} style={{ width: '90%' }}></div>
              <div className={styles.aiSkeletonLine} style={{ width: '80%' }}></div>
              <div className={styles.aiSkeletonLine} style={{ width: '85%' }}></div>
              <div className={styles.aiSkeletonGrid}>
                <div className={styles.aiSkeletonCard}></div>
                <div className={styles.aiSkeletonCard}></div>
              </div>
            </div>
          )}

          {aiError && (
            <div className={styles.aiErrorContainer}>
              <AlertCircle size={18} className={styles.aiErrorIcon} />
              <div className={styles.aiErrorText}>
                <strong>分析に失敗しました</strong>
                <p>{aiError}</p>
              </div>
            </div>
          )}

          {!isAILoading && !aiError && aiAnalysis && (
            <div className={styles.aiReportContent}>
              <div className={styles.aiReportHeader}>
                <Brain size={16} className={styles.aiHeaderIcon} />
                <h4>AIポジショニング分析レポート</h4>
              </div>

              {/* 要約 */}
              <p className={styles.aiSummary}>{aiAnalysis.channel_summary}</p>

              {/* 強みと弱みの2カラム */}
              <div className={styles.aiGrid2}>
                <div className={`${styles.aiCard} ${styles.aiCardStrength}`}>
                  <h5>
                    <CheckCircle2 size={14} className={styles.aiCardIconStrength} />
                    <span>競合独自の強み</span>
                  </h5>
                  <ul>
                    {aiAnalysis.strengths.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className={`${styles.aiCard} ${styles.aiCardWeakness}`}>
                  <h5>
                    <AlertCircle size={14} className={styles.aiCardIconWeakness} />
                    <span>弱み・未開拓領域</span>
                  </h5>
                  <ul>
                    {aiAnalysis.weaknesses.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 主要ヒットテーマ */}
              <div className={styles.aiSection}>
                <h5 className={styles.aiSectionTitle}>
                  <Trophy size={14} className={styles.aiSectionIconTrophy} />
                  <span>高パフォーマンスなヒットテーマ (最大3つ)</span>
                </h5>
                <div className={styles.aiThemesGrid}>
                  {aiAnalysis.top_performing_themes.map((theme, idx) => (
                    <div key={idx} className={styles.aiThemeCard}>
                      <div className={styles.aiThemeBadge}>Theme {idx + 1}</div>
                      <h6>{theme.theme_name}</h6>
                      <p>{theme.reason_for_popularity}</p>
                      <div className={styles.aiExampleVideo}>
                        <span>代表動画:</span> {theme.example_video_title}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 差別化アドバイス */}
              <div className={`${styles.aiCard} ${styles.aiCardAdvice}`}>
                <h5>
                  <ArrowRight size={14} className={styles.aiCardIconAdvice} />
                  <span>自チャンネルの差別化・ポジショニング戦略</span>
                </h5>
                <ul>
                  {aiAnalysis.positioning_advice.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              {/* 生成日時 */}
              <div className={styles.aiReportFooter}>
                分析日時: {new Date(aiAnalysis.generated_at).toLocaleString('ja-JP')}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
