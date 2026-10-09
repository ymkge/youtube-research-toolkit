'use client';

import React, { useState, useEffect } from 'react';
import { ChannelStatsHistory, ChannelWeekdayStatsResponse, fetchChannelWeekdayStats } from '../utils/api';
import styles from './ChannelHistoryChart.module.css';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  TooltipProps
} from 'recharts';

type MetricType = 'subscribers' | 'views' | 'videos' | 'weekday';

interface ChannelHistoryChartProps {
  channelId?: number;
  history: ChannelStatsHistory[];
  isLoading: boolean;
  initialMetric?: MetricType;
}

// 数値を読みやすい単位（万、億）にフォーマットする関数
function formatMetricValue(value: number): string {
  if (value >= 100000000) {
    return `${(value / 100000000).toFixed(2)}億`;
  }
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万`;
  }
  return value.toLocaleString();
}

// 日付のフォーマット (YYYY/MM/DD -> MM/DD など)
function formatChartDate(dateStr: string): string {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[1]}/${parts[2]}`; // MM/DD 形式にする
  }
  return dateStr;
}

interface MetricDiff {
  diffStr: string;
  rateStr: string;
  type: 'positive' | 'negative' | 'neutral' | 'none';
}

function calcDiff(current: number, baseline: number | null): MetricDiff {
  if (baseline === null || baseline === undefined) {
    return { diffStr: '—', rateStr: '', type: 'none' };
  }
  const diff = current - baseline;
  const rate = baseline > 0 ? (diff / baseline) * 100 : 0;

  if (diff > 0) {
    return {
      diffStr: `+${formatMetricValue(diff)}`,
      rateStr: `(+${rate.toFixed(1)}%)`,
      type: 'positive',
    };
  } else if (diff < 0) {
    return {
      diffStr: `${formatMetricValue(diff)}`,
      rateStr: `(${rate.toFixed(1)}%)`,
      type: 'negative',
    };
  } else {
    return { diffStr: '±0', rateStr: '(0.0%)', type: 'neutral' };
  }
}

// 実日付 (recorded_at) ベースの過去データ最近傍検索関数
function findNearestHistoryItem(history: ChannelStatsHistory[], currentIndex: number, targetDaysAgo: number): ChannelStatsHistory | null {
  if (currentIndex <= 0) return null;
  const currentItem = history[currentIndex];
  const currentDate = new Date(currentItem.recorded_at).getTime();
  const targetTime = currentDate - targetDaysAgo * 86400 * 1000;

  // 許容誤差範囲 (DoD: 1〜3日前 / WoW: 5〜10日前)
  const minAllowedTime = targetDaysAgo === 1 
    ? currentDate - 3 * 86400 * 1000 
    : currentDate - 10 * 86400 * 1000;

  let bestMatch: ChannelStatsHistory | null = null;
  let minDiff = Infinity;

  for (let i = currentIndex - 1; i >= 0; i--) {
    const itemDate = new Date(history[i].recorded_at).getTime();
    if (itemDate < minAllowedTime) break;

    const diff = Math.abs(itemDate - targetTime);
    if (diff < minDiff) {
      minDiff = diff;
      bestMatch = history[i];
    }
  }

  return bestMatch;
}

export default function ChannelHistoryChart({ channelId, history, isLoading, initialMetric = 'subscribers' }: ChannelHistoryChartProps) {
  const [metric, setMetric] = useState<MetricType>(initialMetric);
  const [weekdayStats, setWeekdayStats] = useState<ChannelWeekdayStatsResponse | null>(null);
  const [isWeekdayLoading, setIsWeekdayLoading] = useState(false);
  const [weekdayViewMode, setWeekdayViewMode] = useState<'upload' | 'growth'>('upload');

  useEffect(() => {
    if (initialMetric) {
      setMetric(initialMetric);
    }
  }, [initialMetric]);

  // 曜日別タブ選択時に API をフェッチ
  useEffect(() => {
    if (metric === 'weekday' && channelId && !weekdayStats && !isWeekdayLoading) {
      setIsWeekdayLoading(true);
      fetchChannelWeekdayStats(channelId)
        .then((data) => setWeekdayStats(data))
        .catch((err) => console.error('曜日別統計取得エラー:', err))
        .finally(() => setIsWeekdayLoading(false));
    }
  }, [metric, channelId, weekdayStats, isWeekdayLoading]);

  // グラフ用データおよび DoD/WoW 事前計算キャッシュ構築 (Hooks は最上部で呼び出す)
  const chartData = React.useMemo(() => {
    if (!history || history.length === 0) return [];
    return history.map((item, index) => {
      const dodItem = findNearestHistoryItem(history, index, 1);
      const wowItem = findNearestHistoryItem(history, index, 7);

      return {
        date: formatChartDate(item.recorded_at),
        fullDate: item.recorded_at.replace(/-/g, '/'),
        subscribers: item.subscriber_count,
        views: item.view_count,
        videos: item.video_count,
        dod: {
          subscribers: calcDiff(item.subscriber_count, dodItem ? dodItem.subscriber_count : null),
          views: calcDiff(item.view_count, dodItem ? dodItem.view_count : null),
          videos: calcDiff(item.video_count, dodItem ? dodItem.video_count : null),
        },
        wow: {
          subscribers: calcDiff(item.subscriber_count, wowItem ? wowItem.subscriber_count : null),
          views: calcDiff(item.view_count, wowItem ? wowItem.view_count : null),
          videos: calcDiff(item.video_count, wowItem ? wowItem.video_count : null),
        }
      };
    });
  }, [history]);

  // 全 Hook の評価後に早期リターンを行う
  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner}></div>
        <p>トレンドデータを読み込み中...</p>
      </div>
    );
  }

  if (!history || history.length === 0) {
    return (
      <div className={styles.emptyContainer}>
        <p>時系列データがまだ蓄積されていません。</p>
        <p className={styles.emptyTip}>
          GitHub Actions の定期実行、またはローカルバッチの定期実行が行われると、日次の推移がここにグラフ表示されます。
        </p>
      </div>
    );
  }

  // 現在選択されているメトリクスに応じたデザイン設定
  const metricConfigs = {
    subscribers: {
      key: 'subscribers',
      label: '登録者数',
      color: '#8a2be2',
      gradientId: 'colorSubscribers',
      gradientColor1: '#8a2be2',
      gradientColor2: '#ff007f'
    },
    views: {
      key: 'views',
      label: '総再生数',
      color: '#00bfff',
      gradientId: 'colorViews',
      gradientColor1: '#00bfff',
      gradientColor2: '#00ff7f'
    },
    videos: {
      key: 'videos',
      label: '総動画数',
      color: '#00ff7f',
      gradientId: 'colorVideos',
      gradientColor1: '#00ff7f',
      gradientColor2: '#adff2f'
    },
    weekday: {
      key: 'weekday',
      label: '曜日別',
      color: '#ffaa00',
      gradientId: 'colorWeekday',
      gradientColor1: '#ffaa00',
      gradientColor2: '#ff5500'
    }
  };

  const config = metricConfigs[metric];

  // カスタムツールチップのコンポーネント (時系列用)
  const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const metricDod: MetricDiff = data.dod[metric];
      const metricWow: MetricDiff = data.wow[metric];

      return (
        <div className={styles.customTooltip}>
          <p className={styles.tooltipDate}>{data.fullDate}</p>
          <div className={styles.tooltipMainValue} style={{ color: config.color }}>
            {config.label}: <strong>{formatMetricValue(payload[0].value as number)}</strong>
          </div>
          <div className={styles.tooltipDiffContainer}>
            <div className={styles.tooltipDiffRow}>
              <span className={styles.diffLabel}>前日比:</span>
              {metricDod.type === 'none' ? (
                <span className={styles.diffBadgeNone}>—</span>
              ) : (
                <span className={`${styles.diffBadge} ${styles[metricDod.type]}`}>
                  {metricDod.diffStr} {metricDod.rateStr}
                </span>
              )}
            </div>
            <div className={styles.tooltipDiffRow}>
              <span className={styles.diffLabel}>前週比:</span>
              {metricWow.type === 'none' ? (
                <span className={styles.diffBadgeNone}>—</span>
              ) : (
                <span className={`${styles.diffBadge} ${styles[metricWow.type]}`}>
                  {metricWow.diffStr} {metricWow.rateStr}
                </span>
              )}
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 曜日別棒グラフ専用ツールチップ
  const WeekdayCustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className={styles.customTooltip}>
          <p className={styles.tooltipDate}>{item.day_name}曜日</p>
          <div className={styles.tooltipMainValue} style={{ color: '#ffaa00' }}>
            {weekdayViewMode === 'upload' ? '動画平均再生数' : '平均日次増加量'}: <strong>{formatMetricValue(payload[0].value as number)}回</strong>
          </div>
          <div className={styles.tooltipDiffContainer}>
            <div className={styles.tooltipDiffRow}>
              <span className={styles.diffLabel}>投稿本数:</span>
              <span className={styles.diffValueBold}>{item.video_count}本</span>
            </div>
            <div className={styles.tooltipDiffRow}>
              <span className={styles.diffLabel}>該当曜日累計:</span>
              <span className={styles.diffValueBold}>{item.total_views.toLocaleString()}回</span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={styles.chartContainer}>
      <div className={styles.header}>
        {metric === 'weekday' && (
          <div className={styles.weekdayModeSwitch}>
            <button
              className={`${styles.modeBtn} ${weekdayViewMode === 'upload' ? styles.modeBtnActive : ''}`}
              onClick={() => setWeekdayViewMode('upload')}
              title="該当曜日に公開された動画の1本あたり平均再生数"
            >
              投稿曜日別
            </button>
            <button
              className={`${styles.modeBtn} ${weekdayViewMode === 'growth' ? styles.modeBtnActive : ''}`}
              onClick={() => setWeekdayViewMode('growth')}
              title="チャンネル全体の日次再生数増加量（曜日別）"
            >
              日次視聴増
            </button>
          </div>
        )}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${metric === 'subscribers' ? styles.tabActive : ''}`}
            style={metric === 'subscribers' ? { borderColor: '#8a2be2', color: '#ffffff' } : {}}
            onClick={() => setMetric('subscribers')}
          >
            登録者数
          </button>
          <button
            className={`${styles.tab} ${metric === 'views' ? styles.tabActive : ''}`}
            style={metric === 'views' ? { borderColor: '#00bfff', color: '#ffffff' } : {}}
            onClick={() => setMetric('views')}
          >
            総再生数
          </button>
          <button
            className={`${styles.tab} ${metric === 'videos' ? styles.tabActive : ''}`}
            style={metric === 'videos' ? { borderColor: '#00ff7f', color: '#ffffff' } : {}}
            onClick={() => setMetric('videos')}
          >
            動画数
          </button>
          <button
            className={`${styles.tab} ${metric === 'weekday' ? styles.tabActive : ''}`}
            style={metric === 'weekday' ? { borderColor: '#ffaa00', color: '#ffffff' } : {}}
            onClick={() => setMetric('weekday')}
            title="曜日別の平均再生数・成長傾向"
          >
            📅 曜日別
          </button>
        </div>
      </div>

      {metric === 'weekday' ? (
        <div className={styles.weekdaySection}>
          {isWeekdayLoading ? (
            <div className={styles.chartLoadingMini}>
              <div className={styles.spinnerMini}></div>
              <span>曜日別データを集計中...</span>
            </div>
          ) : weekdayStats ? (
            <>
              {/* サマリーバッジ */}
              <div className={styles.weekdaySummaryRow}>
                {weekdayViewMode === 'upload' ? (
                  <>
                    <div className={styles.summaryBadgeBest} title="最も動画平均再生数が高い投稿曜日">
                      <span className={styles.summaryBadgeLabel}>Best投稿曜日:</span>
                      <strong>{weekdayStats.best_upload_day ? `${weekdayStats.best_upload_day}曜日` : '—'}</strong>
                    </div>
                    {weekdayStats.worst_upload_day && (
                      <div className={styles.summaryBadgeWorst} title="最も動画平均再生数が低い投稿曜日">
                        <span className={styles.summaryBadgeLabel}>Worst投稿曜日:</span>
                        <strong>{weekdayStats.worst_upload_day}曜日</strong>
                      </div>
                    )}
                  </>
                ) : (
                  <div className={styles.summaryBadgeBest} title="最も日次再生数増加が大きい曜日">
                    <span className={styles.summaryBadgeLabel}>Best視聴活性曜日:</span>
                    <strong>{weekdayStats.best_growth_day ? `${weekdayStats.best_growth_day}曜日` : '—'}</strong>
                  </div>
                )}
                <span className={styles.weekdayHintText}>
                  {weekdayViewMode === 'upload' ? '※ JST基準での動画公開曜日ごとの平均' : '※ 日次データ差分の曜日別平均'}
                </span>
              </div>

              {/* 棒グラフ */}
              <div className={styles.chartWrapper}>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={weekdayStats.items} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#252525" vertical={false} />
                    <XAxis
                      dataKey="day_name"
                      stroke="#888888"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      dy={5}
                      tickFormatter={(val) => `${val}`}
                    />
                    <YAxis
                      stroke="#666666"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={formatMetricValue}
                    />
                    <Tooltip content={<WeekdayCustomTooltip />} cursor={{ fill: 'rgba(255, 170, 0, 0.08)' }} />
                    <Bar
                      dataKey={weekdayViewMode === 'upload' ? 'average_views' : 'average_daily_growth'}
                      radius={[4, 4, 0, 0]}
                    >
                      {weekdayStats.items.map((entry) => {
                        const isBest = weekdayViewMode === 'upload'
                          ? entry.day_name === weekdayStats.best_upload_day
                          : entry.day_name === weekdayStats.best_growth_day;
                        const isWorst = weekdayViewMode === 'upload' && entry.day_name === weekdayStats.worst_upload_day;

                        let fillColor = '#ffaa00'; // 通常カラー（琥珀・アンバー）
                        if (isBest) fillColor = '#00ff7f'; // Bestはネオングリーン
                        if (isWorst) fillColor = '#555566'; // Worstは落ち着いたダークグレー

                        return <Cell key={`cell-${entry.weekday}`} fill={fillColor} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <div className={styles.chartLoadingMini}>
              <span>曜日別データが取得できませんでした。</span>
            </div>
          )}
        </div>
      ) : (
        <div className={styles.chartWrapper}>
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={config.gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={config.gradientColor1} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={config.gradientColor2} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#252525" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="#666666"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dy={5}
              />
              <YAxis
                stroke="#666666"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={formatMetricValue}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={config.key}
                stroke={config.color}
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#${config.gradientId})`}
                activeDot={{ r: 4, strokeWidth: 0, fill: config.color }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
