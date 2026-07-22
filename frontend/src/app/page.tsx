'use client';

import React, { useEffect, useState } from 'react';
import { fetchChannels, Channel, deleteChannel } from './utils/api';
import ChannelRegisterForm from './components/ChannelRegisterForm';
import ChannelCard from './components/ChannelCard';
import styles from './page.module.css';

export default function Home() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      if (exists) {
        return prev.map((c) =>
          c.youtube_channel_id === newChannel.youtube_channel_id ? newChannel : c
        );
      }
      return [...prev, newChannel];
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
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
