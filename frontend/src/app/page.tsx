'use client';

import React, { useEffect, useState } from 'react';
import { fetchChannels, Channel, deleteChannel, updateChannelPin, updateChannelsSort } from './utils/api';
import ChannelRegisterForm from './components/ChannelRegisterForm';
import ChannelCard from './components/ChannelCard';
import styles from './page.module.css';

export default function Home() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<number | null>(null);

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
      </header>

      <main className={styles.main}>
        <section className={styles.registerSection}>
          <ChannelRegisterForm onRegisterSuccess={handleRegisterSuccess} />
        </section>

        <section className={styles.dashboardSection}>
          <h2 className={styles.sectionTitle}>追跡中の競合チャンネル</h2>

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
              {channels.map((channel) => (
                <ChannelCard 
                  key={channel.id} 
                  channel={channel} 
                  onDelete={handleDeleteChannel}
                  onPinToggle={handlePinToggle}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDragEnd={handleDragEnd}
                  isDraggingNow={channel.id === draggedId}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
