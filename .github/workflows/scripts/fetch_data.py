import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import os

PYTZ_AVAILABLE = False
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    pass

def get_bangkok_time():
    now = datetime.utcnow()
    bangkok_offset = timedelta(hours=7)
    return now + bangkok_offset

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

    return get_fallback_rate()

def get_fallback_rate():
    today = get_bangkok_time()
    return {
        "date": today.strftime("%Y-%m-%d"),
        "buying": 0,
        "selling": 0,
        "mid": 0,
        "source": "Unavailable - Please check BOT website",
        "note": "Visit https://www.bot.or.th for current rates"
    }

def fetch_fx_news():
    news_items = []
    feeds = [
        {
            "url": "https://feeds.reuters.com/reuters/businessNews",
            "source": "Reuters Business"
        },
        {
            "url": "https://www.bangkokpost.com/rss/data/business.xml",
            "source": "Bangkok Post Business"
        }
    ]

    keywords = ["USD", "THB", "baht", "dollar", "Fed", "BOT",
                "interest rate", "forex", "FX", "currency", "exchange"]

    for feed in feeds:
        try:
            req = urllib.request.Request(
                feed["url"],
                headers={"User-Agent": "Mozilla/5.0 FX-Monitor/1.0"}
            )
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
                            "date": pub_date,
                            "link": link,
                            "source": feed["source"]
                        })
        except Exception as e:
            print(f"RSS error {feed['source']}: {e}")

    if not news_items:
        news_items = [
            {
                "title": "ไม่สามารถดึงข่าวอัตโนมัติได้",
                "description": "กรุณาตรวจสอบข่าว FX จาก Reuters, Bloomberg หรือ Bangkok Post โดยตรง",
                "date": get_bangkok_time().strftime("%Y-%m-%d %H:%M"),
                "link": "https://www.reuters.com/markets/currencies/",
                "source": "Manual"
            }
        ]

    return news_items[:10]

def build_claude_prompt(rate_data, news_items, budget_rate=34.50):
    today = get_bangkok_time()
    mid = rate_data.get("mid", 0)
    vs_budget = mid - budget_rate if mid > 0 else 0
    vs_budget_str = f"+{vs_budget:.2f}" if vs_budget >= 0 else f"{vs_budget:.2f}"
    budget_status = "เกิน Budget ⚠️" if vs_budget > 0 else "ต่ำกว่า Budget ✅"

    news_text = "\n".join([
        f"- [{item['source']}] {item['title']}"
        for item in news_items[:8]
    ])

    prompt = f"""คุณคือ CFO FX Advisor สำหรับบริษัท IT Distribution ในประเทศไทย (รายได้ 50,000 ล้านบาท)

═══════════════════════════════════
ข้อมูล USD/THB วันที่ {today.strftime("%d/%m/%Y %H:%M")} น.
═══════════════════════════════════
• อัตราซื้อ (Buying):  {rate_data.get('buying', 'N/A')} THB/USD
• อัตราขาย (Selling): {rate_data.get('selling', 'N/A')} THB/USD  
• อัตรากลาง (Mid):    {rate_data.get('mid', 'N/A')} THB/USD
• แหล่งข้อมูล: {rate_data.get('source', 'N/A')}

Budget Rate: {budget_rate} THB/USD
vs Budget: {vs_budget_str} THB ({budget_status})

═══════════════════════════════════
ข่าว FX ล่าสุด
═══════════════════════════════════
{news_text}

═══════════════════════════════════
ข้อมูลบริษัท (ใส่ข้อมูลจริงก่อนวิเคราะห์)
═══════════════════════════════════
• USD Payable/เดือน: USD [X]M (ค่าสินค้านำเข้าจาก Principal)
• USD Receivable/เดือน: USD [Y]M (ถ้ามี)
• Forward ที่ทำไว้แล้ว: [X]% ของ exposure
• Forward ที่ยังไม่ได้ทำ: USD [Z]M

═══════════════════════════════════
กรุณาวิเคราะห์และตอบในรูปแบบนี้:
═══════════════════════════════════

🎯 MARKET BIAS
• ทิศทาง USD วันนี้: [STRONG/NEUTRAL/WEAK]
• ความมั่นใจ: [HIGH/MEDIUM/LOW]
• เหตุผลหลัก 3 ข้อ:

📊 SENSITIVITY ANALYSIS
• ถ้า USD แข็งค่า +0.50 THB → ผลกระทบ: THB [X]M
• ถ้า USD อ่อนค่า -0.50 THB → โอกาส: THB [X]M
• Break-even rate สำหรับ Forward: [X] THB/USD

⚡ FORWARD CONTRACT RECOMMENDATION
• ควรทำ Forward วันนี้: [YES/WAIT/PARTIAL]
• จำนวนที่แนะนำ: USD [X]M
• Tenor ที่เหมาะสม: [1M/2M/3M]
• เหตุผล: [2 บรรทัด]
• ความเสี่ยงถ้าไม่ทำ: THB [X]M

✅ CFO ACTION TODAY
1. [Action แรก]
2. [Action สอง]
3. [Action สาม]

⚠️ Key Risks to Monitor:
• [Risk 1]
• [Risk 2]"""

    return prompt

def save_data(rate_data, news_items, prompt):
    today = get_bangkok_time()
    output = {
        "last_updated": today.strftime("%Y-%m-%d %H:%M:%S BKK"),
        "rate": rate_data,
        "news": news_items,
        "claude_prompt": prompt,
        "stats": {
            "news_count": len(news_items),
            "data_sources": list(set([n["source"] for n in news_items]))
        }
    }

    os.makedirs("data", exist_ok=True)
    with open("data/fx_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ Data saved: {today.strftime('%Y-%m-%d %H:%M')} BKK")
    print(f"   Rate: {rate_data.get('mid', 'N/A')} THB/USD ({rate_data.get('source')})")
    print(f"   News: {len(news_items)} articles")

if __name__ == "__main__":
    print("🔄 Fetching FX data...")
    rate_data = fetch_bot_rate()
    print("🔄 Fetching news...")
    news_items = fetch_fx_news()
    print("🔄 Building prompt...")
    prompt = build_claude_prompt(rate_data, news_items)
    save_data(rate_data, news_items, prompt)
    print("✅ Done!")
