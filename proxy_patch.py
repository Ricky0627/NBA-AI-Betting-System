# 檔名: proxy_patch.py
import requests
import os
from urllib.parse import urlencode

# 1. 備份原本的 requests.get 功能，以免等等找不到
_original_get = requests.get

def _patched_get(url, params=None, **kwargs):
    """
    這是我們偽造的 get 函式，它會自動把請求轉發給 ScraperAPI
    """
    # 從環境變數讀取金鑰 (GitHub Actions 會自動注入)
    api_key = os.environ.get('SCRAPER_API_KEY')
    
    # 如果沒有金鑰 (例如在本機測試沒設變數)，就用原本的普通連線
    if not api_key:
        print(f"⚠️ [原廠模式] 無 API Key，直接連線: {url}")
        return _original_get(url, params=params, **kwargs)

    # 檢查網址是否已經是 ScraperAPI (避免無窮迴圈)
    if 'api.scraperapi.com' in url:
        return _original_get(url, params=params, **kwargs)

    # --- 偷天換日開始 ---
    
    # 如果原本的請求有帶參數 (params)，我們要先把它拼回 url 裡
    # 因為我們要把它整個當作一個字串傳給 ScraperAPI
    if params:
        if '?' in url:
            url += '&' + urlencode(params)
        else:
            url += '?' + urlencode(params)
    
    # 建構 ScraperAPI 的參數
    new_params = {
        'api_key': api_key,
        'url': url,
        'keep_headers': 'true',  # 盡量保留你原本程式碼設定的 User-Agent 等
        # 'render': 'true'      # 如果是被 Cloudflare 擋得很兇，可以取消這行註解
    }

    print(f"🕵️‍♂️ [自動代理] 攔截請求 -> 轉發 ScraperAPI: {url}")
    
    # 使用備份的原始連線功能，發送給代理伺服器
    # 注意：這裡我們移除了 params，因為已經拼進 url 了，把 new_params 給代理
    return _original_get('http://api.scraperapi.com', params=new_params, **kwargs)

# 2. 覆寫 requests.get
# 從這一刻起，你的所有程式碼只要呼叫 requests.get，實際上都是呼叫 _patched_get
requests.get = _patched_get

print("✅ [系統] 自動代理掛載成功！所有 requests.get 都將通過 ScraperAPI。")