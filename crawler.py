import requests, re, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import urllib.robotparser
import concurrent.futures
from db import db, urls_collection, pages_collection
from settings import MY_USER_AGENT, RECRAWL_DELAY_DAYS, MAX_RETRIES
from indexer import add_doc_to_whoosh

rp = urllib.robotparser.RobotFileParser()

def can_crawl(url):
    parsed_url = urlparse(url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = f"{domain}/robots.txt"
    try:
        if rp.url != robots_url:
            rp.set_url(robots_url)
            rp.read()
        return rp.can_fetch(MY_USER_AGENT, url)
    except:
        return True

def normalize_url(base_url, link_url):
    if not link_url or link_url.startswith("#"):
        return None
    absolute_url = urljoin(base_url, link_url)
    parsed = urlparse(absolute_url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path

def get_next_url():
    return urls_collection.find_one_and_update(
        {
            "status": "pending",
            "$or": [
                {"last_crawled": {"$exists": False}},
                {"last_crawled": {"$lt": datetime.now() - timedelta(days=RECRAWL_DELAY_DAYS)}}
            ]
        },
        {"$set": {"status": "in_progress", "started_at": datetime.now()}},
        sort=[("discovered_at", 1)]
    )

def process_url(url_doc, ix):
    url = url_doc["url"]
    print(f"🔎 Processing: {url}")

    if not can_crawl(url):
        print(f"🚫 Robots.txt interdit: {url}")
        urls_collection.update_one({"_id": url_doc["_id"]}, {"$set": {"status": "done"}})
        return

    try:
        headers = {"User-Agent": MY_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=5)
        if "text/html" not in response.headers.get("Content-Type", ""):
            urls_collection.update_one({"_id": url_doc["_id"]}, {"$set": {"status": "done"}})
            return

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "Sans titre"
        content = re.sub(r'\s+', ' ', soup.get_text()).strip()
        snippet = content[:200] + "..." if len(content) > 200 else content

        doc = {
            "url": url,
            "title": title,
            "content": content,
            "snippet": snippet,
            "crawled_date": datetime.now()
        }

        pages_collection.update_one({"url": url}, {"$set": doc}, upsert=True)
        add_doc_to_whoosh(ix, doc)

        for link in soup.find_all("a", href=True):
            absolute_link = normalize_url(url, link["href"])
            if absolute_link:
                urls_collection.update_one({"url": absolute_link}, {"$setOnInsert": {
                    "url": absolute_link,
                    "status": "pending",
                    "discovered_at": datetime.now(),
                    "retries": 0
                }}, upsert=True)

        urls_collection.update_one({"_id": url_doc["_id"]}, {"$set": {"status": "done", "last_crawled": datetime.now()}})
        print(f"✅ Page stockée: {title[:40]}")

    except Exception as e:
        print(f"💥 Erreur pour {url}: {e}")
        urls_collection.update_one(
            {"_id": url_doc["_id"]},
            {"$set": {"status": "error", "last_crawled": datetime.now()}, "$inc": {"retries": 1}}
        )

def crawl_multithreaded(start_url, ix, max_threads=5, max_pages=100):
    urls_collection.update_one(
        {"url": start_url},
        {"$setOnInsert": {"url": start_url, "status": "pending", "discovered_at": datetime.now(), "retries": 0}},
        upsert=True
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        count = 0
        futures = []
        while count < max_pages:
            url_doc = get_next_url()
            if not url_doc:
                print("⚠️ Plus d’URL en attente.")
                break
            futures.append(executor.submit(process_url, url_doc, ix))
            count += 1
        concurrent.futures.wait(futures)
    print(f"=== Crawl terminé: {count} pages ===")