# Full-featured Streamlit Crypto Dashboard with:
# - Multi-language (EN/FA/AR)
# - RTL/LTR UI
# - Refresh button
# - RSS crypto news
# - Multi-coin prices
# - Sentiment analysis using Gemini API
# - Price chart using CoinGecko market data
# NOTE: Replace YOUR_GEMINI_API_KEY with your actual key.

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
from datetime import datetime, timedelta

# ---------------------------
# CONFIG
# ---------------------------
RSS_URL = "https://www.investing.com/rss/news_301.rss"
COINGECKO_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_CHART_API = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_MODEL = "gemini-2.0-flash"

SUPPORTED_COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

# ---------------------------
# LANG DICTIONARY
# ---------------------------
LANG = {
    "en": {
        "title": "📊 Advanced Crypto Dashboard",
        "refresh": "🔄 Refresh Data",
        "fetching": "Fetching latest data...",
        "latest_news": "📰 Latest Crypto News",
        "price": "💰 Live Prices",
        "choose_coin": "Select a coin",
        "chart": "📈 7-Day Price Chart",
        "analysis": "🤖 AI News Sentiment Analysis",
        "click_refresh": "Press refresh to load latest data.",
        "success": "Data updated successfully.",
    },
    "fa": {
        "title": "📊 داشبورد پیشرفته کریپتو",
        "refresh": "🔄 رفرش اطلاعات",
        "fetching": "در حال دریافت اطلاعات...",
        "latest_news": "📰 آخرین اخبار کریپتو",
        "price": "💰 قیمت‌های لحظه‌ای",
        "choose_coin": "رمزارز را انتخاب کنید",
        "chart": "📈 نمودار ۷ روزه قیمت",
        "analysis": "🤖 تحلیل هوشمند اخبار",
        "click_refresh": "برای دریافت اطلاعات جدید دکمه را بزنید.",
        "success": "اطلاعات با موفقیت به‌روزرسانی شد.",
    },
    "ar": {
        "title": "📊 لوحة تحكم العملات الرقمية المتقدمة",
        "refresh": "🔄 تحديث البيانات",
        "fetching": "جاري جلب البيانات...",
        "latest_news": "📰 آخر أخبار العملات الرقمية",
        "price": "💰 أسعار مباشرة",
        "choose_coin": "اختر العملة",
        "chart": "📈 مخطط السعر لمدة 7 أيام",
        "analysis": "🤖 تحليل ذكي للأخبار",
        "click_refresh": "اضغط تحديث للحصول على أحدث البيانات.",
        "success": "تم التحديث بنجاح.",
    }
}

# ---------------------------
# FUNCTIONS
# ---------------------------
def fetch_crypto_news_from_rss(limit=10):
    resp = requests.get(RSS_URL)
    root = ET.fromstring(resp.content)
    items = []
    for item in root.iter("item"):
        title = item.find("title").text
        link = item.find("link").text
        items.append({"title": title, "link": link})
        if len(items) >= limit:
            break
    return items


def fetch_price(coin):
    params = {"ids": coin, "vs_currencies": "usd"}
    r = requests.get(COINGECKO_PRICE_API, params=params).json()
    return r[coin]["usd"]


def fetch_chart(coin):
    url = COINGECKO_CHART_API.format(coin=coin)
    params = {"vs_currency": "usd", "days": 7}
    data = requests.get(url, params=params).json()

    prices = data.get("prices", [])
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    return df


def analyze_with_gemini(text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": f"Analyze sentiment of this crypto news title and give effect on price: {text}"}]}]
    }
    params = {"key": GEMINI_API_KEY}

    r = requests.post(url, headers=headers, json=payload, params=params).json()
    try:
        return r["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "AI Error or Invalid API key."


# ---------------------------
# STREAMLIT UI
# ---------------------------
lang_code = st.sidebar.selectbox(
    "🌍 Language / زبان / اللغة", ["en", "fa", "ar"], index=0
)
T = LANG[lang_code]

# RTL/LTR
if lang_code == "en":
    direction = "ltr"
    align = "left"
else:
    direction = "rtl"
    align = "right"

st.markdown(f"""
<style>
    .main-container {{ direction: {direction}; text-align: {align}; }}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.title(T["title"])

selected_coin = st.selectbox(T["choose_coin"], list(SUPPORTED_COINS.keys()), format_func=lambda c: SUPPORTED_COINS[c])

if st.button(T["refresh"]):
    st.info(T["fetching"])

    # NEWS
    news = fetch_crypto_news_from_rss()

    st.subheader(T["latest_news"])
    for n in news:
        st.write(f"• [{n['title']}]({n['link']})")

    # PRICES
    st.subheader(T["price"])
    placeholder_prices = st.empty()

    # ---- Free REAL-TIME prices using Binance WebSocket ----
    import websocket
    import json

    def get_live_price(symbol):
        ws_url = f"wss://stream.binance.com:9443/ws/{symbol}usdt@trade"
        price_box = st.empty()

        def on_message(ws, message):
            data = json.loads(message)
            price = float(data['p'])
            price_box.write(f"{symbol.upper()}: {price} USD")

        ws = websocket.WebSocketApp(ws_url, on_message=on_message)
        ws.run_forever(dispatcher=None)

    # Display live prices for BTC / ETH / SOL
    for coin, symbol in SUPPORTED_COINS.items():
        st.write(f"Live {symbol} price streaming…")
        st.threaded(get_live_price, args=(coin,))

    # CHART
    st.subheader(T["chart"])
    df = fetch_chart(selected_coin)
    st.line_chart(df.set_index("timestamp"))

    # AI ANALYSIS
    st.subheader(T["analysis"])
    ai_result = analyze_with_gemini(news[0]["title"])
    st.write(ai_result)

    st.success(T["success"])

else:
    st.info(T["click_refresh"])

st.markdown('</div>', unsafe_allow_html=True)
