import ccxt
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import requests
import time
from datetime import datetime

# ==========================================
# 設定エリア（直接ここに書き込んでください）
# ==========================================
GEMINI_API_KEY = "あなたのGemini_APIキー"
DISCORD_WEBHOOK_URL = "あなたのDiscord_Webhook_URL"

SYMBOL = 'ETH/USDT'
TIMEFRAME = '15m'
LIMIT = 50
# ==========================================

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def get_market_data():
    """Bybitからデータを取得"""
    bybit = ccxt.bybit()
    # 日本からのアクセスならこれで通ります
    ohlcv = bybit.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=9) # 日本時間

    # テクニカル指標
    df['RSI'] = ta.rsi(df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df['EMA_25'] = ta.ema(df['close'], length=25)
    df['EMA_75'] = ta.ema(df['close'], length=75)
    df['EMA_200'] = ta.ema(df['close'], length=200)
    return df

def ask_gemini(df):
    """Geminiに分析させる"""
    latest = df.iloc[-1]
    prompt = f"""
    あなたはプロトレーダー「ししゃもん」です。ユーザーはリハビリ中。
    【データ: {SYMBOL} ({TIMEFRAME})】
    Price: {latest['close']}
    RSI: {latest['RSI']:.2f}
    BB: Upper{latest['BBU_20_2.0']:.2f}/Mid{latest['BBM_20_2.0']:.2f}/Lower{latest['BBL_20_2.0']:.2f}
    EMA: 25({latest['EMA_25']:.2f})/75({latest['EMA_75']:.2f})/200({latest['EMA_200']:.2f})
    
    【直近値動き】
    {df.tail(5)[['timestamp', 'close']].to_string(index=False)}
    
    【指示】
    スマホ通知用。短文で。
    1.【判断】Wait/Long/Short
    2.【理由】一言
    3.【戦略】価格と損切り
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"

def send_discord(message):
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Discord Error: {e}")

# ==========================================
# 実行ループ（Mac用）
# ==========================================
if __name__ == "__main__":
    print(f"✅ {SYMBOL} の監視を開始します（Ctrl+Cで停止）")
    send_discord("🚀 Mac Studioで監視ボットを起動しました！")

    while True:
        try:
            # 現在の「分」を取得
            now = datetime.now()
            current_minute = now.minute

            # 15分足の確定タイミング（00, 15, 30, 45分）の直後に実行
            # ※1分〜2分の遅れを持たせてデータ確定を待つ
            if current_minute in [1, 16, 31, 46]:
                print(f"\n[{now.strftime('%H:%M:%S')}] 分析中...")
                
                df = get_market_data()
                analysis = ask_gemini(df)
                
                print(f"価格: {df.iloc[-1]['close']}")
                print(analysis)
                send_discord(analysis)
                
                # 連投防止のため65秒待つ
                time.sleep(65)
            else:
                # タイミングが来るまで30秒待機
                time.sleep(30)

        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(60)
