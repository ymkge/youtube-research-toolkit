'use client';

import React, { useState } from 'react';
import { registerChannel, Channel } from '../utils/api';
import styles from './ChannelRegisterForm.module.css';

interface ChannelRegisterFormProps {
  onRegisterSuccess: (channel: Channel) => void;
}

export default function ChannelRegisterForm({ onRegisterSuccess }: ChannelRegisterFormProps) {
  const [identifier, setIdentifier] = useState('');
  const [importLimit, setImportLimit] = useState(50);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) return;

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const channel = await registerChannel(identifier.trim(), importLimit);
      setSuccess(`「${channel.title}」を正常に登録しました！`);
      setIdentifier('');
      onRegisterSuccess(channel);
    } catch (err: any) {
      setError(err.message || '登録中にエラーが発生しました。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.inputGroup}>
          <label htmlFor="identifier" className={styles.label}>
            競合のチャンネルID または ハンドル
          </label>
          <input
            type="text"
            id="identifier"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="例: @Google または UC_x5XG..."
            disabled={isLoading}
            className={styles.input}
            required
          />
        </div>

        <div className={styles.inputGroupLimit}>
          <label htmlFor="importLimit" className={styles.label}>
            初期同期動画数
          </label>
          <select
            id="importLimit"
            value={importLimit}
            onChange={(e) => setImportLimit(Number(e.target.value))}
            disabled={isLoading}
            className={styles.select}
          >
            <option value={10}>10 件</option>
            <option value={30}>30 件</option>
            <option value={50}>50 件</option>
            <option value={100}>100 件</option>
          </select>
        </div>

        <button type="submit" disabled={isLoading} className={styles.button}>
          {isLoading ? (
            <span className={styles.loadingSpinner}></span>
          ) : (
            '登録する'
          )}
        </button>
      </form>

      {error && <div className={styles.errorMessage}>{error}</div>}
      {success && <div className={styles.successMessage}>{success}</div>}
    </div>
  );
}
