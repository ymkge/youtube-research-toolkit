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
  const [activeTab, setActiveTab] = useState<'basic' | 'factors' | 'prescription'>('basic');

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

          <div className={styles.headerActions}>
            {/* エクスポートボタン群 (ヘッダー側) */}
            {analysis && !isLoading && (
              <div className={styles.exportGroupHeader}>
                <button
                  onClick={handleExportPDF}
                  className={styles.exportBtnHeader}
                  title="レポートを PDF としてダウンロード"
                  disabled={isExporting}
                >
                  <FileText size={13} />
                  <span>PDF</span>
                </button>
                <button
                  onClick={handleExportImage}
                  className={styles.exportBtnHeader}
                  title="レポートを画像 (PNG/SVG) としてダウンロード"
                  disabled={isExporting}
                >
                  <Image size={13} />
                  <span>画像</span>
                </button>
              </div>
            )}
            <button className={styles.closeButton} onClick={onClose} title="閉じる">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* ℹ️ AI分析の生成仕組み説明バナー (100文字以内 / 100件未満フォロー注記付き) */}
        <div className={styles.infoBanner}>
          <Info size={15} className={styles.infoBannerIcon} />
          <p className={styles.infoBannerText}>
            本レポートは、チャンネルの統計・直近100件の動画(100件未満は全動画)・ドメインナレッジ(RAG)を元に、Gemini AIが競合の強み・弱み・ヒットテーマ・差別化戦略を自動分析して生成しています。
          </p>
        </div>

        {/* モーダルコンテンツ */}
        <div className={styles.content}>
          {/* ローディングスケルトン */}
          {isLoading && (
            <div className={styles.skeletonContainer}>
              <div className={styles.skeletonTitle}>
                <Sparkles className={styles.skeletonIcon} size={16} />
                <span>AIが競合データを多角的にポジショニング分析中...</span>
              </div>
              <div className={styles.skeletonLine} style={{ width: '80%' }} />
              <div className={styles.skeletonLine} style={{ width: '60%' }} />
              <div className={styles.skeletonGrid}>
                <div className={styles.skeletonCard} />
                <div className={styles.skeletonCard} />
              </div>
            </div>
          )}

          {/* エラー表示 */}
          {error && (
            <div className={styles.errorContainer}>
              <AlertCircle className={styles.errorIcon} size={24} />
              <div className={styles.errorText}>
                <h4>AI分析の生成に失敗しました</h4>
                <p>{error}</p>
              </div>
            </div>
          )}

          {/* レポートコンテンツ (キャプチャ対象 ID: ai-report-export-area) */}
          {!isLoading && !error && analysis && (
            <div id="ai-report-export-area" className={styles.reportContent}>
              {/* レポートキャプチャ用ヘッダーブランディング */}
              <div className={styles.exportBranding}>
                <span className={styles.brandingTitle}>YouTube Research Toolkit - AI Positioning Analysis</span>
                <span className={styles.brandingChannel}>Target: {channelTitle}</span>
              </div>

              {/* タブナビゲーション */}
              <div className={styles.tabBar}>
                <button
                  className={`${styles.tabBtn} ${activeTab === 'basic' ? styles.activeTabBtn : ''}`}
                  onClick={() => setActiveTab('basic')}
                >
                  <Brain size={14} />
                  <span>基本ポジショニング</span>
                </button>
                <button
                  className={`${styles.tabBtn} ${activeTab === 'factors' ? styles.activeTabBtn : ''}`}
                  onClick={() => setActiveTab('factors')}
                >
                  <Flame size={14} />
                  <span>🔥 急成長要因詳細</span>
                </button>
                <button
                  className={`${styles.tabBtn} ${activeTab === 'prescription' ? styles.activeTabBtn : ''}`}
                  onClick={() => setActiveTab('prescription')}
                >
                  <Home size={14} />
                  <span>💊 自チャンネル改善処方箋</span>
                </button>
              </div>

              {/* === タブ1: 基本ポジショニング === */}
              {(activeTab === 'basic' || isExporting) && (
                <div className={styles.tabContentSection}>
                  {/* 概要・サマリー */}
                  <div className={styles.summarySection}>
                    <p className={styles.summaryText}>{analysis.channel_summary}</p>
                  </div>

                  {/* 🚀 注目チャンネル特記: 直近の再生数急拡大 ＆ サムネイルデザイン分析 */}
                  {analysis.recent_growth_analysis && (
                    <div className={styles.recentGrowthCard}>
                      <h4>
                        <Flame size={16} className={styles.recentGrowthIcon} />
                        <span>🚀 注目チャンネル特別分析: 直近の再生数急増 ＆ サムネイル勝因分析</span>
                      </h4>
                      <p>{analysis.recent_growth_analysis}</p>

                      {/* 🎥 最注目・スパイク動画のダイレクトURLリンク群 */}
                      {analysis.featured_videos && analysis.featured_videos.length > 0 && (
                        <div className={styles.featuredVideosSection}>
                          <div className={styles.featuredVideosHeader}>
                            <Play size={13} className={styles.playIcon} />
                            <span>分析の根拠となった直近の最注目動画 (クリックでYouTube再生)</span>
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
                    </div>
                  )}
                </div>
              )}

              {/* === タブ2: 急成長要因詳細 === */}
              {(activeTab === 'factors' || isExporting) && (
                <div className={styles.tabContentSection}>
                  <div className={styles.factorDetailContainer}>
                    <div className={styles.factorCard}>
                      <h4>
                        <Sparkles size={16} className={styles.factorIcon} />
                        <span>🖼️ サムネイル ＆ タイトルの具体勝因</span>
                      </h4>
                      <p>{analysis.growth_factor_detail?.thumbnail_title_factors || '最新のヒットデータからサムネイル・タイトルの惹きつけ勝因を抽出中...'}</p>
                    </div>

                    <div className={styles.factorCard}>
                      <h4>
                        <Zap size={16} className={styles.factorIcon} />
                        <span>📈 投稿頻度 ＆ 更新ペースの影響</span>
                      </h4>
                      <p>{analysis.growth_factor_detail?.posting_frequency_impact || '投稿間隔や更新ペースがアルゴリズム露出に及ぼした影響を分析中...'}</p>
                    </div>

                    <div className={styles.factorCard}>
                      <h4>
                        <Target size={16} className={styles.factorIcon} />
                        <span>🎯 チャンネル登録率 (最重要KPI) ＆ ファン化構造</span>
                      </h4>
                      <p>{analysis.growth_factor_detail?.conversion_rate_evaluation || '閲覧からチャンネル登録に至ったコンバージョン転換効率を評価中...'}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* === タブ3: 自チャンネル改善処方箋 === */}
              {(activeTab === 'prescription' || isExporting) && (
                <div className={styles.tabContentSection}>
                  {analysis.own_channel_prescription ? (
                    <div className={styles.prescriptionContainer}>
                      {/* ギャップ分析 */}
                      <div className={styles.prescriptionCard}>
                        <h4>
                          <Target size={16} className={styles.prescriptionIcon} />
                          <span>競合と自チャンネルの決定的な差 (ギャップ分析)</span>
                        </h4>
                        <p>{analysis.own_channel_prescription.gap_analysis}</p>
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
