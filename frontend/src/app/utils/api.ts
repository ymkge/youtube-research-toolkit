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
    // 206 Partial Content (動画同期のみ失敗) などの可能性もあるため、エラーハンドリングを丁寧に行う
    const errorData = await res.json().catch(() => ({}));
    const message = errorData.detail || 'チャンネルの登録に失敗しました。';
    throw new Error(message);
  }

  return res.json();
}
