import streamlit as st
import requests
import xml.etree.ElementTree as ET

# ---------------------------
# CONFIG
# ---------------------------

RSS_URL = "https://www.investing.com/rss/news_301.rss"
COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price"


# ---------------------------
# LANG DICTIONARY
# ---------------------------

LANG = {
    "en": {
        "title": "📊 Crypto News & Price Analyzer",
        "refresh": "🔄 Refresh Data",
        "fetching": "Fetching latest data...",
        "latest_news": "📰 Latest Crypto News",
        "price": "💰 Live BTC Price",
        "click_refresh": "Click refresh to get the latest data.",
        "success": "Data refreshed successfully."
    },
    "fa": {
        "title": "📊 تحلیل اخبار و قیمت کریپتو",
        "refresh": "🔄 رفرش اطلاعات",
        "fetching": "در حال دریافت اطلاعات...",
        "latest_news": "📰 آخرین اخبار کریپتو",
        "price": "💰 قیمت لحظه‌ای BTC",
        "click_refresh": "برای دریافت اطلاعات جدید دکمه رفرش را بزن.",
        "success": "اطلاعات با موفقیت به‌روزرسانی شد."
    },
    "ar": {
        "title": "📊 تحليل أخبار وأسعار العملات الرقمية",
        "refresh": "🔄 تحديث البيانات",
        "fetching": "جاري جلب البيانات...",
        "latest_news": "📰 آخر أخبار العملات الرقمية",
        "price": "💰 السعر اللحظي لبيتكوين",
        "click_refresh": "اضغط زر التحديث للحصول على أحدث البيانات.",
        "success": "تم تحديث البيانات بنجاح."
    },
}


# ---------------------------
# FUNCTIONS
# ---------------------------

def fetch_crypto_news_from_rss(limit=10):
    resp = requests.get(RSS_URL)
    root = ET.fromstring(resp.content)

    items = []
    for item
