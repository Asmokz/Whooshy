import asyncio
import random
import aiohttp
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import urllib.robotparser
from db import urls_collection, pages_collection
from settings import MY_USER_AGENT, RECRAWL_DELAY_DAYS, MAX_RETRIES

# Cache pour les parsers robots.txt et gestion du crawl-delay
robots_cache = {}
last_access = {}

# Limite de pages par domaine
MAX_PAGES_PER_DOMAIN = 1000
# Dictionnaire pour compter les pages crawlées par domaine
domain_page_count = {}

def get_robot_parser(domain):
    """Charge ou retourne le parser robots.txt pour un domaine."""
    robots_url = f"{domain}/robots.txt"
    if domain not in robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            robots_cache[domain] = rp
        except Exception as e:
            print(f"⚠️ Impossible de lire robots.txt pour {domain}: {e}")
            robots_cache[domain] = None
    return robots_cache[domain]

def can_crawl(url, user_agent=MY_USER_AGENT):
    """Vérifie si l'URL peut être crawlée selon robots.txt et retourne le crawl-delay."""
    parsed_url = urlparse(url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    rp = get_robot_parser(domain)
    if rp and not rp.can_fetch(user_agent, url):
        return False, None
    crawl_delay = None
    if rp and hasattr(rp, "crawl_delay"):
        try:
            crawl_delay = rp.crawl_delay(user_agent)
        except Exception:
            crawl_delay = None
    return True, crawl_delay

def load_seeds(filename="resources/seeds.txt"):
    """Charge les URLs de départ depuis un fichier."""
    with open(filename, "r") as f:
        seeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return seeds

def normalize_url(base_url, link_url):
    """Normalise une URL relative en URL absolue."""
    if not link_url or link_url.startswith("#"):
        return None
    absolute_url = urljoin(base_url, link_url)
    parsed = urlparse(absolute_url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path

def get_next_url():
    """Récupère la prochaine URL à crawler depuis MongoDB."""
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

async def fetch(session, url, headers=None):
    """Récupère le contenu d'une URL de manière asynchrone."""
    try:
        async with session.get(url, headers=headers or {"User-Agent": MY_USER_AGENT}, timeout=10) as response:
            if response.status == 200 and "text/html" in response.headers.get("Content-Type", ""):
                return await response.text()
            else:
                print(f"⚠️ Erreur HTTP {response.status} pour {url}")
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération de {url}: {e}")
    return None

async def process_url(session, url_doc):
    """Traite une URL : crawl, extrait les liens, et stocke dans MongoDB."""
    global domain_page_count
    url = url_doc["url"]
    parsed_url = urlparse(url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Initialise le compteur pour ce domaine si nécessaire
    if domain not in domain_page_count:
        domain_page_count[domain] = 0

    # Vérifie si on a atteint la limite pour ce domaine
    if domain_page_count[domain] >= MAX_PAGES_PER_DOMAIN:
        print(f"⏹️ Limite de {MAX_PAGES_PER_DOMAIN} pages atteinte pour {domain}. Ignoré.")
        urls_collection.update_one(
            {"_id": url_doc["_id"]},
            {"$set": {"status": "done", "last_crawled": datetime.now()}}
        )
        return

    print(f"🔎 Processing: {url}")

    # Vérification robots.txt et crawl-delay
    allowed, crawl_delay = can_crawl(url)
    if not allowed:
        print(f"🚫 Robots.txt interdit: {url}")
        urls_collection.update_one({"_id": url_doc["_id"]}, {"$set": {"status": "done"}})
        return

    # Respect du crawl-delay
    if crawl_delay:
        last_time = last_access.get(domain)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < crawl_delay:
                wait_time = crawl_delay - elapsed
                print(f"⏳ Respect crawl-delay ({crawl_delay}s) pour {domain}, attente {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

    # Délai aléatoire pour éviter le spam
    await asyncio.sleep(random.uniform(0.5, 1.2))

    # Récupération du contenu
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyBot/1.0; +http://example.com/bot)"}
    html = await fetch(session, url, headers=headers)
    last_access[domain] = datetime.now()

    if not html:
        urls_collection.update_one(
            {"_id": url_doc["_id"]},
            {"$set": {"status": "error", "last_crawled": datetime.now()}, "$inc": {"retries": 1}}
        )
        return

    # Parsing du HTML
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "Sans titre"
    content = re.sub(r'\s+', ' ', soup.get_text()).strip()
    snippet = content[:200] + "..." if len(content) > 200 else content

    # Stocke la page dans MongoDB
    doc = {
        "url": url,
        "title": title,
        "content": content,
        "snippet": snippet,
        "crawled_date": datetime.now(),
        "status": "index_pending"
    }
    pages_collection.update_one({"url": url}, {"$set": doc}, upsert=True)

    # Incrémente le compteur de pages pour ce domaine
    domain_page_count[domain] += 1
    print(f"📊 Pages crawées pour {domain}: {domain_page_count[domain]}/{MAX_PAGES_PER_DOMAIN}")

    # Découverte de nouveaux liens
    for link in soup.find_all("a", href=True):
        absolute_link = normalize_url(url, link["href"])
        if absolute_link:
            urls_collection.update_one(
                {"url": absolute_link},
                {"$setOnInsert": {
                    "url": absolute_link,
                    "status": "pending",
                    "discovered_at": datetime.now(),
                    "retries": 0
                }},
                upsert=True
            )

    # Mise à jour du statut de l'URL
    urls_collection.update_one(
        {"_id": url_doc["_id"]},
        {"$set": {"status": "done", "last_crawled": datetime.now()}}
    )
    print(f"✅ Page stockée: {title[:40]}")

async def crawl_async(seeds=None, max_pages=20000, max_concurrent_tasks=50, max_per_domain=2):
    """Lance le crawling asynchrone à partir d'une liste de seeds."""
    global domain_page_count
    domain_page_count = {}  # Réinitialise le compteur

    if seeds is None:
        seeds = load_seeds()

    # Nettoyage de la file d'attente
    urls_collection.delete_many({"status": {"$in": ["pending", "in_progress", "error"]}})
    print("🗑️ Cleared pending URLs from the database.")

    # Ajout des seeds
    now = datetime.now()
    for seed in seeds:
        urls_collection.update_one(
            {"url": seed},
            {
                "$set": {
                    "url": seed,
                    "status": "pending",
                    "discovered_at": now,
                    "retries": 0
                }
            },
            upsert=True
        )

    # Configuration de la session
    connector = aiohttp.TCPConnector(limit=max_concurrent_tasks, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        global_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        domain_semaphores = {}
        processed_pages = 0

        async def worker():
            nonlocal processed_pages
            while processed_pages < max_pages:
                async with global_semaphore:
                    url_doc = get_next_url()
                    if not url_doc:
                        print("⚠️ Plus d’URL en attente. Attente...")
                        await asyncio.sleep(5)
                        continue
                    parsed = urlparse(url_doc["url"])
                    domain = f"{parsed.scheme}://{parsed.netloc}"
                    if domain not in domain_semaphores:
                        domain_semaphores[domain] = asyncio.Semaphore(max_per_domain)
                    async with domain_semaphores[domain]:
                        await process_url(session, url_doc)
                        processed_pages += 1
                        print(f"📊 Pages traitées: {processed_pages}/{max_pages}")

        # Lancement des workers
        tasks = [asyncio.create_task(worker()) for _ in range(max_concurrent_tasks)]
        await asyncio.gather(*tasks)

    print(f"=== Crawl terminé: {processed_pages} pages ===")

def update_whoosh_index():
    """Met à jour l'index Whoosh avec les pages en attente."""
    from whoosh.index import open_dir
    ix = open_dir("indexdir")
    writer = ix.writer()
    for page in pages_collection.find({"status": "index_pending"}):
        writer.update_document(
            url=page["url"],
            title=page["title"],
            content=page["content"],
            snippet=page["snippet"]
        )
        pages_collection.update_one({"_id": page["_id"]}, {"$set": {"status": "indexed"}})
    writer.commit()
    print(f"📝 Index mis à jour avec {pages_collection.count_documents({'status': 'indexed'})} pages.")
