# Streamlit Crypto Dashboard (Multi-language, Live Prices, RSS News, Gemini Analysis)
# Fully rewritten + cleaned

import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import json

# ==========================
# CONFIG
# ==========================
RSS_URL = "https://www.investing.com/rss/news_301.rss"
COINGECKO_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_CHART_API = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
GEMINI_API_KEY = "AIzaSyAA90H731pSoYBT7q3yrHEUmM5bwP7wtQs"
GEMINI_MODEL = "gemini-2.5-pro"

SUPPORTED_COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "ripple": "XRP",
    "cardano": "ADA",
    "dogecoin": "DOGE",
    "tron": "TRX",
    "litecoin": "LTC",
    "polkadot": "DOT",
    "avalanche": "AVAX"
}

# ==========================
# MULTI-LANGUAGE TEXT
# ==========================
LANG = {
    "en": {
        "title": "📊 Advanced Crypto Dashboard",
        "refresh_news": "🔄 Refresh News",
        "analyze": "🤖 Run AI Analysis",
        "news": "📰 Latest Crypto News",
        "prices": "💰 Live Prices",
        "analysis": "📡 AI Market Impact Analysis",
        "chart": "📈 7‑Day Price Chart",
        "choose": "Select coin",
        "success": "Data updated.",
        "wait": "Fetching data..."
    },
    "fa": {
        "title": "📊 داشبورد پیشرفته کریپتو",
        "refresh_news": "🔄 رفرش اخبار",
        "analyze": "🤖 تحلیل هوشمند",
        "news": "📰 آخرین اخبار کریپتو",
        "prices": "💰 قیمت لحظه‌ای",
        "analysis": "📡 تحلیل اثر اخبار بر بازار",
        "chart": "📈 نمودار ۷ روزه",
        "choose": "انتخاب رمزارز",
        "success": "اطلاعات به‌روزرسانی شد.",
        "wait": "در حال دریافت اطلاعات..."
    },
    "ar": {
        "title": "📊 لوحة تحكم العملات الرقمية",
        "refresh_news": "🔄 تحديث الأخبار",
        "analyze": "🤖 تحليل ذكي",
        "news": "📰 آخر أخبار الكريبتو",
        "prices": "💰 الأسعار المباشرة",
        "analysis": "📡 تحليل تأثير الأخبار",
        "chart": "📈 مخطط 7 أيام",
        "choose": "اختر العملة",
        "success": "تم التحديث.",
        "wait": "جاري جلب البيانات..."
    }
}

# ==========================
# FUNCTIONS
# ==========================

def fetch_news(limit=10):
    r = requests.get(RSS_URL)
    root = ET.fromstring(r.content)
    out = []
    for item in root.iter("item"):
        out.append({"t": item.find("title").text, "l": item.find("link").text})
        if len(out) >= limit:
            break
    return out


def get_prices():
    ids = ",".join(SUPPORTED_COINS.keys())
    params = {"ids": ids, "vs_currencies": "usd"}
    return requests.get(COINGECKO_PRICE_API, params=params).json()


def get_chart(coin):
    url = COINGECKO_CHART_API.format(coin=coin)
    data = requests.get(url, params={"vs_currency": "usd", "days": 7}).json()
    df = pd.DataFrame(data.get("prices", []), columns=["ts", "price"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df


def gemini_analysis(news_titles, price_data):
    text_news = "
".join([f"- {n['t']}" for n in news_titles])
    text_prices = json.dumps(price_data, indent=2)

    prompt = f"""
You are an expert crypto quantitative analyst.
Analyze ALL NEWS ITEMS INDIVIDUALLY.

For EACH news headline, output ONLY this structured format:

Headline: <headline>
Impacted Coins: <list>
Expected Move: +X% to +Y% OR -X% to -Y%
Reason: <short explanation>

Rules:
- DO NOT output sentiment labels.
- Only output percentage change prediction.
- Keep each explanation short and numerical.
- Use realistic crypto‑market reaction ranges.

After individual analysis, provide a final section:

OVERALL MARKET SUMMARY:
- Coins likely to rise: ...
- Coins likely to fall: ...
- Estimated total market direction: <Up/Down/Sideways>
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=payload, params={"key": GEMINI_API_KEY}).json()

    try:
        return r["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Gemini API Error. Check API key." r["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Gemini API Error. Check API key." r["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Gemini API Error. Check API key."


# ==========================
# UI SETUP
# ==========================
lang = st.sidebar.selectbox("🌍 Language", ["en", "fa", "ar"], index=0)
T = LANG[lang]

if lang == "en":
    st.markdown("<style>.main{direction:ltr;text-align:left;}</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.main{direction:rtl;text-align:right;}</style>", unsafe_allow_html=True)

st.markdown('<div class="main">', unsafe_allow_html=True)

# ==========================
# TITLE
# ==========================
st.title(T["title"])

# ==========================
# BUTTONS
# ==========================
col1, col2 = st.columns(2)
btn_news = col1.button(T["refresh_news"])
btn_ai = col2.button(T["analyze"])

# ==========================
# ACTIONS
# ==========================
if btn_news:
    st.info(T["wait"])
    news = fetch_news()
    prices = get_prices()

    st.subheader(T["news"])
    for n in news:
        st.write(f"• [{n['t']}]({n['l']})")

    st.subheader(T["prices"])
    for coin, symbol in SUPPORTED_COINS.items():
        if coin in prices:
            st.write(f"{symbol}: {prices[coin]['usd']} USD")

    st.subheader(T["chart"])
    chosen = st.selectbox(T["choose"], list(SUPPORTED_COINS.keys()))
    st.line_chart(get_chart(chosen).set_index("ts"))

    st.success(T["success"])

if btn_ai:
    st.subheader(T["analysis"])
    news = fetch_news()
    prices = get_prices()
    out = gemini_analysis(news, prices)
    st.write(out)

st.markdown('</div>', unsafe_allow_html=True)
