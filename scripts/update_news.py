import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape

# செய்தி வகைகள் மற்றும் Google News Tamil RSS இணைப்புகள்
CATEGORIES = {
    "இலங்கை": "https://news.google.com/rss/search?q=Sri+Lanka+Tamil+News&hl=ta&gl=LK&ceid=LK:ta",
    "தமிழகம்": "https://news.google.com/rss/search?q=Tamil+Nadu+News&hl=ta&gl=IN&ceid=IN:ta",
    "உலகம்": "https://news.google.com/rss/search?q=World+Tamil+News&hl=ta&gl=IN&ceid=IN:ta",
    "விளையாட்டு": "https://news.google.com/rss/search?q=Sports+Cricket+Tamil&hl=ta&gl=IN&ceid=IN:ta",
    "சினிமா": "https://news.google.com/rss/search?q=Tamil+Cinema+News&hl=ta&gl=IN&ceid=IN:ta",
}

def clean_html(raw_html):
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def get_topic_image(title, desc, category):
    text = f"{title} {desc} {category}".lower()
    if any(k in text for k in ["இலங்கை", "sri lanka", "கொழும்பு", "யாழ்ப்பாணம்", "மட்டக்களப்பு"]):
        return "https://images.unsplash.com/photo-1588591795084-17770cb32374?auto=format&fit=crop&w=800&q=80"
    if any(k in text for k in ["கொள்ளை", "சிறை", "நீதிமன்றம்", "கைது", "போலீஸ்", "மரண"]):
        return "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=800&q=80"
    if any(k in text for k in ["விளையாட்டு", "கிரிக்கெட்", "cricket", "போட்டி"]):
        return "https://images.unsplash.com/photo-1531415074968-036ba1b575da?auto=format&fit=crop&w=800&q=80"
    if any(k in text for k in ["சினிமா", "படம்", "நடிகர்", "விஜய்", "திரைப்படம்"]):
        return "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80"
    if any(k in text for k in ["தங்கம்", "பொருளாதாரம்", "வங்கி", "விலை"]):
        return "https://images.unsplash.com/photo-1610375461246-83df859d849d?auto=format&fit=crop&w=800&q=80"
    return "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"

def expand_to_10_plus_lines(title, raw_desc, category, source):
    """
    RSS-ல் 2 வரி மட்டுமே வந்தாலும், வாசகர்களுக்கு முழுமையான செய்தி கிடைக்க
    குறைந்தது 10 வரிகளுக்கு மேல் விரிவான செய்தி வடிவத்தை உருவாக்கும்.
    """
    base_text = clean_html(raw_desc)
    if not base_text or base_text == title:
        base_text = f"{title} தொடர்பான முக்கியத் தகவல்கள் தற்போது வெளியாகியுள்ளன."

    paragraphs = [
        f"📌 முக்கியச் செய்தி ({category}): {title}.",
        f"இச்சம்பவம் தொடர்பாக {source} ஊடகத்தின் வழியாக வெளியாகியுள்ள தகவல்களின்படி, {base_text}.",
        "இது குறித்து சம்பந்தப்பட்ட அதிகாரிகள் மற்றும் துறை சார்ந்த நிபுணர்கள் தீவிர கவனம் செலுத்தி வருகின்றனர். பொதுமக்கள் மற்றும் வாசகர்கள் மத்தியில் இந்தச் செய்தி மிகுந்த எதிர்பார்ப்பையும் கவனத்தையும் பெற்றுள்ளது.",
        "தற்போதைய சூழலில், இதனுடன் தொடர்புடைய மேலதிக விவரங்கள் மற்றும் அதிகாரப்பூர்வ அறிவிப்புகள் தொடர்ந்து சேகரிக்கப்பட்டு வருகின்றன. குறிப்பாக, இதன் தாக்கம் மற்றும் அடுத்தகட்ட நடவடிக்கைகள் குறித்து முக்கிய ஆலோசனைகள் நடைபெற்று வருவதாகத் தெரிவிக்கப்பட்டுள்ளது.",
        "மேலும், பாதிக்கப்பட்ட அல்லது தொடர்புடைய தரப்பினரின் கருத்துக்களும் பதிவு செய்யப்பட்டு வருவதால், விரைவில் இது குறித்த முழுமையான அறிக்கை வெளியாகும் என எதிர்பார்க்கப்படுகிறது.",
        f"AI Tamil News வாசகர்களுக்காக {category} பிரிவின் கீழ் இந்தச் செய்தி உடனுக்குடன் தொகுத்து வழங்கப்பட்டுள்ளது. இதன் அடுத்தகட்ட மாற்றங்கள் மற்றும் புதிய தகவல்கள் வெளியானதும் எமது தளத்தில் உடனடியாகப் புதுப்பிக்கப்படும்."
    ]
    return "\n\n".join(paragraphs)

def fetch_full_article_text(url):
    """இணைப்பிலிருந்து பத்திகளை (paragraphs) எடுக்க முயற்சிக்கும்"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            paras = re.findall(r"<p[^>]*>(.*?)</p>", html, flags=re.S | re.I)
            cleaned = [clean_html(p) for p in paras if len(clean_html(p)) > 60]
            if len(cleaned) >= 4:
                return "\n\n".join(cleaned[:8])
    except Exception:
        pass
    return ""

def update_news():
    all_news = []
    seen_titles = set()

    for category, rss_url in CATEGORIES.items():
        try:
            req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:15]:
                title = clean_html(item.findtext("title", ""))
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                link = item.findtext("link", "#").strip()
                pub_date = item.findtext("pubDate", "")
                source = clean_html(item.findtext("source", "AI Tamil News"))
                desc = clean_html(item.findtext("description", ""))

                # முதலில் மூல இணையதளத்திலிருந்து முழுச் செய்தியை எடுக்க முயற்சிக்கும்
                full_text = fetch_full_article_text(link)
                if len(full_text) < 450:
                    # மூலத் தளம் தடுத்தால் (Google News redirect), 10+ வரிகள் கொண்ட விரிவான செய்தியாக மாற்றும்
                    full_text = expand_to_10_plus_lines(title, desc, category, source)

                image_url = get_topic_image(title, full_text, category)

                all_news.append({
                    "id": f"news-{len(all_news)+1}",
                    "title": title,
                    "description": full_text,
                    "category": category,
                    "source": source,
                    "date": datetime.now().strftime("%d %b, %Y"),
                    "image": image_url,
                    "url": link,
                    "likes": 15
                })
        except Exception as e:
            print(f"Error fetching {category}: {e}")

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update_news()
