import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

def get_bangkok_time():
    now = datetime.utcnow()
    return now + timedelta(hours=7)

def fetch_bot_rate():
    try:
        today = get_bangkok_time()
        date_str = today.strftime("%Y-%m-%d")
        url = f"https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period={date_str}&end_period={date_str}&currency=USD"
        req = urllib.request.Request(url, headers={
            "X-IBM-Client-Id": "bot-api-public",
            "accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            rates = data.get("result", {}).get("data", {}).get("data_detail", [])
            if rates:
                rate = rates[0]
                return {
                    "date": date_str,
                    "buying": float(rate.get("buying_sight", 0)),
                    "selling": float(rate.get("selling", 0)),
                    "mid": float(rate.get("mid", 0)),
                    "source": "BOT Official"
                }
    except Exception as e:
        print(f"BOT API error: {e}")
    return {
        "date": get_bangkok_time().strftime("%Y-%m-%d"),
        "buying": 0, "selling": 0, "mid": 0,
        "source": "Unavailable - Please check BOT website"
    }

def fetch_fx_news():
    news_items = []
    feeds = [
        {"url": "https://feeds.reuters.com/reuters/businessNews", "source": "Reuters Business"},
        {"url": "https://www.bangkokpost.com/rss/data/business.xml", "source": "Bangkok Post Business"}
    ]
    keywords = ["USD", "THB", "baht", "dollar", "Fed", "BOT",
                "interest rate", "forex", "FX", "currency", "exchange"]
    for feed in feeds:
        try:
            req = urllib.request.Request(feed["url"],
                headers={"User-Agent": "Mozilla/5.0 FX-Monitor/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="ignore")
                root = ET.fromstring(content)
                channel = root.find("channel")
                if channel is None:
                    continue
                for item in channel.findall("item")[:20]:
                    title = item.findtext("title", "")
                    desc = item.findtext("description", "")
                    pub_date = item.findtext("pubDate", "")
                    link = item.findtext("link", "")
                    combined = (title + " " + desc).lower()
                    if any(kw.lower() in combined for kw in keywords):
                        news_items.append({
                            "title": title.strip(),
                            "description": desc[:200].strip() if desc else "",
                            "date": pub_date, "link": link,
                            "source": feed["source"]
                        })
        except Exception as e:
            print(f"RSS error {feed['source']}: {e}")
    if not news_items:
        news_items = [{"title": "ไม่สามารถดึงข่าวอัตโนมัติได้",
            "description": "กรุณาตรวจสอบข่าว FX จาก Reuters หรือ Bangkok Post",
            "date": get_bangkok_time().strftime("%Y-%m-%d %H:%M"),
            "link": "https://www.reuters.com/markets/currencies/",
            "source": "Manual"}]
    return news_items[:10]

def fetch_synnex_news():
    all_news = []
    # ===== TRUSTED SOURCES (priority, direct links) =====
    trusted_feeds = [
        # Settrade research via FeedBurner (เสถียร ไม่ block bot) - บทวิเคราะห์หุ้นรายตัว
        {"url": "https://feeds2.feedburner.com/settrade/researchStock?format=xml",
         "source": "Settrade Research", "category": "stock", "trusted": True, "priority": 1},
        # Settrade market analysis
        {"url": "https://feeds2.feedburner.com/settrade/researchMarket?format=xml",
         "source": "Settrade Market", "category": "stock", "trusted": True, "priority": 2},
        # Bangkok Post business (พิสูจน์แล้วว่าดึงได้บน GitHub Actions)
        {"url": "https://www.bangkokpost.com/rss/data/business.xml",
         "source": "Bangkok Post", "category": "general", "trusted": True, "priority": 3},
    ]
    # ===== GOOGLE NEWS (aggregator, search-redirect links) =====
    google_feeds = [
        {"url": "https://news.google.com/rss/search?q=%22Synnex%22+Thailand+SYNEX&hl=th&gl=TH&ceid=TH:th",
         "source": "Google News TH", "category": "general", "trusted": False, "priority": 5},
        {"url": "https://news.google.com/rss/search?q=%22Synnex+Thailand%22+IT+distribution&hl=en&gl=TH&ceid=TH:en",
         "source": "Google News EN", "category": "general", "trusted": False, "priority": 6},
    ]
    feeds = trusted_feeds + google_feeds
    synnex_keywords = ["synnex", "ซินเน็ค", "synex", "Synnex Public",
                       "สยามซินเน็ค"]
    for feed in feeds:
        try:
            req = urllib.request.Request(feed["url"],
                headers={"User-Agent": "Mozilla/5.0 NewsBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode("utf-8", errors="ignore")
                root = ET.fromstring(content)
                channel = root.find("channel")
                if channel is None:
                    continue
                for item in channel.findall("item")[:15]:
                    title = item.findtext("title", "")
                    desc = item.findtext("description", "")
                    pub_date = item.findtext("pubDate", "")
                    link = item.findtext("link", "")
                    combined = (title + " " + desc).lower()
                    # Google News = already searched for Synnex, always relevant
                    is_google = feed["source"].startswith("Google News")
                    # Settrade FeedBurner = all stocks, must filter for SYNEX keyword
                    is_relevant = any(kw.lower() in combined for kw in synnex_keywords)
                    if title and (is_google or is_relevant):
                        all_news.append({
                            "title": title.strip(),
                            "description": desc[:300].strip() if desc else "",
                            "date": pub_date, "link": link,
                            "source": feed["source"],
                            "category": feed["category"],
                            "trusted": feed["trusted"],
                            "priority": feed["priority"]
                        })
        except Exception as e:
            print(f"Synnex feed error {feed['source']}: {e}")
    # dedupe by title
    seen = set()
    unique = []
    for n in all_news:
        key = n["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(n)
    # sort: trusted first (by priority), then google
    unique.sort(key=lambda n: n["priority"])
    if not unique:
        unique = [
            {"title": "Synnex Public Company (Thailand) — ยังไม่มีข่าวใหม่วันนี้",
             "description": "ตรวจสอบข่าวล่าสุดได้ที่ SET หรือ ir.synnex.co.th",
             "date": get_bangkok_time().strftime("%Y-%m-%d %H:%M"),
             "link": "https://www.set.or.th/th/market/product/stock/quote/SYNEX/price",
             "source": "SET Official", "category": "stock", "trusted": True, "priority": 1},
        ]
    return unique[:25]

def build_claude_prompt(rate_data, news_items, budget_rate=34.50):
    today = get_bangkok_time()
    mid = rate_data.get("mid", 0)
    vs_budget = mid - budget_rate if mid > 0 else 0
    vs_budget_str = f"+{vs_budget:.2f}" if vs_budget >= 0 else f"{vs_budget:.2f}"
    news_text = "\n".join([f"- [{i['source']}] {i['title']}" for i in news_items[:8]])
    return f"CFO FX Brief {today.strftime('%d/%m/%Y')} | Rate: {rate_data.get('mid','N/A')} | vs Budget: {vs_budget_str}\n\nNews:\n{news_text}"

def save_data(rate_data, fx_news, synnex_news, prompt):
    today = get_bangkok_time()
    output = {
        "last_updated": today.strftime("%Y-%m-%d %H:%M:%S BKK"),
        "rate": rate_data,
        "news": fx_news,
        "synnex_news": synnex_news,
        "claude_prompt": prompt,
        "stats": {
            "fx_news_count": len(fx_news),
            "synnex_news_count": len(synnex_news),
            "data_sources": list(set([n["source"] for n in fx_news + synnex_news]))
        }
    }
    os.makedirs("data", exist_ok=True)
    with open("data/fx_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved: {today.strftime('%Y-%m-%d %H:%M')} BKK")
    print(f"   FX Rate: {rate_data.get('mid', 'N/A')} THB/USD")
    print(f"   FX News: {len(fx_news)} articles")
    print(f"   Synnex News: {len(synnex_news)} articles")

if __name__ == "__main__":
    print("🔄 Fetching FX rate...")
    rate_data = fetch_bot_rate()
    print("🔄 Fetching FX news...")
    fx_news = fetch_fx_news()
    print("🔄 Fetching Synnex news...")
    synnex_news = fetch_synnex_news()
    print("🔄 Building prompt...")
    prompt = build_claude_prompt(rate_data, fx_news)
    save_data(rate_data, fx_news, synnex_news, prompt)
    print("✅ Done!")
