import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.ai_analysis import AIAnalysisResponse, FeaturedVideoInfo
from app.core.config import settings

# モック用のダミーAIレスポンス
MOCK_AI_RESPONSE = {
    "channel_summary": "テスト用の要約文です。150文字以内の制約があります。",
    "recent_growth_analysis": None,
    "growth_factor_detail": {
        "thumbnail_title_factors": "明るい黄色の背景と太字フォントが視認性を高めています。",
        "posting_frequency_impact": "週2回の定期投稿がアルゴリズム露出を維持しています。",
        "conversion_rate_evaluation": "高い登録率を示しておりファン化に成功しています。"
    },
    "own_channel_prescription": None,
    "featured_videos": [],
    "strengths": ["強み1です", "強み2です"],
    "weaknesses": ["弱み1です", "弱み2です"],
    "top_performing_themes": [
        {
            "theme_name": "テーマ名",
            "reason_for_popularity": "人気理由",
            "example_video_title": "動画タイトル"
        }
    ],
    "positioning_advice": ["アドバイス1", "アドバイス2"]
}

def test_analyze_channel_no_videos(client, db):
    """
    動画が1件もない場合に、分析要求が 400 Bad Request になるかを検証。
    """
    c = Channel(youtube_channel_id="UC_NO_V", title="No Videos Channel", sort_order=0)
    db.add(c)
    db.commit()

    response = client.post(f"/api/channels/{c.id}/analyze")
    assert response.status_code == 400
    assert "分析に必要な動画データがありません" in response.json()["detail"]

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_no_api_key(mock_ai, client, db):
    """
    GEMINI_API_KEY が未設定の場合に 400 Bad Request になるかを検証。
    """
    # チャンネルと動画を登録
    c = Channel(youtube_channel_id="UC_NO_KEY", title="No Key Channel", sort_order=0)
    db.add(c)
    db.flush()
    v = Video(channel_id=c.id, youtube_video_id="video_id", title="Video Title", published_at=datetime.utcnow())
    db.add(v)
    db.commit()

    # API キーを未設定にする
    mock_ai.is_configured.return_value = False

    response = client.post(f"/api/channels/{c.id}/analyze")
    assert response.status_code == 400
    assert "APIキーが設定されていません" in response.json()["detail"]

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_success_and_cache(mock_ai, client, db):
    """
    正常系：初回は AI サービスを呼び出し、2回目はキャッシュから値を取得すること（モックが呼ばれないこと）を検証。
    """
    c = Channel(youtube_channel_id="UC_CACHE_TEST", title="Cache Channel", sort_order=0)
    db.add(c)
    db.flush()
    v = Video(channel_id=c.id, youtube_video_id="v_id", title="Video Title", published_at=datetime.utcnow() - timedelta(hours=1))
    db.add(v)
    db.commit()

    # AIサービスのモック設定
    mock_ai.is_configured.return_value = True
    
    # 戻り値を AIAnalysisResponse の型で作成
    mock_response = AIAnalysisResponse(
        **MOCK_AI_RESPONSE,
        generated_at=datetime.utcnow()
    )
    mock_ai.analyze_channel_positioning.return_value = mock_response

    # 1. 初回リクエスト（API実行）
    response1 = client.post(f"/api/channels/{c.id}/analyze")
    assert response1.status_code == 200
    assert response1.json()["channel_summary"] == MOCK_AI_RESPONSE["channel_summary"]
    assert mock_ai.analyze_channel_positioning.call_count == 1

    # 2. 2回目リクエスト（キャッシュから返るため、分析メソッドの呼び出し回数は 1回 のままであるべき）
    response2 = client.post(f"/api/channels/{c.id}/analyze")
    assert response2.status_code == 200
    assert response2.json()["channel_summary"] == MOCK_AI_RESPONSE["channel_summary"]
    # 呼び出し回数が 1回 から増えていない（キャッシュが使われた）ことを検証
    assert mock_ai.analyze_channel_positioning.call_count == 1

    # 3. キャッシュ期限パージ検証: 動画データが同期され、updated_at が更新された場合
    # 最終更新（同期）時刻を「分析生成日時よりも未来」に書き換える
    db.refresh(c)
    c.updated_at = datetime.utcnow() + timedelta(minutes=5)
    db.commit()

    # 3回目リクエスト（動画同期が入ったためキャッシュが無効化され、再び API コールが走る）
    response3 = client.post(f"/api/channels/{c.id}/analyze")
    assert response3.status_code == 200
    # 呼び出し回数が 2回 に増えたことを検証
    assert mock_ai.analyze_channel_positioning.call_count == 2

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_with_none_values(mock_ai, client, db):
    """
    登録者数や再生数、動画の高評価・コメント数が None の状態でリクエストを送った際、
    エラー（TypeError）にならず正常に 0 として処理されて AI サービスが呼ばれることを検証。
    """
    c = Channel(
        youtube_channel_id="UC_NONE_VALUES",
        title="None Values Channel",
        subscriber_count=None,
        view_count=None,
        description=None,
        sort_order=0
    )
    db.add(c)
    db.flush()
    v = Video(
        channel_id=c.id,
        youtube_video_id="v_none_id",
        title="Video Title",
        view_count=None,
        like_count=None,
        comment_count=None,
        published_at=datetime.utcnow()
    )
    db.add(v)
    db.commit()

    # AIサービスのモック設定
    mock_ai.is_configured.return_value = True
    
    mock_response = AIAnalysisResponse(
        **MOCK_AI_RESPONSE,
        generated_at=datetime.utcnow()
    )
    mock_ai.analyze_channel_positioning.return_value = mock_response

    # API呼び出し
    response = client.post(f"/api/channels/{c.id}/analyze")
    assert response.status_code == 200
    assert response.json()["channel_summary"] == MOCK_AI_RESPONSE["channel_summary"]
    assert mock_ai.analyze_channel_positioning.call_count == 1
    
    # 呼び出された時の引数 (channel_dict) を確認し、値のフォールバック状態を検証
    called_channel_data = mock_ai.analyze_channel_positioning.call_args[0][0]
    assert called_channel_data["subscriber_count"] == 0  # DB default=0
    assert called_channel_data["view_count"] == 0        # DB default=0
    assert called_channel_data["description"] is None

    # 呼び出された時の引数 (videos_list) を確認し、値のフォールバック状態を検証
    called_video_data = mock_ai.analyze_channel_positioning.call_args[0][1][0]
    assert called_video_data["view_count"] == 0          # Video view_count default=0
    assert called_video_data["like_count"] is None
    assert called_video_data["comment_count"] is None

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_is_featured(mock_ai, client, db):
    """
    注目フラグ (is_pinned=True) のあるチャンネルの分析時、is_featured=True で
    AIService.analyze_channel_positioning が呼び出されることを検証。
    """
    c = Channel(
        youtube_channel_id="UC_FEATURED_PIN",
        title="Pinned Featured Channel",
        is_pinned=True,
        sort_order=0
    )
    db.add(c)
    db.flush()
    v = Video(
        channel_id=c.id,
        youtube_video_id="v_feat_id",
        title="Featured Video Title",
        view_count=5000,
        published_at=datetime.utcnow()
    )
    db.add(v)
    db.commit()

    mock_ai.is_configured.return_value = True
    featured_mock_resp = AIAnalysisResponse(
        **{**MOCK_AI_RESPONSE, "recent_growth_analysis": "直近でポモドーロ動画が急上昇し、サムネイルの大文字が寄与。"},
        generated_at=datetime.utcnow()
    )
    mock_ai.analyze_channel_positioning.return_value = featured_mock_resp

    response = client.post(f"/api/channels/{c.id}/analyze?force=true")
    assert response.status_code == 200
    assert response.json()["recent_growth_analysis"] is not None
    assert "直近でポモドーロ動画が急上昇" in response.json()["recent_growth_analysis"]
    
    # 呼び出し時の第3引数 (is_featured) が True であることを検証
    call_kwargs = mock_ai.analyze_channel_positioning.call_args
    assert call_kwargs[1].get("is_featured") is True

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_is_featured_with_video_links(mock_ai, client, db):
    """
    注目フラグチャンネルの分析時、最注目動画のURLおよびIDが
    正確にレスポンスへ自動付与されているかを検証。
    """
    c = Channel(
        youtube_channel_id="UC_FEATURED_URL_TEST",
        title="Featured URL Channel",
        is_pinned=True,
        sort_order=0
    )
    db.add(c)
    db.flush()
    
    v1 = Video(
        channel_id=c.id,
        youtube_video_id="spike_vid_01",
        title="1.5倍バズ動画",
        view_count=15000,
        published_at=datetime.utcnow() - timedelta(days=5)
    )
    db.add(v1)
    db.commit()

    mock_ai.is_configured.return_value = True
    
    featured_mock_resp = AIAnalysisResponse(
        **{**MOCK_AI_RESPONSE, "recent_growth_analysis": "直近で急成長しています。"},
        generated_at=datetime.utcnow()
    )
    featured_mock_resp.featured_videos = [
        FeaturedVideoInfo(
            youtube_video_id="spike_vid_01",
            title="1.5倍バズ動画",
            url="https://www.youtube.com/watch?v=spike_vid_01",
            view_count=15000,
            spike_ratio=1.5,
            thumbnail_url=None
        )
    ]
    mock_ai.analyze_channel_positioning.return_value = featured_mock_resp

    response = client.post(f"/api/channels/{c.id}/analyze?force=true")
    assert response.status_code == 200
    res_data = response.json()
    
    assert "featured_videos" in res_data
    assert len(res_data["featured_videos"]) == 1
    assert res_data["featured_videos"][0]["youtube_video_id"] == "spike_vid_01"
    assert res_data["featured_videos"][0]["url"] == "https://www.youtube.com/watch?v=spike_vid_01"

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_24h_cache_expiration(mock_ai, client, db):
    """
    24時間スマートキャッシュの検証:
    - 23時間前のキャッシュ -> 有効 (API未呼び出し)
    - 25時間前のキャッシュ -> 期限切れ (API再呼び出し)
    - force=True リクエスト -> 強制更新 (API再呼び出し)
    """
    c = Channel(youtube_channel_id="UC_24H_TEST", title="24h Test Channel", sort_order=0)
    db.add(c)
    db.flush()
    v = Video(channel_id=c.id, youtube_video_id="v_24h", title="Video Title", published_at=datetime.utcnow())
    db.add(v)
    db.commit()

    mock_ai.is_configured.return_value = True
    mock_response = AIAnalysisResponse(**MOCK_AI_RESPONSE, generated_at=datetime.utcnow())
    mock_ai.analyze_channel_positioning.return_value = mock_response

    # 1. 初回生成
    client.post(f"/api/channels/{c.id}/analyze")
    assert mock_ai.analyze_channel_positioning.call_count == 1

    # 2. 23時間前に生成されたことに時刻を偽装 -> キャッシュ有効
    db.refresh(c)
    c.ai_analysis_generated_at = datetime.utcnow() - timedelta(hours=23)
    c.updated_at = c.ai_analysis_generated_at
    db.commit()

    res2 = client.post(f"/api/channels/{c.id}/analyze")
    assert res2.status_code == 200
    assert mock_ai.analyze_channel_positioning.call_count == 1  # 増えない

    # 3. 25時間前に偽装 -> キャッシュ切れで再呼び出し
    c.ai_analysis_generated_at = datetime.utcnow() - timedelta(hours=25)
    c.updated_at = c.ai_analysis_generated_at
    db.commit()

    res3 = client.post(f"/api/channels/{c.id}/analyze")
    assert res3.status_code == 200
    assert mock_ai.analyze_channel_positioning.call_count == 2  # 増える

    # 4. 24時間以内だが force=true でリクエスト -> 強制更新
    c.ai_analysis_generated_at = datetime.utcnow() - timedelta(hours=1)
    c.updated_at = c.ai_analysis_generated_at
    db.commit()

    res4 = client.post(f"/api/channels/{c.id}/analyze?force=true")
    assert res4.status_code == 200
    assert mock_ai.analyze_channel_positioning.call_count == 3  # 増える

@patch("app.api.endpoints.channels.ai_service")
def test_analyze_channel_corrupted_cache_fallback(mock_ai, client, db):
    """
    破損キャッシュ/旧スキーマデータのフォールバック検証:
    JSONデコードエラーやPydanticパースエラーが発生した場合、
    エラーで落ちずに破損キャッシュをクリアし、API再呼び出しを行って正常レスポンスを返すこと。
    """
    c = Channel(
        youtube_channel_id="UC_CORRUPTED",
        title="Corrupted Cache Channel",
        ai_analysis="{ invalid json content }",
        ai_analysis_generated_at=datetime.utcnow(),
        sort_order=0
    )
    db.add(c)
    db.flush()
    v = Video(channel_id=c.id, youtube_video_id="v_corr", title="Video", published_at=datetime.utcnow())
    db.add(v)
    db.commit()

    mock_ai.is_configured.return_value = True
    mock_response = AIAnalysisResponse(**MOCK_AI_RESPONSE, generated_at=datetime.utcnow())
    mock_ai.analyze_channel_positioning.return_value = mock_response

    res = client.post(f"/api/channels/{c.id}/analyze")
    assert res.status_code == 200
    assert mock_ai.analyze_channel_positioning.call_count == 1

    # DB上の破損キャッシュがクリアされた後、新生成されたキャッシュが入っていることを確認
    db.refresh(c)
    assert c.ai_analysis is not None
