#!/usr/bin/env python3
"""Fetch Tamil-language headlines from Google News RSS and publish news.json."""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus

FEED_CONFIGS = [
    ("இலங்கை", "இலங்கை", "LK", "ta", "LK:ta"),
    ("தமிழகம்", "தமிழ்நாடு OR தமிழகம்", "IN", "ta", "IN:ta"),
    ("உலகம்", "உலக செய்திகள்", "LK", "ta", "LK:ta"),
    ("விளையாட்டு", "விளையாட்டு செய்திகள்", "LK", "ta", "LK:ta"),
    ("சினிமா", "தமிழ் சினிமா", "IN", "ta", "IN:ta"),
]

FEEDS = [
    (
        category,
        f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}",
    )
    for category, query, gl, hl, ceid in FEED_CONFIGS
]

NS = {"media": "http://search.yahoo.com/mrss/"}


def clean(s):
    s = unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def fetch(category, url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 AI-Tamil-News/1.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        root = ET.fromstring(response.read())
    rows = []
    for item in root.findall("./channel/item"):
        title = clean(item.findtext("title"))
        link = clean(item.findtext("link"))
        desc = clean(item.findtext("description"))
        source_node = item.find("source")
        source = clean(source_node.text if source_node is not None else "Google News")
        pub = clean(item.findtext("pubDate"))
        try:
            published = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
        except Exception:
            published = datetime.now(timezone.utc).isoformat()
        image = ""
        thumb = item.find("media:thumbnail", NS)
        if thumb is not None:
            image = thumb.attrib.get("url", "")
        if title and link:
            rows.append(
                {
                    "category": category,
                    "title": title,
                    "description": desc[:500],
                    "url": link,
                    "source": source,
                    "publishedAt": published,
                    "image": image,
                }
            )
    return rows


all_rows, seen = [], set()
for category, url in FEEDS:
    try:
        for row in fetch(category, url):
            key = row["url"]
            if key not in seen:
                seen.add(key)
                all_rows.append(row)
    except Exception as exc:
        print(f"Feed error ({category}): {exc}")

all_rows.sort(key=lambda x: x["publishedAt"], reverse=True)
if not all_rows:
    raise SystemExit("No RSS items fetched; refusing to overwrite the existing news.json")

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(all_rows[:80], f, ensure_ascii=False, indent=2)

print(f"Wrote {min(len(all_rows), 80)} articles to news.json")
