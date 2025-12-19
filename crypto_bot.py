import ccxt
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import requests
import os  # 環境変数のために追加

# ==========================================
# 設定エリア（GitHub Secretsから読み込む設定）
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

SYMBOL = 'ETH/USDT'
TIMEFRAME = '15m'
LIMIT = 50

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def get_market_data():
    bybit = ccxt.bybit()
    ohlcv = bybit.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + pd.Timedelta(hours=9)

    df['RSI'] = ta.rsi(df['close'], length=14)
    bb = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bb], axis=1)
    df['EMA_25'] = ta.ema(df['close'], length=25)
    df['EMA_75'] = ta.ema(df['close'], length=75)
    df['EMA_200'] = ta.ema(df['close'], length=200)
    return df

def ask_gemini(df):
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
        return f"Error: {e}"

def send_discord(message):
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    if not GEMINI_API_KEY or not DISCORD_WEBHOOK_URL:
        print("Error: APIキーが設定されていません")
        exit()
        
    df = get_market_data()
    analysis = ask_gemini(df)
    print(analysis)
    send_discord(analysis)
