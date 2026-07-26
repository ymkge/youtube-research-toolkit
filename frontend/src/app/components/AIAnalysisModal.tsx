import React, { useEffect } from 'react';
import { AIAnalysisResponse } from '../utils/api';
import styles from './AIAnalysisModal.module.css';
import { Sparkles, Brain, AlertCircle, CheckCircle2, Trophy, ArrowRight, X } from 'lucide-react';

interface AIAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  isLoading: boolean;
  error: string | null;
  analysis: AIAnalysisResponse | null;
  channelTitle: string;
}

export default function AIAnalysisModal({
  isOpen,
  onClose,
  isLoading,
  error,
  analysis,
  channelTitle,
}: AIAnalysisModalProps) {
  // モーダルが開いている間、背景のスクロールをロックする
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* モーダルヘッダー */}
        <div className={styles.header}>
          <div className={styles.titleInfo}>
            <Brain className={styles.brainIcon} size={20} />
            <div>
              <h3>AIポジショニング分析レポート</h3>
              <p className={styles.subtitle}>対象チャンネル: {channelTitle}</p>
            </div>
          </div>
          <button className={styles.closeButton} onClick={onClose} title="閉じる">
            <X size={20} />
          </button>
        </div>

        {/* モーダルコンテンツ */}
        <div className={styles.content}>
          {/* ローディングスケルトン */}
          {isLoading && (
            <div className={styles.skeletonContainer}>
              <div className={styles.skeletonTitle}>
                <Sparkles className={styles.skeletonIcon} size={16} />
                <span>AIが動画データを定量・定性的に分析中...</span>
              </div>
              <div className={styles.skeletonLine} style={{ width: '90%' }}></div>
              <div className={styles.skeletonLine} style={{ width: '80%' }}></div>
              <div className={styles.skeletonLine} style={{ width: '85%' }}></div>
              <div className={styles.skeletonGrid}>
                <div className={styles.skeletonCard}></div>
                <div className={styles.skeletonCard}></div>
              </div>
            </div>
          )}

          {/* エラー表示 */}
          {error && (
            <div className={styles.errorContainer}>
              <AlertCircle size={20} className={styles.errorIcon} />
              <div className={styles.errorText}>
                <h4>分析レポートの作成に失敗しました</h4>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* 正常系レポート表示 */}
          {!isLoading && !error && analysis && (
            <div className={styles.reportContent}>
              {/* 1行要約 */}
              <div className={styles.summarySection}>
                <p className={styles.summaryText}>{analysis.channel_summary}</p>
              </div>

              {/* 強みと弱みの2カラム */}
              <div className={styles.grid2}>
                <div className={`${styles.card} ${styles.cardStrength}`}>
                  <h4>
                    <CheckCircle2 size={16} className={styles.cardIconStrength} />
                    <span>競合独自の強み</span>
                  </h4>
                  <ul>
                    {analysis.strengths.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className={`${styles.card} ${styles.cardWeakness}`}>
                  <h4>
                    <AlertCircle size={16} className={styles.cardIconWeakness} />
                    <span>弱み・未開拓領域</span>
                  </h4>
                  <ul>
                    {analysis.weaknesses.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 主要なヒットテーマ */}
              <div className={styles.section}>
                <h4 className={styles.sectionTitle}>
                  <Trophy size={16} className={styles.sectionIconTrophy} />
                  <span>高パフォーマンスなヒットテーマ</span>
                </h4>
                <div className={styles.themesGrid}>
                  {analysis.top_performing_themes.map((theme, idx) => (
                    <div key={idx} className={styles.themeCard}>
                      <div className={styles.themeBadge}>Theme {idx + 1}</div>
                      <h5>{theme.theme_name}</h5>
                      <p>{theme.reason_for_popularity}</p>
                      <div className={styles.exampleVideo}>
                        <span>代表動画:</span> {theme.example_video_title}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 差別化アドバイス */}
              <div className={`${styles.card} ${styles.cardAdvice}`}>
                <h4>
                  <ArrowRight size={16} className={styles.cardIconAdvice} />
                  <span>自チャンネルの差別化・ポジショニング戦略アドバイス</span>
                </h4>
                <ul>
                  {analysis.positioning_advice.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              {/* レポート生成日時 */}
              <div className={styles.footer}>
                分析日時: {new Date(analysis.generated_at).toLocaleString('ja-JP')}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
