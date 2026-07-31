import React, { useEffect, useState, useMemo } from 'react';
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
import { TrendingUp, Users, Play, CheckSquare, Square, RefreshCw, AlertCircle, Filter, Search, X } from 'lucide-react';

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
  // ホバー（強調表示）中のチャンネルID
  const [hoveredChannelId, setHoveredChannelId] = useState<number | null>(null);
  // 自由入力カスタム登録者数フィルター
  const [customMinSubs, setCustomMinSubs] = useState<string>('');
  // 左サイドバーチャンネル検索クエリ
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredChannels = useMemo(() => {
    if (!data) return [];
    if (!searchQuery.trim()) return data.channels;
    const query = searchQuery.toLowerCase().trim();
    return data.channels.filter((c) => {
      const matchTitle = c.title.toLowerCase().includes(query);
      const matchUrl = c.custom_url ? c.custom_url.toLowerCase().includes(query) : false;
      return matchTitle || matchUrl;
    });
  }, [data, searchQuery]);

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
    const targetIds = filteredChannels.filter((c) => c.has_history).map((c) => c.id);
    if (!searchQuery.trim()) {
      setSelectedChannelIds(targetIds);
    } else {
      setSelectedChannelIds((prev) => Array.from(new Set([...prev, ...targetIds])));
    }
  };

  const deselectAll = () => {
    if (!data) return;
    if (!searchQuery.trim()) {
      setSelectedChannelIds([]);
    } else {
      const targetIdsSet = new Set(filteredChannels.map((c) => c.id));
      setSelectedChannelIds((prev) => prev.filter((id) => !targetIdsSet.has(id)));
    }
  };

  // ランク別およびピン留めのワンタップ一括選択ハンドラー
  const selectByFilter = (filterType: '100k' | '10k' | '1k' | 'pinned') => {
    if (!data) return;
    const matchedIds = data.channels
      .filter((c) => c.has_history)
      .filter((c) => {
        const subs = c.subscriber_count || 0;
        switch (filterType) {
          case '100k':
            return subs >= 100000;
          case '10k':
            return subs >= 10000;
          case '1k':
            return subs >= 1000;
          case 'pinned':
            return !!c.is_pinned;
          default:
            return true;
        }
      })
      .map((c) => c.id);

    setSelectedChannelIds(matchedIds);
  };

  // 自由数値入力の適用ハンドラー
  const applyCustomMinSubsFilter = (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    const minVal = parseInt(customMinSubs, 10);
    if (isNaN(minVal) || minVal < 0) return;

    const matchedIds = data.channels
      .filter((c) => c.has_history)
      .filter((c) => (c.subscriber_count || 0) >= minVal)
      .map((c) => c.id);

    setSelectedChannelIds(matchedIds);
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
    }
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
    }
    return null;
  };

  return (
    <div className={styles.container}>
      <div className={styles.mainLayout}>
        {/* 左側: スクロール追従 (Sticky) フィルターサイドバー */}
        <aside className={styles.sidebar}>
          <div className={styles.controlPanel}>
            <div className={styles.controlHeader}>
              <h3>
                <TrendingUp size={18} className={styles.iconTrend} />
                <span>比較フィルター</span>
              </h3>
              <div className={styles.btnGroup}>
                <button onClick={selectAll} className={styles.actionBtn}>
                  <CheckSquare size={13} /> 全選択
                </button>
                <button onClick={deselectAll} className={styles.actionBtn}>
                  <Square size={13} /> 全解除
                </button>
              </div>
            </div>

            {/* 💎 規模別ワンタップ一括フィルター */}
            <div className={styles.quickFilterSection}>
              <span className={styles.filterSectionLabel}>規模別一括選択:</span>
              <div className={styles.quickFilterGrid}>
                <button onClick={() => selectByFilter('100k')} className={styles.quickFilterBtn} title="登録者10万人以上のチャンネルを全選択">
                  💎 10万+
                </button>
                <button onClick={() => selectByFilter('10k')} className={styles.quickFilterBtn} title="登録者1万人以上のチャンネルを全選択">
                  🥇 1万+
                </button>
                <button onClick={() => selectByFilter('1k')} className={styles.quickFilterBtn} title="登録者1,000人以上のチャンネルを全選択">
                  🥈 1千+
                </button>
                <button onClick={() => selectByFilter('pinned')} className={styles.quickFilterBtn} title="ピン留めされているチャンネルを全選択">
                  📌 ピン留め
                </button>
              </div>
            </div>

            {/* 自由数値入力カスタムフィルター */}
            <form onSubmit={applyCustomMinSubsFilter} className={styles.customFilterForm}>
              <div className={styles.inputWrapper}>
                <Filter size={13} className={styles.filterInputIcon} />
                <input
                  type="number"
                  placeholder="登録者数 (例: 5000)"
                  value={customMinSubs}
                  onChange={(e) => setCustomMinSubs(e.target.value)}
                  className={styles.customInput}
                  min="0"
                />
                <span className={styles.inputUnit}>人以上</span>
              </div>
              <button type="submit" className={styles.applyBtn}>
                適用
              </button>
            </form>

            {/* チャンネルリスト検索窓 */}
            <div className={styles.sidebarSearchWrapper}>
              <Search size={13} className={styles.sidebarSearchIcon} />
              <input
                type="text"
                placeholder="チャンネル名・ハンドルで検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.sidebarSearchInput}
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className={styles.clearSidebarSearchBtn} title="検索をクリア">
                  <X size={12} />
                </button>
              )}
            </div>

            {/* チャンネル選択バッジ一覧 */}
            <div className={styles.filterGrid}>
              {filteredChannels.length === 0 ? (
                <div className={styles.noSearchResult}>
                  <span>一致するチャンネルがありません</span>
                </div>
              ) : (
                filteredChannels.map((channel) => {
                  const isSelected = selectedChannelIds.includes(channel.id);
                  const isHovered = hoveredChannelId === channel.id;
                  const disabled = !channel.has_history;

                return (
                  <button
                    key={channel.id}
                    onClick={() => !disabled && toggleChannel(channel.id)}
                    onMouseEnter={() => !disabled && setHoveredChannelId(channel.id)}
                    onMouseLeave={() => setHoveredChannelId(null)}
                    disabled={disabled}
                    className={`${styles.filterChip} ${isSelected ? styles.chipSelected : ''} ${
                      isHovered ? styles.chipHovered : ''
                    } ${disabled ? styles.chipDisabled : ''}`}
                    style={{
                      borderColor: isSelected ? channel.color : 'transparent',
                    }}
                  >
                    <span
                      className={styles.colorDot}
                      style={{ backgroundColor: disabled ? '#444' : channel.color }}
                    />
                    <span className={styles.dashIndicator} style={{ color: channel.color }}>
                      {channel.dash_pattern === 'none' ? '━' : '╌'}
                    </span>
                    <span className={styles.chipTitle}>{channel.title}</span>
                    {disabled && <span className={styles.disabledLabel}>(データなし)</span>}
                  </button>
                );
              }))}
            </div>
          </div>
        </aside>

        {/* 右側: 2連並列グラフエリア */}
        <main className={styles.contentArea}>
          <div className={styles.chartsGrid}>
            {/* 上段: 登録者数 成長率グラフ */}
            <div className={styles.chartCard}>
              <div className={styles.chartHeader}>
                <Users size={18} className={styles.iconUsers} />
                <h4>登録者数の累積成長率 (%) 比較</h4>
              </div>
              <div className={styles.chartBody}>
                <ResponsiveContainer width="100%" height={340}>
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
                    {selectedChannels.map((channel) => {
                      const isHovered = hoveredChannelId === channel.id;
                      const hasHovered = hoveredChannelId !== null;
                      return (
                        <Line
                          key={channel.id}
                          type="monotone"
                          dataKey={`sub_growth_${channel.id}`}
                          name={channel.title}
                          stroke={channel.color}
                          strokeWidth={isHovered ? 4.5 : 2.5}
                          strokeOpacity={hasHovered ? (isHovered ? 1.0 : 0.15) : 1.0}
                          strokeDasharray={
                            channel.dash_pattern === 'none' ? undefined : channel.dash_pattern
                          }
                          dot={{
                            r: isHovered ? 5 : 3,
                            fill: channel.color,
                            fillOpacity: hasHovered ? (isHovered ? 1.0 : 0.2) : 1.0,
                          }}
                          activeDot={{ r: 7 }}
                        />
                      );
                    })}
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
                <ResponsiveContainer width="100%" height={340}>
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
                    {selectedChannels.map((channel) => {
                      const isHovered = hoveredChannelId === channel.id;
                      const hasHovered = hoveredChannelId !== null;
                      return (
                        <Line
                          key={channel.id}
                          type="monotone"
                          dataKey={`view_growth_${channel.id}`}
                          name={channel.title}
                          stroke={channel.color}
                          strokeWidth={isHovered ? 4.5 : 2.5}
                          strokeOpacity={hasHovered ? (isHovered ? 1.0 : 0.15) : 1.0}
                          strokeDasharray={
                            channel.dash_pattern === 'none' ? undefined : channel.dash_pattern
                          }
                          dot={{
                            r: isHovered ? 5 : 3,
                            fill: channel.color,
                            fillOpacity: hasHovered ? (isHovered ? 1.0 : 0.2) : 1.0,
                          }}
                          activeDot={{ r: 7 }}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
