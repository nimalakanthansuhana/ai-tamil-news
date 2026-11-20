import json
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("இலங்கை", "https://news.google.com/rss/search?q=Sri+Lanka+Tamil+news&hl=ta&gl=LK&ceid=LK:ta"),
    ("தமிழகம்", "https://news.google.com/rss/search?q=Tamil+Nadu+news&hl=ta&gl=IN&ceid=IN:ta"),
    ("உலகம்", "https://news.google.com/rss/search?q=World+Tamil+news&hl=ta&gl=IN&ceid=IN:ta"),
    ("விளையாட்டு", "https://news.google.com/rss/search?q=Cricket+Sports+Tamil&hl=ta&gl=IN&ceid=IN:ta"),
    ("சினிமா", "https://news.google.com/rss/search?q=Tamil+Cinema+news&hl=ta&gl=IN&ceid=IN:ta"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def fetch_url(url, timeout=12):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore"), resp.geturl()

def clean_html_text(raw):
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_article_details(link, fallback_desc):
    image = ""
    full_text = ""
    try:
        page_html, final_url = fetch_url(link, timeout=10)
        m_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', page_html, re.I)
        if not m_img:
            m_img = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', page_html, re.I)
        if m_img:
            image = urllib.parse.urljoin(final_url, html.unescape(m_img.group(1).strip()))

        paragraphs = re.findall(r"<p[^>]*>([\s\S]*?)</p>", page_html, re.I)
        cleaned_paras = []
        for p in paragraphs:
            txt = clean_html_text(p)
            if len(txt) > 55 and not any(bad in txt.lower() for bad in ["cookie", "copyright", "subscribe", "all rights reserved", "advertisement"]):
                cleaned_paras.append(txt)
            if len(cleaned_paras) >= 8:
                break
        if cleaned_paras:
            full_text = "\n\n".join(cleaned_paras)
    except Exception:
        pass

    if not full_text:
        full_text = clean_html_text(fallback_desc)
    return image, full_text

def main():
    all_articles = []
    seen_titles = set()

    for category, feed_url in FEEDS:
        try:
            xml_data, _ = fetch_url(feed_url, timeout=15)
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")[:16]
            for item in items:
                raw_title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                desc = (item.findtext("description") or "").strip()
                source_el = item.find("source")
                source = (source_el.text if source_el is not None else "Tamil News").strip()

                title = re.sub(r"\s*[-–—|]\s*[^-–—|]+$", "", raw_title).strip() or raw_title
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                image, content = extract_article_details(link, desc)
                summary = content[:220].rsplit(" ", 1)[0] + "..." if len(content) > 220 else content

                all_articles.append({
                    "category": category,
                    "title": title,
                    "description": summary,
                    "content": content,
                    "image": image,
                    "source": source,
                    "publishedAt": pub_date,
                    "url": link
                })
        except Exception as e:
            print(f"Error fetching {category}: {e}")

    if all_articles:
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(all_articles)} full articles with images.")

if __name__ == "__main__":
    main()
