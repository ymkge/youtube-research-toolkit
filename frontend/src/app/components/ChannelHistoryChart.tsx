'use client';

import React, { useState, useEffect } from 'react';
import { ChannelStatsHistory } from '../utils/api';
import styles from './ChannelHistoryChart.module.css';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  TooltipProps
} from 'recharts';

type MetricType = 'subscribers' | 'views' | 'videos';

interface ChannelHistoryChartProps {
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

export default function ChannelHistoryChart({ history, isLoading, initialMetric = 'subscribers' }: ChannelHistoryChartProps) {
  const [metric, setMetric] = useState<MetricType>(initialMetric);

  useEffect(() => {
    if (initialMetric) {
      setMetric(initialMetric);
    }
  }, [initialMetric]);

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

  // グラフ用データの構築
  const chartData = history.map((item) => ({
    date: formatChartDate(item.recorded_at),
    fullDate: item.recorded_at.replace(/-/g, '/'),
    subscribers: item.subscriber_count,
    views: item.view_count,
    videos: item.video_count
  }));

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
    }
  };

  const config = metricConfigs[metric];

  // カスタムツールチップのコンポーネント
  const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className={styles.customTooltip}>
          <p className={styles.tooltipDate}>{data.fullDate}</p>
          <p className={styles.tooltipValue} style={{ color: config.color }}>
            {config.label}: <strong>{formatMetricValue(payload[0].value as number)}</strong>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={styles.chartContainer}>
      <div className={styles.header}>
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
        </div>
      </div>

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
    </div>
  );
}
