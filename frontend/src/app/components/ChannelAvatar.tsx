'use client';

import React, { useState, useEffect } from 'react';
import styles from './ChannelAvatar.module.css';

interface ChannelAvatarProps {
  src?: string | null;
  title: string;
  size?: number; // デフォルト 44px
  className?: string;
  draggable?: boolean;
}

// チャンネル名から一貫したグラデーション背景を生成
const GRADIENT_PALETTES = [
  'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)', // Indigo to Purple
  'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)', // Blue to Cyan
  'linear-gradient(135deg, #10b981 0%, #059669 100%)', // Emerald
  'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', // Amber
  'linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)', // Pink to Violet
  'linear-gradient(135deg, #f43f5e 0%, #fb7185 100%)', // Rose
  'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)', // Violet
  'linear-gradient(135deg, #14b8a6 0%, #0284c7 100%)', // Teal to Light Blue
];

function getGradientForTitle(title: string): string {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % GRADIENT_PALETTES.length;
  return GRADIENT_PALETTES[index];
}

function getInitialLetter(title: string): string {
  if (!title) return '?';
  // 絵文字や記号を取り除いて最初の有効文字を取得
  const cleanTitle = title.replace(/[【】\[\]\s（）()!！?？]/g, '');
  if (!cleanTitle) return title.charAt(0) || '?';
  return cleanTitle.charAt(0);
}

export const ChannelAvatar: React.FC<ChannelAvatarProps> = ({
  src,
  title,
  size = 44,
  className = '',
  draggable = false,
}) => {
  // ロード段階: 'initial' | 'fallback_size' | 'error'
  const [loadStage, setLoadStage] = useState<'initial' | 'fallback_size' | 'error'>('initial');
  const [currentSrc, setCurrentSrc] = useState<string | null>(src || null);

  useEffect(() => {
    setCurrentSrc(src || null);
    setLoadStage('initial');
  }, [src]);

  const handleError = () => {
    if (loadStage === 'initial' && currentSrc) {
      // 段階1: もし =s800 などの指定があれば、=s176 (標準サムネイルサイズ) に変更して再試行
      if (currentSrc.includes('=s')) {
        const lowerResSrc = currentSrc.replace(/=s\d+/, '=s176');
        if (lowerResSrc !== currentSrc) {
          setLoadStage('fallback_size');
          setCurrentSrc(lowerResSrc);
          return;
        }
      }
    }
    // 段階2: 最終フォールバック（グラデーション頭文字アバター）へ移行
    setLoadStage('error');
  };

  const initialChar = getInitialLetter(title);
  const gradientBg = getGradientForTitle(title);
  const fontSize = Math.max(12, Math.round(size * 0.42));

  // 画像がない、または読み込み失敗時はフォールバックアバターを表示
  if (!currentSrc || loadStage === 'error') {
    return (
      <div
        className={`${styles.avatarWrapper} ${className}`}
        style={{
          width: size,
          height: size,
          background: gradientBg,
        }}
        title={title}
      >
        <span
          className={styles.fallbackAvatar}
          style={{ fontSize: `${fontSize}px` }}
        >
          {initialChar}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`${styles.avatarWrapper} ${className}`}
      style={{
        width: size,
        height: size,
      }}
      title={title}
    >
      <img
        src={currentSrc}
        alt="" // 破損時に文字が露出するのを完全に防ぐため alt は空文字、wrapper の title 属性でツールチップ表示
        className={styles.avatarImage}
        onError={handleError}
        referrerPolicy="no-referrer"
        loading="lazy"
        draggable={draggable}
      />
    </div>
  );
};

export default ChannelAvatar;
