# app.py
# RUN: pip install streamlit feedparser yfinance ccxt pandas scikit-learn google-generativeai

import streamlit as st
import feedparser
import yfinance as yf
import ccxt
import pandas as pd
import numpy as np
import time
import google.generativeai as genai
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="AI Market Predictor", layout="wide")
st.title("📈 پیش‌بینی بازار با Gemini (کاملاً رایگان)")

# -------------------------
# Sidebar Settings
# -------------------------
st.sidebar.header("تنظیمات")

GEMINI_KEY = "AIzaSyAA90H731pSoYBT7q3yrHEUmM5bwP7wtQs"

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")   # رایگان و سریع

stock_symbol = st.sidebar.text_input("سهام", "AAPL")
crypto_symbol = st.sidebar.text_input("کریپتو", "BTC/USDT")
metal_symbol = st.sidebar.selectbox("فلز", ["GC=F (Gold)", "SI=F (Silver)"])
metal_symbol = metal_symbol.split()[0]

# -------------------------
# Functions
# -------------------------
RSS = "https://www.investing.com/rss/news_25.rss"

def get_news(n=7):
    feed = feedparser.parse(RSS)
    return feed.entries[:n]

def get_stock(symbol):
    t = yf.Ticker(symbol)
    df = t.history(period="1d", interval="1m")
    if df.empty:
        return None, None
    return df["Close"].iloc[-1], df["Close"]

def get_crypto(symbol):
    ex = ccxt.binance()
    t = ex.fetch_ticker(symbol)
    return t["last"]

def get_crypto_history(symbol):
    ex = ccxt.binance()
    ohlcv = ex.fetch_ohlcv(symbol, "1m", limit=60)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])
    return df["c"]

def get_metal(symbol):
    t = yf.Ticker(symbol)
    df = t.history(period="1d", interval="1m")
    if df.empty:
        return None, None
    return df["Close"].iloc[-1], df["Close"]

def predict_local(series):
    if series is None or len(series) < 10:
        return None
    X = np.arange(len(series)).reshape(-1,1)
    y = series.values.reshape(-1,1)
    lr = LinearRegression().fit(X, y)
    pred = lr.predict([[len(series)]])
    return float(pred[0][0])

# -------------------------
# MAIN BUTTON
# -------------------------
if st.button("🚀 دریافت دیتا + تحلیل Gemini"):
    with st.spinner("در حال جمع‌آوری اطلاعات..."):
        t0 = time.time()

        # news
        news = get_news()
        news_text = "".join([f"- {n.title}\n" for n in news])

        # prices
        stock_price, stock_hist = get_stock(stock_symbol)
        crypto_price = get_crypto(crypto_symbol)
        crypto_hist = get_crypto_history(crypto_symbol)
        metal_price, metal_hist = get_metal(metal_symbol)

        # local predictions
        stock_pred = predict_local(stock_hist)
        crypto_pred = predict_local(crypto_hist)
        metal_pred = predict_local(metal_hist)

        # -------------------------
        # Gemini Prompt
        # -------------------------
        if GEMINI_KEY:
            prompt = (
                "اخبار اقتصادی امروز:\n"
                + news_text
                + f"قیمت‌ها:\n"
                  f"- سهام {stock_symbol}: {stock_price}\n"
                  f"- کریپتو {crypto_symbol}: {crypto_price}\n"
                  f"- فلز {metal_symbol}: {metal_price}\n"
                  f"پیش‌بینی محلی:\n"
                  f"- سهام: {stock_pred}\n"
                  f"- کریپتو: {crypto_pred}\n"
                  f"- فلز: {metal_pred}\n"
                  "لطفاً تحلیل تو، روندها، و پیش‌بینی کوتاه‌مدت خودت را بده."
            )                
            ai_output = model.generate_content(prompt).text
        else:
            ai_output = "❗ Gemini API key وارد نشده — فقط پیش‌بینی محلی نمایش داده می‌شود."

        elapsed = time.time() - t0

    st.success(f"انجام شد! ({elapsed:.1f} ثانیه)")

    # -------------------------
    # Display
    # -------------------------
    st.subheader("📰 آخرین خبرهای اقتصادی")
    for n in news:
        st.markdown(f"### {n.title}")
        st.write(n.summary)
        st.markdown(f"[لینک خبر]({n.link})")
        st.markdown("---")

    st.subheader("💹 قیمت‌ها + پیش‌بینی‌ها")
    st.write({
        "stock_price": stock_price,
        "stock_pred": stock_pred,
        "crypto_price": crypto_price,
        "crypto_pred": crypto_pred,
        "metal_price": metal_price,
        "metal_pred": metal_pred,
    })

    st.subheader("🤖 تحلیل Gemini")
    st.write(ai_output)
