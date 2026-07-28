'use client';

import React, { useEffect, useState } from 'react';
import { fetchChannels, Channel, deleteChannel, updateChannelPin, updateChannelsSort, fetchChannelAIAnalysis, AIAnalysisResponse } from './utils/api';
import ChannelRegisterForm from './components/ChannelRegisterForm';
import ChannelCard from './components/ChannelCard';
import AIAnalysisModal from './components/AIAnalysisModal';
import GrowthComparisonView from './components/GrowthComparisonView';
import { LayoutDashboard, LineChart as LineChartIcon, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import styles from './page.module.css';

type SortKey = 'custom' | 'subscribers' | 'views' | 'videos' | 'avg_views';
type SortOrder = 'desc' | 'asc';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'comparison'>('dashboard');
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);

  // ソート用ステート
  const [sortBy, setSortBy] = useState<SortKey>('custom');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // AI分析表示モーダル用のステート
  const [activeAnalysisChannel, setActiveAnalysisChannel] = useState<Channel | null>(null);
  const [isAILoading, setIsAILoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysisResponse | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // ソート条件に基づいてチャンネル配列を動的に並び替え
  const sortedChannels = React.useMemo(() => {
    return [...channels].sort((a, b) => {
      // 1. ピン留め優先制御 (ピン留めされているものが常に上)
      if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1;
      }

      // 2. カスタム順 (標準ドラッグ順) の場合
      if (sortBy === 'custom') {
        return a.sort_order - b.sort_order;
      }

      // 3. 各指標の数値比較
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
  }, [channels, sortBy, sortOrder]);

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
        </div>
      </header>

      <main className={styles.main}>
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
                      登録中: <strong>{channels.length}</strong> 件
                    </span>
                  )}
                </div>

                {/* ソートコントロール */}
                {!isLoading && channels.length > 0 && (
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
              ) : (
                <div className={styles.grid}>
                  {sortedChannels.map((channel) => (
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
    </div>
  );
}
