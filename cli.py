# cli.py
import argparse
from crawler import crawl
from db import save_page, get_all_pages
from searcher import search_pages
from indexer import build_index, search_index
import settings


def main():
    parser = argparse.ArgumentParser(description="Mini moteur de recherche (CLI)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Commande pour crawler
    crawl_parser = subparsers.add_parser("crawl", help="Crawler une URL")
    crawl_parser.add_argument("url", help="URL de départ")
    crawl_parser.add_argument(
        "--depth", type=int, default=settings.MAX_DEPTH, help="Profondeur de crawl"
    )

    # Commande pour rechercher (full-text regex)
    search_parser = subparsers.add_parser("search", help="Rechercher un mot-clé")
    search_parser.add_argument("query", help="Mot-clé à chercher")

    # Commande pour indexer (TF-IDF / autre méthode)
    subparsers.add_parser("index", help="Construire l’index des pages")
    index_search_parser = subparsers.add_parser("index-search", help="Rechercher via l’index")
    index_search_parser.add_argument("query", help="Mot-clé à chercher")

    # Commande pour afficher la base
    subparsers.add_parser("showdb", help="Lister les pages en base")

    args = parser.parse_args()

    if args.command == "crawl":
        print(f"Crawling depuis {args.url} (profondeur {args.depth})...")
        pages = crawl(args.url, args.depth)
        for page in pages:
            save_page(page)

    elif args.command == "search":
        results = search_pages(args.query)
        print(f"Résultats pour '{args.query}':")
        for r in results:
            print(f"- {r['url']}")

    elif args.command == "index":
        print("Construction de l’index...")
        build_index()

    elif args.command == "index-search":
        results = search_index(args.query)
        print(f"Résultats indexés pour '{args.query}':")
        for r in results:
            print(f"- {r['url']} (score={r['score']})")

    elif args.command == "showdb":
        pages = get_all_pages()
        print("Pages en base :")
        for p in pages:
            print(f"- {p['url']}")

if __name__ == "__main__":
    main()