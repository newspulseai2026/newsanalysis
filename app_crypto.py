# Full-featured Streamlit Crypto Dashboard with:
# - Multi-language (EN/FA/AR)
# - RTL/LTR UI
# - Refresh / Live toggle
# - RSS crypto news
# - Top-10 live prices (free via CoinGecko polling)
# - AI impact prediction per news (which coins go up/down) using Gemini
# NOTE: Replace YOUR_GEMINI_API_KEY with your actual key.

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import json
from datetime import datetime

# ---------------------------
# CONFIG
# ---------------------------
RSS_URL = "https://www.investing.com/rss/news_301.rss"
COINGECKO_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_CHART_API = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
GEMINI_API_KEY = "AIzaSyAA90H731pSoYBT7q3yrHEUmM5bwP7wtQs"
GEMINI_MODEL = "gemini-2.5-pro"

# Top 10 coins (CoinGecko ids -> display symbol)
SUPPORTED_COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binancecoin": "BNB",
    "solana": "SOL",
    "cardano": "ADA",
    "ripple": "XRP",
    "dogecoin": "DOGE",
    "polkadot": "DOT",
    "litecoin": "LTC",
    "avalanche-2": "AVAX",
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
        "price": "💰 Live Prices (Top 10)",
        "live_toggle": "Start Live Prices",
        "stop_live": "Stop Live",
        "choose_coin": "Select a coin",
        "chart": "📈 7-Day Price Chart",
        "analysis": "🤖 AI News Impact Predictions",
        "click_refresh": "Press refresh to load latest data.",
        "success": "Data updated successfully.",
    },
    "fa": {
        "title": "📊 داشبورد پیشرفته کریپتو",
        "refresh": "🔄 رفرش اطلاعات",
        "fetching": "در حال دریافت اطلاعات...",
        "latest_news": "📰 آخرین اخبار کریپتو",
        "price": "💰 قیمت‌های لحظه‌ای (۱۰ رمزارز برتر)",
        "live_toggle": "شروع قیمت لحظه‌ای",
        "stop_live": "توقف قیمت لحظه‌ای",
        "choose_coin": "رمزارز را انتخاب کنید",
        "chart": "📈 نمودار ۷ روزه قیمت",
        "analysis": "🤖 پیش‌بینی اثر اخبار روی قیمت‌ها",
        "click_refresh": "برای دریافت اطلاعات جدید دکمه را بزنید.",
        "success": "اطلاعات با موفقیت به‌روزرسانی شد.",
    },
    "ar": {
        "title": "📊 لوحة تحكم العملات الرقمية المتقدمة",
        "refresh": "🔄 تحديث البيانات",
        "fetching": "جاري جلب البيانات...",
        "latest_news": "📰 آخر أخبار العملات الرقمية",
        "price": "💰 الأسعار اللحظية (أفضل 10 عملات)",
        "live_toggle": "بدء العرض اللحظي",
        "stop_live": "إيقاف العرض",
        "choose_coin": "اختر العملة",
        "chart": "📈 مخطط السعر لمدة 7 أيام",
        "analysis": "🤖 توقعات تأثير الأخبار على الأسعار",
        "click_refresh": "اضغط لتحديث البيانات.",
        "success": "تم تحديث البيانات بنجاح.",
    }
}

# ---------------------------
# HELPERS
# ---------------------------

def fetch_crypto_news_from_rss(limit=5):
    resp = requests.get(RSS_URL, timeout=10)
    root = ET.fromstring(resp.content)
    items = []
    for item in root.iter("item"):
        title = item.find("title").text
        link = item.find("link").text
        items.append({"title": title, "link": link})
        if len(items) >= limit:
            break
    return items


def fetch_prices_bulk(coins):
    ids = ",".join(coins)
    params = {"ids": ids, "vs_currencies": "usd"}
    r = requests.get(COINGECKO_PRICE_API, params=params, timeout=10).json()
    rows = []
    for coin in coins:
        price = r.get(coin, {}).get("usd")
        rows.append({"id": coin, "symbol": SUPPORTED_COINS.get(coin, coin).upper(), "price": price})
    return pd.DataFrame(rows)


def fetch_chart(coin):
    url = COINGECKO_CHART_API.format(coin=coin)
    params = {"vs_currency": "usd", "days": 7}
    data = requests.get(url, params=params, timeout=10).json()
    prices = data.get("prices", [])
    df = pd.DataFrame(prices, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    return df


def analyze_news_impact_with_gemini(news_title, coins_list):
    # Build a prompt that asks Gemini to return JSON mapping coin -> {move: up/down/neutral, pct: float}
    coins_str = ", ".join([SUPPORTED_COINS[c] for c in coins_list])
    prompt = (
        f"News title: \"{news_title}\"\n"
        f"Given this crypto news headline, list which of these coins are likely to go UP, DOWN or NEUTRAL in the next short term: {coins_str}.\n"
        "Respond ONLY in JSON with this structure:\n"
        "{\"predictions\": {\"bitcoin\": {\"move\": \"up\", \"pct\": 2.5}, ...}}\n"
        "Each pct should be a rough percent estimate (use null if unknown)."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}
    body = {
        "prompt": prompt,
        "max_output_tokens": 300
    }
    params = {"key": GEMINI_API_KEY}

    try:
        resp = requests.post(url, headers=headers, json=body, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # extract candidate text (Gemini responses vary in shape)
        text = None
        if "candidates" in data and len(data["candidates"])>0:
            cand = data["candidates"][0]
            if isinstance(cand, dict):
                if "content" in cand and isinstance(cand["content"], dict):
                    parts = cand["content"].get("parts")
                    if parts and isinstance(parts, list):
                        text = parts[0]
                elif "output" in cand:
                    text = cand.get("output")
                else:
                    text = json.dumps(cand)
            else:
                text = str(cand)
        else:
            text = json.dumps(data)

        if text is None:
            return {"error": "No text from model"}

        text_str = text if isinstance(text, str) else json.dumps(text)

        # find JSON substring containing "predictions"
        import re
        m = re.search(r"\{\s*\"predictions\"[\s\S]*\}", text_str)
        if m:
            json_text = m.group(0)
        else:
            json_text = text_str

        predictions = json.loads(json_text)
        return predictions

    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# STREAMLIT UI
# ---------------------------
st.set_page_config(page_title="Crypto Dashboard", layout="wide")

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
    .small-caption {{ font-size: 0.9em; color: #666 }}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.title(T["title"])

col_left, col_right = st.columns([2,1])

with col_left:
    selected_coin = st.selectbox(T["choose_coin"], list(SUPPORTED_COINS.keys()), format_func=lambda c: SUPPORTED_COINS[c])

with col_right:
    if "live" not in st.session_state:
        st.session_state.live = False
    live_control = st.button(T["live_toggle"]) if not st.session_state.live else st.button(T["stop_live"]) 
    if live_control:
        st.session_state.live = not st.session_state.live

# Refresh button
if st.button(T["refresh"]):
    st.info(T["fetching"])

    # Load News
    news = fetch_crypto_news_from_rss(limit=5)

    st.subheader(T["latest_news"])
    for i, n in enumerate(news, start=1):
        st.write(f"{i}. [{n['title']}]({n['link']})")

    # AI predictions for each news (map to top-10 coins)
    st.subheader(T["analysis"])
    coins_list = list(SUPPORTED_COINS.keys())
    predictions_all = {}
    for n in news:
        pred = analyze_news_impact_with_gemini(n["title"], coins_list)
        predictions_all[n["title"]] = pred
        if "error" in pred:
            st.write(f"AI Error for news: {n['title']} -> {pred['error']}")
        else:
            # show a compact table of coin moves
            rows = []
            preds = pred.get("predictions", {})
            for coin in coins_list:
                p = preds.get(coin, {})
                move = p.get("move") if isinstance(p, dict) else None
                pct = p.get("pct") if isinstance(p, dict) else None
                rows.append({"coin": SUPPORTED_COINS.get(coin, coin).upper(), "move": move, "pct": pct})
            dfp = pd.DataFrame(rows)
            st.table(dfp)

    # Prices snapshot
    st.subheader(T["price"])
    df_prices = fetch_prices_bulk(list(SUPPORTED_COINS.keys()))
    st.dataframe(df_prices.set_index("symbol"))

    # Chart for selected coin
    st.subheader(T["chart"])
    df_chart = fetch_chart(selected_coin)
    st.line_chart(df_chart.set_index("timestamp"))

    st.success(T["success"])

else:
    st.info(T["click_refresh"])

# Live price area (polling CoinGecko every N seconds)
st.markdown("---")
st.subheader("🔔 Live Top-10 Prices")

live_placeholder = st.empty()

refresh_interval = st.sidebar.slider("Refresh interval (seconds)", min_value=2, max_value=30, value=5)

# Live control note
st.caption("Use the sidebar language selector and 'Start Live Prices' / 'Stop Live' button to toggle live updates.")

if st.session_state.live:
    try:
        while st.session_state.live:
            df_live = fetch_prices_bulk(list(SUPPORTED_COINS.keys()))
            df_live_display = df_live.copy()
            df_live_display["price"] = df_live_display["price"].apply(lambda x: f"{x:.6f}" if isinstance(x, float) and x<1 else (f"{x:.2f}" if isinstance(x, float) else x))
            # optionally compute small changes if previous snapshot exists
            if "_prev_prices" in st.session_state:
                prev = st.session_state._prev_prices
                merged = df_live_display.merge(prev[["id","price"]], on="id", how="left", suffixes=("","_prev"))
                def pct_change(row):
                    try:
                        p = float(row["price"])
                        pp = float(row["price_prev"]) if row.get("price_prev") is not None else None
                        if pp:
                            return round((p-pp)/pp*100, 2)
                    except:
                        return None
                merged["chg_pct"] = merged.apply(pct_change, axis=1)
                display_df = merged[["symbol","price","chg_pct"]].set_index("symbol")
            else:
                display_df = df_live_display[["symbol","price"]].set_index("symbol")

            live_placeholder.dataframe(display_df)
            st.session_state._prev_prices = df_live_display
            time.sleep(refresh_interval)
    except Exception as e:
        st.error(f"Live update error: {e}")
else:
    # show last snapshot (once)
    df_prices = fetch_prices_bulk(list(SUPPORTED_COINS.keys()))
    live_placeholder.dataframe(df_prices.set_index("symbol"))

st.markdown('</div>', unsafe_allow_html=True)
