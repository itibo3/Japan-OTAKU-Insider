"""
外部サイトの HTML / RSS / 画像取得で共有する HTTP 設定。

Cloudflare 等のボット対策で 403 になりにくいよう、クローラー向け User-Agent を統一する。
X API・DeepL・Perplexity などの公式 API リクエストには使わない（別ヘッダー・認証のため）。

触っていい所: FETCH_USER_AGENT の変更、article_fetch_headers の追加キー。
危ない所: 上記 API クライアントへの流用。
"""

FETCH_USER_AGENT = (
    "Mozilla/5.0 (compatible; Twitterbot/1.0; +http://twitter.com/robots.txt)"
)


def article_fetch_headers() -> dict[str, str]:
    """記事ページ・RSS・画像URL取得用の最低限のヘッダー。"""
    return {"User-Agent": FETCH_USER_AGENT}
