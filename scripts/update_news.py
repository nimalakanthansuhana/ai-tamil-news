import os
import json
import re
import html
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

FEEDS = [
    ("இலங்கை", "https://news.google.com/rss/search?q=Sri+Lanka+Tamil+news&hl=ta&gl=LK&ceid=LK:ta"),
    ("தமிழகம்", "https://news.google.com/rss/search?q=Tamil+Nadu+news&hl=ta&gl=IN&ceid=IN:ta"),
    ("உலகம்", "https://news.google.com/rss/search?q=World+Tamil+news&hl=ta&gl=IN&ceid=IN:ta"),
    ("விளையாட்டு", "https://news.google.com/rss/search?q=Cricket+Sports+Tamil&hl=ta&gl=IN&ceid=IN:ta"),
    ("சினிமா", "https://news.google.com/rss/search?q=Tamil+Cinema+news&hl=ta&gl=IN&ceid=IN:ta"),
]

CAT_STYLE = {
    "இலங்கை": "tropical island news broadcast studio, Sri Lanka cultural modern editorial photography, clean lighting, no text",
    "தமிழகம்": "South Indian modern news editorial scene, temple gopuram and modern city skyline, cinematic lighting, no text",
    "உலகம்": "global news network map and international diplomacy press room, modern blue lighting, no text",
    "விளையாட்டு": "stadium sports action photography, dramatic floodlights, dynamic motion, no text",
    "சினிமா": "cinema film production set, movie camera lens and colorful stage lights, no text",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

IMG_DIR = "images"
MAX_NEW_AI_IMAGES_PER_RUN = 10

def fetch_bytes(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.geturl()

def fetch_text(url, timeout=15):
    data, final_url = fetch_bytes(url, timeout=timeout)
    return data.decode("utf-8", errors="ignore"), final_url

def clean_html_text(raw):
    text = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def is_valid_image_url(url):
    if not url:
        return False
    low = url.lower()
    if low.startswith("data:") or low.endswith(".svg") or "logo" in low or "icon" in low or "avatar" in low:
        return False
    return low.startswith("http://") or low.startswith("https://")

def download_image_to_local(img_url, rel_path):
    try:
        if img_url.startswith("http://"):
            img_url = "https://" + img_url[7:]
        data, _ = fetch_bytes(img_url, timeout=12)
        if len(data) < 4000:
            return False
        os.makedirs(os.path.dirname(rel_path), exist_ok=True)
        with open(rel_path, "wb") as f:
            f.write(data)
        return True
    except Exception:
        return False

def generate_ai_image(title, category, rel_path):
    style = CAT_STYLE.get(category, "modern news editorial photography, clean lighting, no text")
    safe_topic = re.sub(r"[^\w\s-]", " ", title or category)[:80].strip()
    prompt = f"{style}, topic: {safe_topic}, high resolution, realistic editorial visual, no watermark, no letters"
    encoded = urllib.parse.quote(prompt)
    ai_url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=450&nologo=true"
    return download_image_to_local(ai_url, rel_path)

def extract_article_and_image(link, fallback_desc, title, category, ai_generated_count):
    found_img = ""
    full_text = ""

    m_desc_img = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', fallback_desc or "", re.I)
    if m_desc_img and is_valid_image_url(m_desc_img.group(1)):
        found_img = html.unescape(m_desc_img.group(1).strip())

    try:
        page_html, final_url = fetch_text(link, timeout=10)
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        ]
        for pat in patterns:
            m = re.search(pat, page_html, re.I)
            if m:
                cand = urllib.parse.urljoin(final_url, html.unescape(m.group(1).strip()))
                if is_valid_image_url(cand):
                    found_img = cand
                    break

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

    slug = hashlib.md5((category + "|" + title).encode("utf-8")).hexdigest()[:12]
    rel_path = f"{IMG_DIR}/{slug}.jpg"

    if os.path.exists(rel_path) and os.path.getsize(rel_path) > 4000:
        return f"./{rel_path}", full_text, ai_generated_count

    if found_img and download_image_to_local(found_img, rel_path):
        return f"./{rel_path}", full_text, ai_generated_count

    if ai_generated_count < MAX_NEW_AI_IMAGES_PER_RUN and generate_ai_image(title, category, rel_path):
        return f"./{rel_path}", full_text, ai_generated_count + 1

    return "", full_text, ai_generated_count

def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    all_articles = []
    seen_titles = set()
    ai_generated_count = 0

    for category, feed_url in FEEDS:
        try:
            xml_data, _ = fetch_text(feed_url, timeout=15)
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")[:14]
            for item in items:
                raw_title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                desc = (item.findtext("description") or "").strip()
                source_el = item.find("source")
                source = (source_el.text if source_el is not None else "AI Tamil News").strip()

                title = re.sub(r"\s*[-–—|]\s*[^-–—|]+$", "", raw_title).strip() or raw_title
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                local_img, content, ai_generated_count = extract_article_and_image(
                    link, desc, title, category, ai_generated_count
                )
                summary = content[:220].rsplit(" ", 1)[0] + "..." if len(content) > 220 else content

                all_articles.append({
                    "category": category,
                    "title": title,
                    "description": summary,
                    "content": content,
                    "image": local_img,
                    "source": source,
                    "publishedAt": pub_date,
                    "url": link
                })
        except Exception as e:
            print(f"Error fetching {category}: {e}")

    if all_articles:
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        with_img = sum(1 for a in all_articles if a.get("image"))
        print(f"Saved {len(all_articles)} articles ({with_img} with local/AI images, {ai_generated_count} new AI images).")

if __name__ == "__main__":
    main()
