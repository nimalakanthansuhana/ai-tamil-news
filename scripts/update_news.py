
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from datetime import datetime, timezone

CATEGORIES = {
    "இலங்கை": "https://news.google.com/rss/search?q=Sri+Lanka+Tamil+News&hl=ta&gl=LK&ceid=LK:ta",
    "தமிழகம்": "https://news.google.com/rss/search?q=Tamil+Nadu+News&hl=ta&gl=IN&ceid=IN:ta",
    "உலகம்": "https://news.google.com/rss/search?q=World+Tamil+News&hl=ta&gl=IN&ceid=IN:ta",
    "விளையாட்டு": "https://news.google.com/rss/search?q=Sports+Cricket+Tamil&hl=ta&gl=IN&ceid=IN:ta",
    "சினிமா": "https://news.google.com/rss/search?q=Tamil+Cinema+News&hl=ta&gl=IN&ceid=IN:ta",
}

def clean_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", unescape(value)).strip()

def update_news():
    try:
        with open("pending-news.json", "r", encoding="utf-8") as f:
            pending = json.load(f)
        if not isinstance(pending, list):
            pending = []
    except (FileNotFoundError, json.JSONDecodeError):
        pending = []

    seen = {item.get("title") for item in pending}
    added = 0

    for category, rss_url in CATEGORIES.items():
        try:
            request = urllib.request.Request(
                rss_url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                root = ET.fromstring(response.read())

            for item in root.findall(".//item")[:15]:
                title = clean_html(item.findtext("title", ""))
                link = item.findtext("link", "").strip()
                description = clean_html(item.findtext("description", ""))
                source = clean_html(item.findtext("source", "Google News"))
                pub_date = item.findtext("pubDate", "")

                if not title or not link or title in seen:
                    continue

                pending.append({
                    "id": "pending-" + str(len(pending) + 1),
                    "title": title,
                    "description": description,
                    "category": category,
                    "source": source,
                    "date": pub_date,
                    "url": link,
                    "status": "pending",
                    "collected_at": datetime.now(timezone.utc).isoformat()
                })
                seen.add(title)
                added += 1

        except Exception as error:
            print(f"Error in {category}: {error}")

    with open("pending-news.json", "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    print(f"Added {added} stories for admin review.")

if __name__ == "__main__":
    update_news()
