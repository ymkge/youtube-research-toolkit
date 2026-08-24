'use client';

import React, { useEffect, useState } from 'react';
import { fetchChannels, Channel, deleteChannel, updateChannelPin, updateChannelsSort, fetchChannelAIAnalysis, AIAnalysisResponse } from './utils/api';
import ChannelRegisterForm from './components/ChannelRegisterForm';
import ChannelCard from './components/ChannelCard';
import AIAnalysisModal from './components/AIAnalysisModal';
import GrowthComparisonView from './components/GrowthComparisonView';
import { SyncStatusBanner } from './components/SyncStatusBanner';
import { MilestoneModal } from './components/MilestoneModal';
import { LayoutDashboard, LineChart as LineChartIcon, ArrowUpDown, ArrowUp, ArrowDown, Search, X, Filter, RotateCcw, TrendingUp, TrendingDown, BarChart2, Trophy, Flame } from 'lucide-react';
import styles from './page.module.css';

type SortKey = 'custom' | 'subscribers' | 'views' | 'videos' | 'avg_views';
type SortOrder = 'desc' | 'asc';
type RankFilter = 'ALL' | 'DIAMOND' | 'GOLD' | 'SILVER' | 'BRONZE' | 'PINNED';
type TrendMetric = 'views' | 'subscribers' | 'videos';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'comparison'>('dashboard');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);

  // フィルター＆ソート＆トレンド一括表示用ステート
  const [searchQuery, setSearchQuery] = useState('');
  const [rankFilter, setRankFilter] = useState<RankFilter>('ALL');
  const [signalFilter, setSignalFilter] = useState<'ALL' | 'HOT' | 'DECLINING'>('ALL');
  const [sortBy, setSortBy] = useState<SortKey>('custom');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [isAllTrendExpanded, setIsAllTrendExpanded] = useState(false);
  const [trendMetric, setTrendMetric] = useState<TrendMetric>('views');

  // AI分析表示モーダル用のステート
  const [activeAnalysisChannel, setActiveAnalysisChannel] = useState<Channel | null>(null);
  const [isAILoading, setIsAILoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // マイルストーン表示モーダル用のステート
  const [isMilestoneModalOpen, setIsMilestoneModalOpen] = useState(false);

  // フィルター条件およびソート条件に基づいてチャンネル配列を動的に計算
  const filteredAndSortedChannels = React.useMemo(() => {
    // 1. キーワードおよびランク/ピン留め/急成長・衰退シグナルによるフィルタリング
    const filtered = channels.filter((channel) => {
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchTitle = channel.title.toLowerCase().includes(query);
        const matchUrl = channel.custom_url ? channel.custom_url.toLowerCase().includes(query) : false;
        if (!matchTitle && !matchUrl) return false;
      }

      if (signalFilter === 'HOT') {
        const isSubHot = (channel as any).daily_sub_growth !== undefined && (channel as any).daily_sub_growth >= 100;
        const isViewHot = (channel as any).daily_view_growth_rate !== undefined && (channel as any).daily_view_growth_rate >= 2.0;
        if (!isSubHot && !isViewHot) return false;
      } else if (signalFilter === 'DECLINING') {
        const isSubDeclining = (channel as any).daily_sub_growth !== undefined && (channel as any).daily_sub_growth < 0;
        const isViewDeclining = (channel as any).daily_view_growth_rate !== undefined && (channel as any).daily_view_growth_rate < 0;
        if (!isSubDeclining && !isViewDeclining) return false;
      }

      const subs = channel.subscriber_count || 0;
      switch (rankFilter) {
        case 'DIAMOND':
          return subs >= 100000;
        case 'GOLD':
          return subs >= 10000 && subs < 100000;
        case 'SILVER':
          return subs >= 1000 && subs < 10000;
        case 'BRONZE':
          return subs < 1000;
        case 'PINNED':
          return channel.is_pinned === true;
        case 'ALL':
        default:
          return true;
      }
    });

    // 2. ソート順を適用
    return filtered.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1;
      }

      if (sortBy === 'custom') {
        return a.sort_order - b.sort_order;
      }

      let valA = 0;
      let valB = 0;

      switch (sortBy) {
        case 'subscribers':
          valA = a.subscriber_count || 0;
          valB = b.subscriber_count || 0;
          break;
        case 'views':
          valA = a.view_count || 0;
          valB = b.view_count || 0;
          break;
        case 'videos':
          valA = a.video_count || 0;
          valB = b.video_count || 0;
          break;
        case 'avg_views':
          valA = a.average_views_per_video || 0;
          valB = b.average_views_per_video || 0;
          break;
      }

      return sortOrder === 'desc' ? valB - valA : valA - valB;
    });
  }, [channels, searchQuery, rankFilter, signalFilter, sortBy, sortOrder]);

  const resetFilters = () => {
    setSearchQuery('');
    setRankFilter('ALL');
    setSignalFilter('ALL');
  };

  const handleShowAIAnalysis = async (channel: Channel, forceReanalyze: boolean = false) => {
    setActiveAnalysisChannel(channel);
    setIsAILoading(true);
    setAiError(null);
    setAiAnalysis(null);

    try {
      const data = await fetchChannelAIAnalysis(channel.id, forceReanalyze);
      setAiAnalysis(data);
    } catch (err: any) {
      setAiError(err.message || 'AI分析の生成に失敗しました。');
      console.error('AI分析のロードに失敗しました:', err);
    } finally {
      setIsAILoading(false);
    }
  };

  const handleForceReanalyze = () => {
    if (activeAnalysisChannel) {
      handleShowAIAnalysis(activeAnalysisChannel, true);
    }
  };

  const loadChannels = async () => {
    try {
      setIsLoading(true);
      const data = await fetchChannels();
      setChannels(data);
    } catch (err: any) {
      setError(err.message || 'チャンネルデータの取得に失敗しました。');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadChannels();
  }, []);

  const handleRegisterSuccess = (newChannel: Channel) => {
    // すでに同じチャンネルが存在する場合は最新データに置き換え、無い場合は追加
    setChannels((prev) => {
      const exists = prev.some((c) => c.youtube_channel_id === newChannel.youtube_channel_id);
      let updatedList = [];
      if (exists) {
        updatedList = prev.map((c) =>
          c.youtube_channel_id === newChannel.youtube_channel_id ? newChannel : c
        );
      } else {
        updatedList = [...prev, newChannel];
      }

      // ピン留め順 ➔ ソート順で再ソートして整合性を維持
      return [...updatedList].sort((a, b) => {
        if (a.is_pinned !== b.is_pinned) {
          return a.is_pinned ? -1 : 1;
        }
        return a.sort_order - b.sort_order;
      });
    });
  };

  const handleDeleteChannel = async (channelId: number) => {
    try {
      await deleteChannel(channelId);
      // 削除成功時にローカルステートから除外
      setChannels((prev) => prev.filter((c) => c.id !== channelId));
    } catch (err: any) {
      alert(err.message || '削除中にエラーが発生しました。');
      throw err; // 子コンポーネントにエラーを伝える
    }
  };

  const handlePinToggle = async (channelId: number, isPinned: boolean) => {
    try {
      const updatedChannel = await updateChannelPin(channelId, isPinned);
      
      setChannels((prev) => {
        const next = prev.map((c) => (c.id === channelId ? updatedChannel : c));
        // ピン留め優先、次に sort_order 順に再ソート
        return [...next].sort((a, b) => {
          if (a.is_pinned !== b.is_pinned) {
            return a.is_pinned ? -1 : 1;
          }
          return a.sort_order - b.sort_order;
        });
      });
    } catch (err: any) {
      alert(err.message || 'ピン留めの更新に失敗しました。');
      throw err;
    }
  };

  // ドラッグ＆ドロップハンドラ
  const handleDragStart = (e: React.DragEvent, id: number) => {
    setDraggedId(id);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id.toString());
  };

  const handleDragOver = (e: React.DragEvent, overId: number) => {
    e.preventDefault();
    if (draggedId === null || draggedId === overId) return;

    setChannels((prev) => {
      const draggedIdx = prev.findIndex((c) => c.id === draggedId);
      const overIdx = prev.findIndex((c) => c.id === overId);

      if (draggedIdx === -1 || overIdx === -1) return prev;

      const draggedCard = prev[draggedIdx];
      const overCard = prev[overIdx];

      // UX向上: ピンエリアに運ばれたカードは自動でピン状態をターゲットに合わせる
      if (draggedCard.is_pinned !== overCard.is_pinned) {
        draggedCard.is_pinned = overCard.is_pinned;
      }

      const next = [...prev];
      next.splice(draggedIdx, 1);
      next.splice(overIdx, 0, draggedCard);
      return next;
    });
  };

  const handleDragEnd = async () => {
    if (draggedId === null) return;
    setDraggedId(null);
    setSortBy('custom'); // ドラッグ＆ドロップ完了時はカスタム順に復帰

    // 最終的な表示順を抽出して一括保存
    const ids = channels.map((c) => c.id);
    try {
      await updateChannelsSort(ids);

      // ピン状態がドラッグによって変わったカードをDB側にも非同期で保存
      const activeCard = channels.find((c) => c.id === draggedId);
      if (activeCard) {
        await updateChannelPin(activeCard.id, activeCard.is_pinned);
      }
    } catch (err: any) {
      console.error('並び順の保存に失敗しました:', err);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.logoArea}>
          <h1 className={styles.title}>YouTube Research Toolkit</h1>
          <p className={styles.subtitle}>
            競合チャンネルの成長プロセスを追跡し、差別化のポジショニングを分析する
          </p>
        </div>

        {/* タブナビゲーション */}
        <div className={styles.tabNav}>
          <button
            className={`${styles.tabBtn} ${activeTab === 'dashboard' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard size={16} />
            <span>ダッシュボード</span>
            {channels.length > 0 && (
              <span className={styles.tabBadge}>{channels.length}</span>
            )}
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'comparison' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('comparison')}
          >
            <LineChartIcon size={16} />
            <span>成長率比較分析</span>
          </button>

          {/* 🏆 達成マイルストーンモーダル起動ボタン */}
          <button
            className={styles.milestoneTabBtn}
            onClick={() => setIsMilestoneModalOpen(true)}
            title="1K/10K/100K到達日・達成スピード一覧を確認"
          >
            <Trophy size={16} />
            <span>達成マイルストーン</span>
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <SyncStatusBanner onRefreshData={loadChannels} />
        {activeTab === 'dashboard' ? (
          <>
            <section className={styles.registerSection}>
              <ChannelRegisterForm onRegisterSuccess={handleRegisterSuccess} />
            </section>

            <section className={styles.dashboardSection}>
              <div className={styles.sectionHeader}>
                <div className={styles.titleInfo}>
                  <h2 className={styles.sectionTitle}>追跡中の競合チャンネル</h2>
                  {!isLoading && (
                    <span className={styles.countBadge}>
                      表示: <strong>{filteredAndSortedChannels.length}</strong> / {channels.length} 件
                    </span>
                  )}
                </div>

                {/* 検索・フィルター ＆ ソートコントロール */}
                {!isLoading && channels.length > 0 && (
                  <div className={styles.controlsRow}>
                    {/* キーワード検索窓 */}
                    <div className={styles.searchWrapper}>
                      <Search size={14} className={styles.searchIcon} />
                      <input
                        type="text"
                        placeholder="チャンネル名・ハンドル名で検索..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className={styles.searchInput}
                      />
                      {searchQuery && (
                        <button onClick={() => setSearchQuery('')} className={styles.clearSearchBtn} title="検索文字をクリア">
                          <X size={12} />
                        </button>
                      )}
                    </div>

                    {/* 規模ランク・ピン留めフィルターチップ */}
                    <div className={styles.filterChipGroup}>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'ALL' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('ALL')}
                      >
                        すべて
                      </button>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'DIAMOND' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('DIAMOND')}
                        title="登録者数 10万人以上"
                      >
                        💎 10万+
                      </button>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'GOLD' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('GOLD')}
                        title="登録者数 1万人〜10万人未満"
                      >
                        🥇 1万+
                      </button>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'SILVER' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('SILVER')}
                        title="登録者数 1,000人〜1万人未満"
                      >
                        🥈 1千+
                      </button>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'BRONZE' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('BRONZE')}
                        title="登録者数 1,000人未満"
                      >
                        🥉 1千未満
                      </button>
                      <button
                        className={`${styles.filterChip} ${rankFilter === 'PINNED' ? styles.chipActive : ''}`}
                        onClick={() => setRankFilter('PINNED')}
                        title="ピン留め済みチャンネルのみ表示"
                      >
                        📌 ピン留め
                      </button>
                      <button
                        className={`${styles.filterChip} ${styles.hotFilterChip} ${signalFilter === 'HOT' ? styles.hotChipActive : ''}`}
                        onClick={() => setSignalFilter(signalFilter === 'HOT' ? 'ALL' : 'HOT')}
                        title="前日比で登録者+100名以上または再生数+2.0%以上急増中のチャンネル"
                      >
                        🔥 急成長 ({channels.filter(c => ((c as any).daily_sub_growth ?? 0) >= 100 || ((c as any).daily_view_growth_rate ?? 0) >= 2.0).length})
                      </button>
                      <button
                        className={`${styles.filterChip} ${styles.declineFilterChip} ${signalFilter === 'DECLINING' ? styles.declineChipActive : ''}`}
                        onClick={() => setSignalFilter(signalFilter === 'DECLINING' ? 'ALL' : 'DECLINING')}
                        title="前日比で登録者数が減少中の衰退チャンネル"
                      >
                        📉 衰退 ({channels.filter(c => ((c as any).daily_sub_growth ?? 0) < 0 || ((c as any).daily_view_growth_rate ?? 0) < 0).length})
                      </button>
                    </div>

                    {/* トレンドグラフ一括制御（トグルボタン ＆ 指標選択ドロップダウンの一体化グループ） */}
                    <div className={styles.trendControlGroup}>
                      <button
                        onClick={() => setIsAllTrendExpanded(!isAllTrendExpanded)}
                        className={`${styles.toggleAllTrendsBtn} ${isAllTrendExpanded ? styles.toggleActive : ''}`}
                        title={isAllTrendExpanded ? "表示中のチャンネルのトレンド表示を一括で閉じる" : "表示中のチャンネルのトレンド表示を一括で展開"}
                      >
                        {isAllTrendExpanded ? (
                          <>
                            <TrendingDown size={14} />
                            <span>一括閉じる</span>
                          </>
                        ) : (
                          <>
                            <TrendingUp size={14} />
                            <span>トレンド一括表示</span>
                          </>
                        )}
                      </button>

                      <div className={styles.trendMetricSelectWrapper}>
                        <BarChart2 size={14} className={styles.trendMetricIcon} />
                        <select
                          value={trendMetric}
                          onChange={(e) => setTrendMetric(e.target.value as TrendMetric)}
                          className={styles.trendMetricSelect}
                          title="一括表示・切替する統計指標を選択"
                        >
                          <option value="views">🎬 指標: 総再生数</option>
                          <option value="subscribers">👥 指標: 登録者数</option>
                          <option value="videos">📹 指標: 動画数</option>
                        </select>
                      </div>
                    </div>

                    {/* ソートコントロール */}
                    <div className={styles.sortControlGroup}>
                      <div className={styles.sortSelectWrapper}>
                        <ArrowUpDown size={14} className={styles.sortIcon} />
                        <select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value as SortKey)}
                          className={styles.sortSelect}
                          title="並び替え基準を選択"
                        >
                          <option value="custom">カスタム順 (手動ドラッグ順)</option>
                          <option value="subscribers">登録者数順</option>
                          <option value="views">総再生数順</option>
                          <option value="videos">動画数順</option>
                          <option value="avg_views">平均再生数順</option>
                        </select>
                      </div>

                      {sortBy !== 'custom' && (
                        <button
                          onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                          className={styles.sortOrderBtn}
                          title={sortOrder === 'desc' ? '多い順 (降順) -> 少ない順に切替' : '少ない順 (昇順) -> 多い順に切替'}
                        >
                          {sortOrder === 'desc' ? (
                            <>
                              <ArrowDown size={14} />
                              <span>多い順</span>
                            </>
                          ) : (
                            <>
                              <ArrowUp size={14} />
                              <span>少ない順</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {isLoading ? (
                <div className={styles.loadingArea}>
                  <span className={styles.spinner}></span>
                  <p>チャンネルデータを読み込み中...</p>
                </div>
              ) : error ? (
                <div className={styles.errorArea}>
                  <p>{error}</p>
                  <button onClick={loadChannels} className={styles.retryButton}>
                    再試行
                  </button>
                </div>
              ) : channels.length === 0 ? (
                <div className={styles.emptyArea}>
                  <p>現在追跡中のチャンネルはありません。</p>
                  <p className={styles.emptyTip}>
                    上のフォームから、競合チャンネルのID（UC...）またはハンドル名（@...）を登録してください。
                  </p>
                </div>
              ) : filteredAndSortedChannels.length === 0 ? (
                <div className={styles.emptyFilterState}>
                  <Filter size={32} className={styles.emptyFilterIcon} />
                  <h3>条件に一致するチャンネルが見つかりませんでした</h3>
                  <p>検索キーワードや指定されたフィルター条件を変更してお試しください。</p>
                  <button onClick={resetFilters} className={styles.resetFilterBtn}>
                    <RotateCcw size={14} />
                    <span>フィルターをリセット</span>
                  </button>
                </div>
              ) : (
                <div className={styles.grid}>
                  {filteredAndSortedChannels.map((channel) => (
                    <ChannelCard 
                      key={channel.id} 
                      channel={channel} 
                      onDelete={handleDeleteChannel}
                      onPinToggle={handlePinToggle}
                      onDragStart={handleDragStart}
                      onDragOver={handleDragOver}
                      onDragEnd={handleDragEnd}
                      isDraggingNow={channel.id === draggedId}
                      onShowAIAnalysis={handleShowAIAnalysis}
                      isAllTrendExpanded={isAllTrendExpanded}
                      allTrendMetric={trendMetric}
                    />
                  ))}
                </div>
              )}
            </section>
          </>
        ) : (
          <section className={styles.comparisonSection}>
            <GrowthComparisonView />
          </section>
        )}
      </main>

      {/* 🤖 AI分析結果詳細モーダル */}
      <AIAnalysisModal
        isOpen={activeAnalysisChannel !== null}
        onClose={() => setActiveAnalysisChannel(null)}
        isLoading={isAILoading}
        error={aiError}
        analysis={aiAnalysis}
        channelTitle={activeAnalysisChannel?.title || ''}
        onReanalyze={handleForceReanalyze}
      />

      {/* 🏆 マイルストーン達成日一覧モーダル */}
      <MilestoneModal
        isOpen={isMilestoneModalOpen}
        onClose={() => setIsMilestoneModalOpen(false)}
      />
    </div>
  );
}
