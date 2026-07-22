const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  updated_at: string;
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
 * 新しいチャンネルを登録します。
 */
export async function registerChannel(identifier: string, importLimit: number = 50): Promise<Channel> {
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

  return res.json();
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
