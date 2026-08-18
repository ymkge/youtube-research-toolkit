import React, { useEffect, useState } from 'react';
import { AIAnalysisResponse } from '../utils/api';
import styles from './AIAnalysisModal.module.css';
import { Sparkles, Brain, AlertCircle, CheckCircle2, Trophy, ArrowRight, X, RefreshCw, FileText, Image, Info, Flame, ExternalLink, Play, Home, Target, Zap, CheckSquare } from 'lucide-react';

interface AIAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  isLoading: boolean;
  error: string | null;
  analysis: AIAnalysisResponse | null;
  channelTitle: string;
  onReanalyze?: () => void;
}

export default function AIAnalysisModal({
  isOpen,
  onClose,
  isLoading,
  error,
  analysis,
  channelTitle,
  onReanalyze,
}: AIAnalysisModalProps) {
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'report' | 'prescription'>('report');

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

  // テキスト内に改行や「・」が含まれる場合、リストとしてフォーマット表記する関数
  const renderFormattedText = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
    if (lines.length <= 1 && !text.includes('・')) {
      return <p>{text}</p>;
    }
    return (
      <div className={styles.formattedTextList}>
        {lines.map((line, idx) => {
          const isBullet = line.startsWith('・') || line.startsWith('-');
          const cleanLine = isBullet ? line.substring(1).trim() : line;
          return (
            <div key={idx} className={isBullet ? styles.formattedBulletItem : styles.formattedLineItem}>
              {isBullet && <span className={styles.bulletDot}>•</span>}
              <span>{cleanLine}</span>
            </div>
          );
        })}
      </div>
    );
  };

  // レポートコンテンツを高解像度 Canvas 化する共通処理
  const captureReportCanvas = async () => {
    const reportElement = document.getElementById('ai-report-export-area');
    if (!reportElement) return null;

    const html2canvas = (await import('html2canvas')).default;
    return await html2canvas(reportElement, {
      scale: 2, // 2倍高解像度キャプチャ
      useCORS: true,
      backgroundColor: '#141414',
      logging: false,
    });
  };

  // PDF 出力処理
  const handleExportPDF = async () => {
    if (isExporting || !analysis) return;
    setIsExporting(true);
    try {
      const canvas = await captureReportCanvas();
      if (!canvas) return;

      const { jsPDF } = await import('jspdf');
      const imgData = canvas.toDataURL('image/png');

      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height],
      });

      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);

      const dateStr = new Date().toISOString().split('T')[0].replace(/-/g, '');
      const sanitizedTitle = channelTitle.replace(/[\\/:*?"<>|]/g, '_');
      pdf.save(`AIポジショニング分析_${sanitizedTitle}_${dateStr}.pdf`);
    } catch (err) {
      console.error('PDF出力エラー:', err);
      alert('PDFの出力に失敗しました。');
    } finally {
      setIsExporting(false);
    }
  };

  // PNG/SVG 画像出力処理
  const handleExportImage = async () => {
    if (isExporting || !analysis) return;
    setIsExporting(true);
    try {
      const canvas = await captureReportCanvas();
      if (!canvas) return;

      const imgData = canvas.toDataURL('image/png');
      const dateStr = new Date().toISOString().split('T')[0].replace(/-/g, '');
      const sanitizedTitle = channelTitle.replace(/[\\/:*?"<>|]/g, '_');

      const link = document.createElement('a');
      link.href = imgData;
      link.download = `AIポジショニング分析_${sanitizedTitle}_${dateStr}.png`;
      link.click();
    } catch (err) {
      console.error('画像出力エラー:', err);
      alert('画像の出力に失敗しました。');
    } finally {
      setIsExporting(false);
    }
  };

  const hasGrowthFactors = Boolean(
    analysis?.recent_growth_analysis ||
    analysis?.growth_factor_detail?.thumbnail_title_factors ||
    analysis?.growth_factor_detail?.posting_frequency_impact ||
    analysis?.growth_factor_detail?.conversion_rate_evaluation
  );

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* ヘッダーエリア */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <Brain className={styles.headerIcon} />
            <div>
              <h3>AIポジショニング分析レポート</h3>
              <p className={styles.subTitle}>対象チャンネル: <span>{channelTitle}</span></p>
            </div>
          </div>

          <div className={styles.headerActions}>
            {/* エクスポートボタン群 (ヘッダー側) */}
            {analysis && (
              <div className={styles.exportGroup}>
                <button
                  onClick={handleExportPDF}
                  className={styles.exportBtn}
                  title="レポートを PDF としてダウンロード"
                  disabled={isExporting}
                >
                  <FileText size={14} />
                  <span>PDF保存</span>
                </button>
                <button
                  onClick={handleExportImage}
                  className={styles.exportBtn}
                  title="レポートを画像 (PNG/SVG) としてダウンロード"
                  disabled={isExporting}
                >
                  <Image size={14} />
                  <span>画像保存</span>
                </button>
              </div>
            )}

            <button onClick={onClose} className={styles.closeButton}>
              <X size={20} />
            </button>
          </div>
        </div>

        {/* コンテンツエリア */}
        <div className={styles.content}>
          {isLoading && (
            <div className={styles.loadingContainer}>
              <div className={styles.spinner}></div>
              <p>Gemini AI がチャンネル・動画パフォーマンスを多角的に分析中...</p>
              <span className={styles.loadingSubText}>直近100件の動画動向、投稿ペース、RAGドメイン知識を元にポジショニングを生成しています</span>
            </div>
          )}

          {error && (
            <div className={styles.errorContainer}>
              <AlertCircle size={24} className={styles.errorIcon} />
              <div>
                <h4>AI分析の生成に失敗しました</h4>
                <p>{error}</p>
              </div>
            </div>
          )}

          {analysis && !isLoading && (
            <div className={styles.reportArea} id="ai-report-export-area">
              {/* ガイダンス注記 */}
              <div className={styles.guideBox}>
                <Info size={16} className={styles.guideIcon} />
                <span>
                  本レポートは、チャンネルの統計・直近100件の動画・ドメインナレッジ(RAG)を元に、Gemini AIが競合の強み・弱み・ヒットテーマ・差別化戦略を自動分析して生成しています。
                </span>
              </div>

              {/* ナビゲーションタブバー (キャプチャ時は非表示) */}
              {!isExporting && (
                <div className={styles.tabBar}>
                  <button
                    className={`${styles.tabBtn} ${activeTab === 'report' ? styles.activeTabBtn : ''}`}
                    onClick={() => setActiveTab('report')}
                  >
                    <Sparkles size={14} />
                    <span>AIポジショニング分析レポート</span>
                  </button>
                  <button
                    className={`${styles.tabBtn} ${activeTab === 'prescription' ? styles.activeTabBtn : ''}`}
                    onClick={() => setActiveTab('prescription')}
                  >
                    <Home size={14} />
                    <span>自チャンネル改善処方箋</span>
                  </button>
                </div>
              )}

              {/* === タブ1: 📊 AIポジショニング分析レポート (統合メイン) === */}
              {(activeTab === 'report' || isExporting) && (
                <div className={styles.tabContentSection}>
                  {/* 概要・サマリー */}
                  <div className={styles.summarySection}>
                    <p className={styles.summaryText}>{analysis.channel_summary}</p>
                  </div>

                  {/* 🔥 急成長要因詳細セクション (注目・急成長チャンネル時のみ動的挿入) */}
                  {hasGrowthFactors && (
                    <div className={styles.recentGrowthCard}>
                      <h4>
                        <Flame size={16} className={styles.recentGrowthIcon} />
                        <span>🔥 注目・急成長要因深掘り分析</span>
                      </h4>

                      {analysis.recent_growth_analysis && (
                        <div className={styles.growthSubBlock}>
                          <h5 className={styles.growthSubTitle}>🚀 直近再生数急増 ＆ サムネイル視覚勝因</h5>
                          {renderFormattedText(analysis.recent_growth_analysis)}
                        </div>
                      )}

                      {/* 🎥 最注目・スパイク動画のダイレクトURLリンク群 */}
                      {analysis.featured_videos && analysis.featured_videos.length > 0 && (
                        <div className={styles.featuredVideosSection}>
                          <div className={styles.featuredVideosHeader}>
                            <Play size={13} className={styles.playIcon} />
                            <span>分析の根拠となった直近の最注目動画</span>
                          </div>
                          <div className={styles.featuredVideosList}>
                            {analysis.featured_videos.map((video, idx) => (
                              <a
                                key={video.youtube_video_id || idx}
                                href={video.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`${styles.featuredVideoCard} ${idx === 0 ? styles.primaryFeaturedCard : ''}`}
                                title={`YouTubeで「${video.title}」を開く`}
                              >
                                <span className={styles.featuredTag}>
                                  {idx === 0 ? '🔥 No.1 最注目' : `注目 #${idx + 1}`}
                                </span>
                                <div className={styles.featuredContent}>
                                  <span className={styles.featuredTitle}>{video.title}</span>
                                  <span className={styles.featuredMeta}>
                                    再生数: {video.view_count.toLocaleString()}回 (平均の{video.spike_ratio}倍)
                                  </span>
                                </div>
                                <div className={styles.featuredLinkBtn}>
                                  <span>動画を視聴</span>
                                  <ExternalLink size={13} />
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* 共通勝因カード3連 */}
                      {analysis.growth_factor_detail && (
                        <div className={styles.factorDetailContainer}>
                          {analysis.growth_factor_detail.thumbnail_title_factors && (
                            <div className={styles.factorCard}>
                              <h5>🖼️ サムネイル ＆ タイトルの共通勝因</h5>
                              {renderFormattedText(analysis.growth_factor_detail.thumbnail_title_factors)}
                            </div>
                          )}
                          {analysis.growth_factor_detail.posting_frequency_impact && (
                            <div className={styles.factorCard}>
                              <h5>📈 投稿頻度 ＆ 更新ペースの影響</h5>
                              {renderFormattedText(analysis.growth_factor_detail.posting_frequency_impact)}
                            </div>
                          )}
                          {analysis.growth_factor_detail.conversion_rate_evaluation && (
                            <div className={styles.factorCard}>
                              <h5>🎯 チャンネル登録率 (最重要KPI) ＆ ファン化構造</h5>
                              {renderFormattedText(analysis.growth_factor_detail.conversion_rate_evaluation)}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 強み・弱み (2カラム) */}
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
                </div>
              )}

              {/* === タブ2: 💊 自チャンネル改善処方箋 === */}
              {(activeTab === 'prescription' || isExporting) && (
                <div className={styles.tabContentSection}>
                  {isExporting && (
                    <div className={styles.exportSectionDivider}>
                      <h3>💊 自チャンネル改善処方箋</h3>
                    </div>
                  )}

                  {analysis.own_channel_prescription ? (
                    <div className={styles.prescriptionContainer}>
                      {/* ギャップ分析 */}
                      <div className={styles.prescriptionCard}>
                        <h4>
                          <Target size={16} className={styles.prescriptionIcon} />
                          <span>競合と自チャンネルの決定的な差 (ギャップ分析)</span>
                        </h4>
                        {renderFormattedText(analysis.own_channel_prescription.gap_analysis)}
                      </div>

                      {/* 具現的A/Bテスト改善アクション */}
                      <div className={styles.prescriptionCard}>
                        <h4>
                          <CheckSquare size={16} className={styles.prescriptionIcon} />
                          <span>チャンネル登録率を最大化する具体 A/B テスト改善案</span>
                        </h4>
                        <ul>
                          {analysis.own_channel_prescription.actionable_steps.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ul>
                      </div>

                      {/* 最優先改善ポイント */}
                      <div className={`${styles.prescriptionCard} ${styles.priorityCard}`}>
                        <h4>
                          <Trophy size={16} className={styles.priorityIcon} />
                          <span>最優先で着手すべき改善ポイント</span>
                        </h4>
                        <p>{analysis.own_channel_prescription.priority_improvement}</p>
                      </div>
                    </div>
                  ) : (
                    <div className={styles.ownChannelGuidance}>
                      <Home size={28} className={styles.guidanceIcon} />
                      <h4>自チャンネルを登録すると「改善処方箋」が生成されます</h4>
                      <p>チャンネル一覧で自チャンネルのカードにある <strong>「🏠 自チャンネルに設定」</strong> ボタンを押してから AI 分析（または新規ノウハウで再分析）を実行すると、自チャンネルと直感比較した改善処方箋が表示されます。</p>
                    </div>
                  )}
                </div>
              )}

              {/* レポート生成日時 & コントロール */}
              <div className={styles.footer}>
                <span className={styles.generatedAt}>
                  分析日時: {new Date(analysis.generated_at).toLocaleString('ja-JP')}
                </span>

                <div className={styles.footerControls}>
                  {/* エクスポートボタン群 (フッター側) */}
                  <div className={styles.exportGroupFooter}>
                    <button
                      onClick={handleExportPDF}
                      className={styles.exportBtnFooter}
                      title="レポートを PDF としてダウンロード"
                      disabled={isExporting}
                    >
                      <FileText size={13} />
                      <span>📄 PDF保存</span>
                    </button>
                    <button
                      onClick={handleExportImage}
                      className={styles.exportBtnFooter}
                      title="レポートを画像 (PNG/SVG) としてダウンロード"
                      disabled={isExporting}
                    >
                      <Image size={13} />
                      <span>🖼️ 画像保存</span>
                    </button>
                  </div>

                  {onReanalyze && (
                    <button
                      onClick={onReanalyze}
                      className={styles.reanalyzeBtn}
                      title="最新のドメインナレッジ (domain_knowledge.txt) を読み込み強制再分析します"
                      disabled={isLoading || isExporting}
                    >
                      <RefreshCw size={13} className={isLoading ? styles.spinning : ''} />
                      <span>最新ノウハウで再分析</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
