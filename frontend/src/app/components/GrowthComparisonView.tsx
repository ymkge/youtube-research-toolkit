import React, { useEffect, useState } from 'react';
import { fetchChannelsComparison, ChannelsComparisonResponse, ComparisonChannelItem } from '../utils/api';
import styles from './GrowthComparisonView.module.css';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Users, Play, CheckSquare, Square, RefreshCw, AlertCircle } from 'lucide-react';

// 数値を読みやすい単位（万、億）にフォーマット
function formatNumber(num: number): string {
  if (num >= 100000000) {
    return `${(num / 100000000).toFixed(1)}億`;
  }
  if (num >= 10000) {
    return `${(num / 10000).toFixed(1)}万`;
  }
  return num.toLocaleString();
}

export default function GrowthComparisonView() {
  const [data, setData] = useState<ChannelsComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 選択されたチャンネルIDのセット
  const [selectedChannelIds, setSelectedChannelIds] = useState<number[]>([]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchChannelsComparison();
      setData(res);
      // デフォルトでは履歴がある全チャンネルを選択状態にする
      const historyChannelIds = res.channels.filter((c) => c.has_history).map((c) => c.id);
      setSelectedChannelIds(historyChannelIds);
    } catch (err: any) {
      setError(err.message || 'データの読み込みに失敗しました。');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleChannel = (id: number) => {
    setSelectedChannelIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (!data) return;
    const historyChannelIds = data.channels.filter((c) => c.has_history).map((c) => c.id);
    setSelectedChannelIds(historyChannelIds);
  };

  const deselectAll = () => {
    setSelectedChannelIds([]);
  };

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <span className={styles.spinner}></span>
        <p>全チャンネルの成長率データを集計中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <AlertCircle size={24} className={styles.errorIcon} />
        <p>{error}</p>
        <button onClick={loadData} className={styles.retryBtn}>
          <RefreshCw size={14} /> 再試行
        </button>
      </div>
    );
  }

  if (!data || data.timeline.length === 0) {
    return (
      <div className={styles.emptyContainer}>
        <p>成長率を比較するための時系列履歴データがまだありません。</p>
        <p className={styles.emptyTip}>日次自動同期や動画登録が進むと、ここに比較グラフが自動描画されます。</p>
      </div>
    );
  }

  // 選択されたチャンネルオブジェクト一覧
  const selectedChannels = data.channels.filter((c) => selectedChannelIds.includes(c.id));

  // カスタムツールチップ (登録者数用)
  const CustomSubTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={styles.customTooltip}>
          <p className={styles.tooltipDate}>{label}</p>
          <div className={styles.tooltipList}>
            {payload.map((entry: any, index: number) => {
              const channelId = entry.dataKey.replace('sub_growth_', '');
              const channel = data.channels.find((c) => c.id.toString() === channelId);
              const rawCount = entry.payload[`subscribers_${channelId}`];
              return (
                <div key={index} className={styles.tooltipItem} style={{ color: entry.color }}>
                  <span className={styles.tooltipName}>{channel?.title || entry.name}:</span>
                  <span className={styles.tooltipGrowth}>
                    {entry.value >= 0 ? `+${entry.value}%` : `${entry.value}%`}
                  </span>
                  {rawCount !== undefined && (
                    <span className={styles.tooltipRaw}>({formatNumber(rawCount)}人)</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    };
    return null;
  };

  // カスタムツールチップ (総再生数用)
  const CustomViewTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={styles.customTooltip}>
          <p className={styles.tooltipDate}>{label}</p>
          <div className={styles.tooltipList}>
            {payload.map((entry: any, index: number) => {
              const channelId = entry.dataKey.replace('view_growth_', '');
              const channel = data.channels.find((c) => c.id.toString() === channelId);
              const rawCount = entry.payload[`views_${channelId}`];
              return (
                <div key={index} className={styles.tooltipItem} style={{ color: entry.color }}>
                  <span className={styles.tooltipName}>{channel?.title || entry.name}:</span>
                  <span className={styles.tooltipGrowth}>
                    {entry.value >= 0 ? `+${entry.value}%` : `${entry.value}%`}
                  </span>
                  {rawCount !== undefined && (
                    <span className={styles.tooltipRaw}>({formatNumber(rawCount)}回)</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    };
    return null;
  };

  return (
    <div className={styles.container}>
      {/* ヘッダー・フィルタコントロール */}
      <div className={styles.controlPanel}>
        <div className={styles.controlHeader}>
          <h3>
            <TrendingUp size={18} className={styles.iconTrend} />
            <span>比較フィルター (表示チャンネルの選択)</span>
          </h3>
          <div className={styles.btnGroup}>
            <button onClick={selectAll} className={styles.actionBtn}>
              <CheckSquare size={14} /> 全選択
            </button>
            <button onClick={deselectAll} className={styles.actionBtn}>
              <Square size={14} /> 全解除
            </button>
          </div>
        </div>

        {/* チャンネル選択バッジ */}
        <div className={styles.filterGrid}>
          {data.channels.map((channel) => {
            const isSelected = selectedChannelIds.includes(channel.id);
            const disabled = !channel.has_history;

            return (
              <button
                key={channel.id}
                onClick={() => !disabled && toggleChannel(channel.id)}
                disabled={disabled}
                className={`${styles.filterChip} ${isSelected ? styles.chipSelected : ''} ${
                  disabled ? styles.chipDisabled : ''
                }`}
                style={{
                  borderColor: isSelected ? channel.color : 'transparent',
                }}
              >
                <span
                  className={styles.colorDot}
                  style={{ backgroundColor: disabled ? '#444' : channel.color }}
                />
                <span className={styles.chipTitle}>{channel.title}</span>
                {disabled && <span className={styles.disabledLabel}>(データなし)</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2連並列グラフ */}
      <div className={styles.chartsGrid}>
        {/* 上段: 登録者数 成長率グラフ */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <Users size={18} className={styles.iconUsers} />
            <h4>登録者数の累積成長率 (%) 比較</h4>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={data.timeline} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="date" stroke="#777777" tick={{ fontSize: 11 }} />
                <YAxis
                  stroke="#777777"
                  tick={{ fontSize: 11 }}
                  unit="%"
                  domain={['auto', 'auto']}
                />
                <Tooltip content={<CustomSubTooltip />} />
                {selectedChannels.map((channel) => (
                  <Line
                    key={channel.id}
                    type="monotone"
                    dataKey={`sub_growth_${channel.id}`}
                    name={channel.title}
                    stroke={channel.color}
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: channel.color }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 下段: 総再生数 成長率グラフ */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <Play size={18} className={styles.iconPlay} />
            <h4>総再生数の累積成長率 (%) 比較</h4>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={data.timeline} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="date" stroke="#777777" tick={{ fontSize: 11 }} />
                <YAxis
                  stroke="#777777"
                  tick={{ fontSize: 11 }}
                  unit="%"
                  domain={['auto', 'auto']}
                />
                <Tooltip content={<CustomViewTooltip />} />
                {selectedChannels.map((channel) => (
                  <Line
                    key={channel.id}
                    type="monotone"
                    dataKey={`view_growth_${channel.id}`}
                    name={channel.title}
                    stroke={channel.color}
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: channel.color }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
