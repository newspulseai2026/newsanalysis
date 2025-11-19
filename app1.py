import requests
from bs4 import BeautifulSoup
import json
import datetime

def fetch_news():
    url = "https://www.investing.com/news/cryptocurrency-news"
    headers = { "User-Agent": "Mozilla/5.0" }
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    # مثال استخراج تیترها
    articles = soup.select("article a.title")  # فرضی
    news_list = []
    for a in articles[:5]:
        title = a.get_text(strip=True)
        link = a["href"]
        news_list.append({"title": title, "link": link})
    return news_list

def fetch_price(symbol):
    # مثال استفاده از یک API آزاد (باید پیدا کنید یکی مناسب)
    api_url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    r = requests.get(api_url)
    data = r.json()
    return data[symbol]["usd"]

def analyse_news_with_model(news_list):
    # اینجا می‌تونید فراخوانی مدل Gemini یا هر مدل دیگری بزنید
    # مثلاً برای هر تیتر بگید احساس خبر مثبت است یا منفی
    results = []
    for news in news_list:
        # فرضی: مدل را صدا می‌زنیم و نتیجه "پیش‌بینی تغییر قیمت" می‌گیریم
        sentiment = "positive"  # مثال
        predicted_move = "up"   # مثال
        predicted_pct = 5.0     # مثال
        results.append({ **news, "sentiment": sentiment,
                         "predicted_move": predicted_move,
                         "predicted_pct": predicted_pct })
    return results

def main():
    news = fetch_news()
    symbol = "bitcoin"  # یا ethereum، etc
    price_before = fetch_price(symbol)
    analyses = analyse_news_with_model(news)
    price_after = fetch_price(symbol)
    change_pct = (price_after - price_before) / price_before * 100
    print("Current price:", price_before)
    print("After price:", price_after)
    print(f"Actual change: {change_pct:.2f}%")
    print("News & analyses:", json.dumps(analyses, indent=2))

if __name__ == "__main__":
    main()
