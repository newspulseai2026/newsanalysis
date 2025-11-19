import streamlit as st
import requests
from bs4 import BeautifulSoup

# ---------------------------
# CONFIG
# ---------------------------

INVESTING_URL = "https://www.investing.com/news/cryptocurrency-news"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"

# ---------------------------
# LANGUAGE DICTIONARY
# ---------------------------

LANG = {
    "fa": {
        "title": "📊 تحلیل اخبار و قیمت کریپتو",
        "refresh": "🔄 رفرش اطلاعات",
        "fetching": "در حال دریافت اطلاعات...",
        "latest_news": "📰 آخرین اخبار کریپتو",
        "price": "💰 قیمت لحظه‌ای BTC",
        "click_refresh": "برای دریافت اطلاعات جدید دکمه رفرش را بزن.",
        "success": "اطلاعات به‌روزرسانی شد."
    },
    "en": {
        "title": "📊 Crypto News & Price Analyzer",
        "refresh": "🔄 Refresh Data",
        "fetching": "Fetching latest data...",
        "latest_news": "📰 Latest Crypto News",
        "price": "💰 Live BTC Price",
        "click_refresh": "Click refresh button to update data.",
        "success": "Data refreshed successfully."
    },
    "ar": {
        "title": "📊 تحليل أخبار وأسعار العملات الرقمية",
        "refresh": "🔄 تحديث البيانات",
        "fetching": "جاري جلب البيانات...",
        "latest_news": "📰 آخر أخبار العملات الرقمية",
        "price": "💰 سعر البيتكوين اللحظي",
        "click_refresh": "اضغط زر التحديث لجلب البيانات الجديدة.",
        "success": "تم تحديث البيانات بنجاح."
    },
}

# ---------------------------
# FUNCTIONS
# ---------------------------

def fetch_crypto_news(limit=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(INVESTING_URL, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    items = soup.select("a.title")
    for a in items[:limit]:
        title = a.get_text(strip=True)
        link = a.get("href")
        if link and not link.startswith("http"):
            link = "https://www.investing.com" + link
        results.append({"title": title, "link": link})
    return results


def fetch_price(symbol_id):
    params = {"ids": symbol_id, "vs_currencies": "usd"}
    resp = requests.get(COINGECKO_API, params=params)
    data = resp.json()
    return data[symbol_id]["usd"]

# ---------------------------
# STREAMLIT UI
# ---------------------------

# Language selector
lang_code = st.sidebar.selectbox(
    "🌍 Language / زبان / اللغة",
    options=["fa", "en", "ar"],
    format_func=lambda x: {"fa": "فارسی", "en": "English", "ar": "العربية"}[x]
)

T = LANG[lang_code]  # selected language dictionary

st.title(T["title"])

if st.button(T["refresh"]):
    st.success(T["fetching"])

    # Fetch news
    news = fetch_crypto_news()

    st.subheader(T["latest_news"])
    for n in news:
        st.write(f"- [{n['title']}]({n['link']})")

    # Fetch BTC price
    price = fetch_price("bitcoin")
    st.subheader(T["price"])
    st.write(f"{price} USD")

    st.success(T["success"])

else:
    st.info(T["click_refresh"])
