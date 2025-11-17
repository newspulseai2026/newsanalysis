# app.py — Full expert (Persian)
# Run: pip install streamlit feedparser yfinance ccxt requests pandas scikit-learn matplotlib
# Then: streamlit run app.py

import streamlit as st
import feedparser
import yfinance as yf
import ccxt
import requests
import pandas as pd
import numpy as np
import time
import datetime
from sklearn.linear_model import LinearRegression
from typing import Optional, Dict, Any

st.set_page_config(page_title="اقتصادی‌خوان + Gemini پیش‌بینی (Full expert)", layout="wide")
st.title("اقتصادی‌خوان + پیش‌بینی (Gemini 2.5 Pro) — نسخه Full expert")
st.write("هدف: با یک کلیک اخبار اقتصادی را بخوانیم، قیمت‌های لحظه‌ای (سهام، رمزارز، فلزات) را بگیریم و خروجی تحلیلی و پیش‌بینی عددی از Gemini دریافت کنیم. برای فلزات از yfinance (تیکرهای Futures) استفاده شده تا سرویس پولی نیاز نباشد.")

# ---------------------------
# Sidebar settings
# ---------------------------
st.sidebar.header("تنظیمات اتصال و نمادها")
GEMINI_API_KEY = st.sidebar.text_input("Gemini API Key (کلید Google / Generative API)", type="password")
GEMINI_API_URL = st.sidebar.text_input("Gemini API URL (در صورت نیاز به override)", value="https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generate")
CACHE_TTL = st.sidebar.number_input("Cache (ثانیه)", min_value=30, value=60)
CRYPTO_EXCHANGE = st.sidebar.selectbox("Exchange (ccxt)", ["binance", "kraken", "coinbasepro"], index=0)

st.sidebar.markdown("**نمادها** (می‌تونی چندتا جداشده با کاما وارد کنی)")
stock_symbols = st.sidebar.text_input("سهام (مثال: AAPL,MSFT,GOOG)", value="AAPL")
crypto_symbols = st.sidebar.text_input("رمزارزها (مثال: BTC/USDT,ETH/USDT)", value="BTC/USDT")
metal_choice = st.sidebar.selectbox("فلز (قیمت از yfinance استفاده می‌شود)", ["Gold (XAU) — GC=F", "Silver (XAG) — SI=F"], index=0)

INVESTING_RSS = st.sidebar.text_input("Investing.com RSS (Economic news feed)", value="https://www.investing.com/rss/news_25.rss")

# ---------------------------
# Helpers & caching
# ---------------------------
@st.cache_data(ttl=300)
def parse_rss(url: str, max_items: int = 10):
    try:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:max_items]:
            items.append({
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
                "summary": e.get("summary", "")
            })
        return items
    except Exception as e:
        return []

@st.cache_data(ttl=300)
def fetch_yfinance_quote(ticker: str):
    try:
        t = yf.Ticker(ticker)
        # try to get intraday 1m
        hist = t.history(period="1d", interval="1m")
        if hist is None or hist.empty:
            info = t.info if hasattr(t, "info") else {}
            price = info.get("regularMarketPrice", None)
            return {"price": price, "history": None}
        else:
            last = float(hist['Close'].iloc[-1])
            return {"price": last, "history": hist['Close']}
    except Exception as e:
        return {"price": None, "history": None}

@st.cache_data(ttl=60)
def fetch_crypto_ticker(symbol: str, exchange_id: str = "binance"):
    try:
        exchange_cls = getattr(ccxt, exchange_id)
        ex = exchange_cls({"enableRateLimit": True})
        ticker = ex.fetch_ticker(symbol)
        return {"price": float(ticker['last']), "raw": ticker}
    except Exception as e:
        return {"price": None, "raw": None}

def simple_linear_predict(series: pd.Series, steps: int = 1) -> Optional[float]:
    try:
        if series is None or len(series) < 6:
            return None
        y = series.values.reshape(-1, 1)
        X = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, y)
        next_idx = np.array([[len(y) + (steps - 1)]])
        pred = model.predict(next_idx)
        return float(pred.ravel()[0])
    except Exception:
        return None

def build_structured_prompt(news: list, prices: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Build a clear, structured prompt for Gemini:
    - include brief instruction
    - include JSON-like data: news list, current prices, recent trends (mini-series)
    - request concise numeric predictions and confidence
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"
    prompt = []
    prompt.append("You are a financial expert. Provide a concise analysis and numeric short-term price predictions.")
    prompt.append("Return a JSON object with keys: summary, prediction_1h, prediction_24h, confidence_percent, rationale.")
    prompt.append(f"metadata: {metadata}")
    prompt.append("Recent news (title + short summary):")
    for n in news:
        prompt.append(f"- {n.get('published','')} | {n.get('title','')} — {n.get('summary','')}")
    prompt.append("Current prices (dict):")
    prompt.append(str(prices))
    prompt.append("Requests:")
    prompt.append("1) Provide point-estimates for the following: next 1 hour price and next 24 hours price (use same quote currency as provided).")
    prompt.append("2) Provide confidence as percent (0-100) and a one-paragraph rationale.")
    prompt.append("3) At the end output only a JSON object (no extra prose) — keys as described above. Numeric fields should be numbers (not words).")
    return "\n\n".join(prompt)

def call_gemini_api(prompt_text: str, api_key: str, api_url: str = None, timeout: int = 30) -> Dict[str, Any]:
    """
    Attempts to call Google Generative Language API endpoint for Gemini.
    NOTE: If Google changed the endpoint or payload, update api_url accordingly.
    api_url default is the value passed from sidebar (we set a reasonable default there).
    """
    if not api_key:
        return {"error": "no_api_key"}
    url = api_url or "https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"}
    # payload following google generativelanguage typical pattern (subject to changes)
    payload = {
        "prompt": {
            "text": prompt_text
        },
        "temperature": 0.2,
        "maxOutputTokens": 500
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        return {"status_code": r.status_code, "response": r.json() if r.content else None, "text": r.text}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------
# UI / Main flow
# ---------------------------
col1, col2 = st.columns([2, 3])
with col1:
    st.header("کنترل و اجرای خواندن / پیش‌بینی")
    st.write("روی دکمه کلیک کن تا: اخبار را بخوانیم، قیمت‌های لحظه‌ای را بگیریم و (در صورت دادن کلید) از Gemini درخواست تحلیل کنیم.")
    if st.button("خواندن و تحلیل (Run)"):
        t0 = time.time()
        with st.spinner("در حال واکشی خبرها و قیمت‌ها..."):
            # 1) news
            news = parse_rss(INVESTING_RSS, max_items=8)

            # 2) prices
            stocks = [s.strip().upper() for s in stock_symbols.split(",") if s.strip()]
            cryptos = [c.strip().upper() for c in crypto_symbols.split(",") if c.strip()]

            prices = {"stocks": {}, "cryptos": {}, "metals": {}}

            for s in stocks:
                p = fetch_yfinance_quote(s)
                prices["stocks"][s] = {"price": p["price"]}
                # attach small series if available
                if p["history"] is not None:
                    prices["stocks"][s]["last_series_len"] = len(p["history"])
                    prices["stocks"][s]["recent_close_last"] = float(p["history"].iloc[-1])

            for c in cryptos:
                q = fetch_crypto_ticker(c, CRYPTO_EXCHANGE)
                prices["cryptos"][c] = {"price": q["price"]}

            # metals via futures tickers in yfinance
            if "Gold" in metal_choice:
                metal_ticker = "GC=F"
            else:
                metal_ticker = "SI=F"
            metal_q = fetch_yfinance_quote(metal_ticker)
            prices["metals"][metal_choice] = {"ticker": metal_ticker, "price": metal_q["price"]}

            # 3) lightweight local predictions (fallback)
            local_preds = {"stocks": {}, "cryptos": {}, "metals": {}}
            for s in stocks:
                p = fetch_yfinance_quote(s)
                local_preds["stocks"][s] = {"pred_1_step": None}
                if p.get("history") is not None:
                    pred = simple_linear_predict(p["history"], steps=1)
                    local_preds["stocks"][s]["pred_1_step"] = pred

            # crypto local via OHLCV if possible
            try:
                ex_cls = getattr(ccxt, CRYPTO_EXCHANGE)
                ex = ex_cls({"enableRateLimit": True})
                for c in cryptos:
                    try:
                        ohlcv = ex.fetch_ohlcv(c, timeframe='1m', limit=30)
                        df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])
                        local_preds["cryptos"][c] = {"pred_1_step": simple_linear_predict(df['close'])}
                    except Exception:
                        local_preds["cryptos"][c] = {"pred_1_step": None}
            except Exception:
                for c in cryptos:
                    local_preds["cryptos"][c] = {"pred_1_step": None}

            # metal simple fallback: use same price
            local_preds["metals"][metal_choice] = {"pred_1_step": metal_q.get("price")}

            # 4) build prompt for Gemini
            metadata = {"timestamp_utc": datetime.datetime.utcnow().isoformat(), "requestor": "streamlit_app_full_expert"}
            prompt_text = build_structured_prompt(news, prices, metadata)

            gemini_out = None
            if GEMINI_API_KEY:
                st.info("در حال ارسال prompt ساختاریافته به Gemini (جمینی 2.5 پرو)...")
                gemini_out = call_gemini_api(prompt_text, GEMINI_API_KEY, api_url=GEMINI_API_URL)
            else:
                st.warning("کلید Gemini وارد نشده — فقط پیش‌بینی محلی و نمایش داده‌ها انجام شد.")

        elapsed = time.time() - t0
        st.success(f"واکنش دریافت شد — پردازش {elapsed:.1f}s")

        # Display news
        st.subheader("اخبار (Investing.com RSS)")
        for n in news:
            st.markdown(f"**{n['title']}**  <small>({n.get('published','')})</small>")
            st.write(n.get('summary',''))
            st.markdown(f"[متن کامل]({n.get('link','')})")
            st.markdown("---")

        # Display prices table
        st.subheader("قیمت‌های لحظه‌ای")
        # stocks
        if prices["stocks"]:
            df_stocks = pd.DataFrame([{**{"symbol": k}, **v} for k, v in prices["stocks"].items()])
            st.table(df_stocks)
        if prices["cryptos"]:
            df_cryptos = pd.DataFrame([{**{"symbol": k}, **v} for k, v in prices["cryptos"].items()])
            st.table(df_cryptos)
        df_metals = pd.DataFrame([{**{"symbol": k}, **v} for k, v in prices["metals"].items()])
        st.table(df_metals)

        # Display local predictions
        st.subheader("پیش‌بینی‌های محلی (Fallback: LinearRegression ساده)")
        st.write(local_preds)

        # Display Gemini raw + parsed if any
        st.subheader("خروجی Gemini (خام)")
        if gemini_out:
            if "error" in gemini_out:
                st.error(f"خطا در فراخوانی Gemini: {gemini_out['error']}")
            else:
                st.json(gemini_out)
                # try to parse model textual output if present (depends on API response shape)
                # many Google responses put model text in response['candidates'][0]['output'] or response['output'][0]['content']
                try:
                    # heuristic parse
                    resp = gemini_out.get("response") or {}
                    # try common places
                    text_outputs = []
                    if isinstance(resp, dict):
                        # new style: resp.get('candidates')
                        for k in ("candidates","outputs","output"):
                            if k in resp:
                                arr = resp.get(k)
                                if isinstance(arr, list):
                                    for item in arr:
                                        if isinstance(item, dict):
                                            # find text-like fields
                                            for f in ("content","output","text"):
                                                if f in item:
                                                    text_outputs.append(item[f])
                                                # sometimes candidate has 'content' as list of dicts
                                                if isinstance(item.get(f), list):
                                                    for sub in item[f]:
                                                        if isinstance(sub, dict) and 'text' in sub:
                                                            text_outputs.append(sub['text'])
                    # fallback to top-level 'text' in gemini_out
                    if not text_outputs and "text" in gemini_out:
                        text_outputs.append(gemini_out["text"])

                    if text_outputs:
                        st.subheader("متن تولیدشده توسط مدل (heuristic extraction)")
                        for i, t in enumerate(text_outputs[:2]):
                            st.code(t)
                    else:
                        st.info("متن تولیدشده مدل در پاسخ یافت نشد یا باید ساختار endpoint بروز شود.")
                except Exception as e:
                    st.warning(f"خطا در پارس کردن خروجی Gemini: {e}")
        else:
            st.info("خروجی Gemini وجود ندارد — کلید را در سایدبار وارد کن تا فعال شود.")

with col2:
    st.header("خلاصه، پیشنهادها و هشدارها")
    st.write("نکات مهم:")
    st.markdown("""
    - این اپ برای **استفاده تحلیلی آزمایشی** مناسب است؛ **تصمیم‌گیری سرمایه‌گذاری بر پایه‌ی خروجی این اپ توصیه نمی‌شود**.  
    - ما برای فلزات از **تیکرهای Futures در yfinance** استفاده کرده‌ایم (بدون نیاز به API پولی).  
    - Gemini نیاز به **API Key معتبر** دارد. اگر کلید را وارد کنید، prompt ساختاریافته برای Gemini ارسال می‌شود و مدل یک JSON تحلیلی برمی‌گرداند (در حالت ایده‌آل).  
    - برای تولید سیگنال واقعی (خرید / فروش) باید قوانین ریسک و backtest کامل اضافه شود.
    """)

    st.subheader("مثال JSON-prompt (پیش‌نمایش)")
    st.code(build_structured_prompt(parse_rss(INVESTING_RSS, max_items=3), {
        "stocks": {"AAPL": {"price": 150}},
        "cryptos": {"BTC/USDT": {"price": 56000}},
        "metals": {"Gold (XAU) — GC=F": {"price": 2000}}
    }, {"timestamp_utc": datetime.datetime.utcnow().isoformat()} )[:1500] + "...\n(تکمیل در زمان اجرا)")

st.markdown("---")
st.markdown("**راهنما و توسعه بیشتر (پیشنهادات):**")
st.markdown("""
- اگر بخوایم پروفشنال‌تر بشه:  
  1. ذخیره تاریخچه بلندمدت قیمت‌ها (DB یا فایل) و استفاده از مدل‌های زمان-سری (Prophet / ARIMA / LSTM).  
  2. استفاده از سیستم صف/جریان برای جلوگیری از ریت‌لیمیت و مدیریت retries/backoff.  
  3. اضافه کردن تایم‌فریم‌های مختلف و نمودارهای پیشرفته (matplotlib یا plotly).  
  4. تست و تطبیق دقیقِ payload و endpoint با مستندات رسمی Gemini (Google) در صورت خطا در فراخوانی.
""")

st.caption("نسخه Full expert — هیچ API پولی جداگانه‌ای برای فلزات یا اخبار استفاده نشده. Gemini: در صورت ارائه کلید، تحلیل توسط مدل شما (جمینی) انجام می‌شود.")
