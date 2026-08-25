import sys
import requests
from bs4 import BeautifulSoup
import yaml
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
import asyncio
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def clean_facebook_url(url: str) -> str:
    """Removes tracking and session parameters (__cft__, __tn__) from Facebook URLs."""
    parsed = urlparse(url)
    if "facebook.com" not in parsed.netloc:
        return url
    
    # Parse query parameters
    q_params = dict(parse_qsl(parsed.query))
    
    # Keep only essential ID parameters
    essential_keys = ["story_fbid", "id", "fbid", "comment_id", "reply_comment_id"]
    clean_params = {k: v for k, v in q_params.items() if k in essential_keys}
    
    new_query = urlencode(clean_params)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

def load_sources(path="sources.yaml") -> list[dict]:
    """Loads and returns sources from sources.yaml file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]

def fetch_static_source(source: dict) -> list[dict]:
    """
    Crawls static web pages using standard requests + BeautifulSoup.
    Optimized for WordPress and simple HTML layouts.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    url = source["url"]
    selector = source["selector"]
    source_name = source["name"]
    source_type = source.get("type", "school")
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    
    for el in soup.select(selector):
        title = el.get_text(strip=True)
        link = el.get("href", "").strip()
        
        if link and not link.startswith("http"):
            link = urljoin(url, link)
            
        if title and link:
            # Clean titles from "Read more", "Xem thêm" or double spaces
            title = title.replace("Xem thêm", "").strip()
            # Exclude menu category pages or simple tags if they get caught
            if len(title) < 10 or "category/" in link:
                continue
                
            items.append({
                "title": title,
                "link": link,
                "source_name": source_name,
                "type": source_type
            })
            
    return items

async def fetch_facebook_source(source: dict, page) -> list[dict]:
    """
    Crawls a public Facebook page using Playwright without logging in.
    Extracts article containers, post text, and post URLs.
    """
    url = source["url"]
    source_name = source["name"]
    source_type = source.get("type", "facebook")
    
    print(f"[{source_name}] Navigating to public Facebook page...")
    # Navigate to Facebook and wait for idle network
    await page.goto(url, wait_until="networkidle", timeout=20000)
    
    # Scroll down slightly to trigger loading additional posts if needed
    await page.evaluate("window.scrollTo(0, 500)")
    await page.wait_for_timeout(2000)
    
    html_content = await page.content()
    soup = BeautifulSoup(html_content, "html.parser")
    
    items = []
    # Facebook public page posts are identified by role="article"
    articles = soup.find_all('div', role='article')
    
    for art in articles:
        # 1. Extract post text
        # Facebook uses elements with dir="auto" for post content
        text_elements = art.find_all(dir='auto')
        texts = [el.get_text(strip=True) for el in text_elements if el.get_text(strip=True)]
        
        main_text = ""
        if texts:
            # Select the longest meaningful text block as the main content/title
            meaningful = [t for t in texts if len(t) > 10 and not t.startswith("Like") and not t.startswith("Share")]
            if meaningful:
                main_text = meaningful[0]
            else:
                main_text = texts[0]
        
        # 2. Extract post link
        post_links = []
        for a in art.find_all('a'):
            href = a.get('href', '')
            if href:
                full_href = urljoin("https://www.facebook.com/", href)
                # Match typical post formats (/posts/, /photos/, /videos/, permalink.php, story.php)
                if any(pattern in full_href for pattern in ["/posts/", "/photos/", "/videos/", "permalink.php", "story.php"]):
                    if "/posts/" in full_href or "story_fbid" in full_href or "/photos/" in full_href:
                        post_links.append(full_href)
                        
        if main_text and post_links:
            # Normalize and clean Facebook URL from tracking parameters
            clean_link = clean_facebook_url(post_links[0])
                
            # Create a shorter, punchy title for Telegram notifications
            telegram_title = main_text
            if len(main_text) > 150:
                telegram_title = main_text[:147] + "..."
                
            items.append({
                "title": telegram_title,
                "link": clean_link,
                "source_name": source_name,
                "type": source_type
            })
            
    return items

async def crawl_all_async(sources: list[dict]) -> list[dict]:
    """Asynchronously orchestrates the crawl of static and JS-rendered targets."""
    all_items = []
    
    # Split sources into static and facebook
    static_sources = [s for s in sources if s.get("type") != "facebook"]
    fb_sources = [s for s in sources if s.get("type") == "facebook"]
    
    # 1. Crawl static sources (fast & synchronous calls wrapped in loop)
    for src in static_sources:
        try:
            print(f"Crawl target: [{src['name']}] (Static requests)...")
            items = fetch_static_source(src)
            all_items.extend(items)
            print(f"[{src['name']}] Found {len(items)} items.")
        except Exception as e:
            print(f"[ERROR] Fail crawling static target '{src['name']}': {e}")
            
    # 2. Crawl Facebook sources (requires Playwright browser)
    if fb_sources:
        print("\nStarting Playwright for Facebook sources...")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Mimic standard Chrome browser on Windows
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                    locale="vi-VN"
                )
                page = await context.new_page()
                
                for src in fb_sources:
                    try:
                        print(f"Crawl target: [{src['name']}] (Playwright FB Scraper)...")
                        items = await fetch_facebook_source(src, page)
                        all_items.extend(items)
                        print(f"[{src['name']}] Found {len(items)} items.")
                        # Brief sleep between targets
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"[ERROR] Fail crawling Facebook target '{src['name']}': {e}")
                
                await browser.close()
        except Exception as e:
            print(f"[ERROR] Playwright initialization error: {e}")
            
    return all_items

def crawl_all(sources: list[dict]) -> list[dict]:
    """Helper entrypoint to execute the async event loop for crawling."""
    return asyncio.run(crawl_all_async(sources))
