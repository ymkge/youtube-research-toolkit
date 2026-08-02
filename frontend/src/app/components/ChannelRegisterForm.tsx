'use client';

import React, { useState } from 'react';
import { registerChannel, Channel } from '../utils/api';
import styles from './ChannelRegisterForm.module.css';

interface ChannelRegisterFormProps {
  onRegisterSuccess: (channel: Channel) => void;
}

export default function ChannelRegisterForm({ onRegisterSuccess }: ChannelRegisterFormProps) {
  const [identifier, setIdentifier] = useState('');
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
      const { channel, isNew } = await registerChannel(identifier.trim());
      if (isNew) {
        setSuccess(`「${channel.title}」を正常に登録しました！`);
      } else {
        setSuccess(`「${channel.title}」は登録済みです。最新情報に更新しました。`);
      }
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
          <div className={styles.inputRow}>
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
            <button type="submit" disabled={isLoading} className={styles.button}>
              {isLoading ? (
                <span className={styles.loadingSpinner}></span>
              ) : (
                '登録する'
              )}
            </button>
          </div>
        </div>
      </form>

      {error && <div className={styles.errorMessage}>{error}</div>}
      {success && <div className={styles.successMessage}>{success}</div>}
    </div>
  );
}
