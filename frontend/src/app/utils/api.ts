const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface Channel {
  id: number;
  youtube_channel_id: string;
  title: string;
  description: string | null;
  custom_url: string | null;
  published_at: string | null;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  thumbnail_url: string | null;
  average_video_duration: number | null; // 平均動画時間 (秒)
  average_views_per_video: number | null; // 1動画あたりの平均再生数
  average_upload_frequency: number | null; // 平均動画投稿頻度 (週単位)
  country: string | null; // 国名コード (JP, US など)
  sort_order: number; // 表示順
  is_pinned: boolean; // ピン留め状態
  latest_video_published_at: string | null; // 最新動画アップロード日時
  daily_sub_growth?: number; // 前日比登録者増加数
  updated_at: string;
}

export interface RegisterResponse {
  channel: Channel;
  isNew: boolean;
}

export interface ChannelStatsHistory {
  id: number;
  channel_id: number;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  recorded_at: string; // YYYY-MM-DD
}

export interface AIAnalysisTheme {
  theme_name: string;
  reason_for_popularity: string;
  example_video_title: string;
}

export interface AIAnalysisResponse {
  channel_summary: string;
  strengths: string[];
  weaknesses: string[];
  top_performing_themes: AIAnalysisTheme[];
  positioning_advice: string[];
  generated_at: string;
}

/**
 * 登録済みチャンネル一覧を取得します。
 */
export async function fetchChannels(): Promise<Channel[]> {
  const res = await fetch(`${API_BASE_URL}/api/channels/`);
  if (!res.ok) {
    throw new Error('チャンネル一覧の取得に失敗しました。');
  }
  return res.json();
}

/**
 * 新しいチャンネルを登録します（重複時は更新）。
 */
export async function registerChannel(identifier: string, importLimit: number = 100): Promise<RegisterResponse> {
  const res = await fetch(`${API_BASE_URL}/api/channels/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ identifier, import_limit: importLimit }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || 'チャンネルの登録に失敗しました。';
    throw new Error(message);
  }

  const isNew = res.status === 201;
  const channel = await res.json();
  return { channel, isNew };
}

/**
 * チャンネルを削除します（カスケード削除）。
 */
export async function deleteChannel(channelId: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/channels/${channelId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || 'チャンネルの削除に失敗しました。';
    throw new Error(message);
  }
}

/**
 * チャンネルのピン留め（最上部固定）状態を更新します。
 */
export async function updateChannelPin(channelId: number, isPinned: boolean): Promise<Channel> {
  const res = await fetch(`${API_BASE_URL}/api/channels/${channelId}/pin?is_pinned=${isPinned}`, {
    method: 'PATCH',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || 'ピン留めの更新に失敗しました。';
    throw new Error(message);
  }

  return res.json();
}

/**
 * ドラッグ＆ドロップ後の表示順を一括保存します。
 */
export async function updateChannelsSort(ids: number[]): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/channels/sort`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ids }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || '表示順の更新に失敗しました。';
    throw new Error(message);
  }
}

/**
 * チャンネルの時系列統計データを取得します。
 */
export async function fetchChannelHistory(channelId: number): Promise<ChannelStatsHistory[]> {
  const res = await fetch(`${API_BASE_URL}/api/channels/${channelId}/history`);
  if (!res.ok) {
    throw new Error('統計履歴の取得に失敗しました。');
  }
  return res.json();
}

/**
 * チャンネルのAIポジショニング分析レポートを取得（生成）します。
 * forceReanalyze が true の場合はキャッシュを無視して最新のドメインナレッジで強制再分析を行います。
 */
export async function fetchChannelAIAnalysis(
  channelId: number,
  forceReanalyze: boolean = false
): Promise<AIAnalysisResponse> {
  const url = `${API_BASE_URL}/api/channels/${channelId}/analyze${
    forceReanalyze ? '?force=true' : ''
  }`;
  const res = await fetch(url, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || 'AI分析の生成に失敗しました。';
    throw new Error(message);
  }

  return res.json();
}

/**
 * 競合比較用インターフェース
 */
export interface ComparisonChannelItem {
  id: number;
  title: string;
  youtube_channel_id: string;
  custom_url?: string | null;
  thumbnail_url: string | null;
  color: string;
  dash_pattern: string;
  has_history: boolean;
  history_count: number;
  subscriber_count?: number;
  is_pinned?: boolean;
}

export interface ComparisonTimelineEntry {
  date: string;
  [key: string]: any;
}

export interface ChannelsComparisonResponse {
  channels: ComparisonChannelItem[];
  timeline: ComparisonTimelineEntry[];
}

/**
 * 全チャンネルの成長率比較タイムラインデータを取得します。
 */
export async function fetchChannelsComparison(): Promise<ChannelsComparisonResponse> {
  const res = await fetch(`${API_BASE_URL}/api/channels/comparison`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || '成長率比較データの取得に失敗しました。');
  }
  return res.json();
}
