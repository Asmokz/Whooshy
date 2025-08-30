# cli.py
import argparse
from crawler import crawl_multithreaded
from searcher import search_func
import settings
import click
import time
import os

from whooshy import load_data_into_whoosh


@click.group()
def cli():
    """Whooshy Searcher CLI"""
    pass

@cli.command()
@click.option('--start-url', default="https://books.toscrape.com/", help="URL de départ du crawl.")
@click.option('--max-pages', default=20, type=int, help="Nombre maximum de pages à crawler.")
@click.option('--max-threads', default=10, type=int, help="Nombre de threads maximum pour le crawl.")
def crawl(start_url, max_pages, max_threads):
    """Lance le crawler et indexe les pages dans MongoDB."""
    start_time = time.time()
    crawl_multithreaded(start_url, max_threads=max_threads, max_pages=max_pages)
    print("--- %s seconds ---" % (time.time() - start_time))

@cli.command()
def load_index():
    """Charge les données de MongoDB vers l'index Whoosh."""
    global ix
    start_time = time.time()
    ix = load_data_into_whoosh()
    print("--- %s seconds ---" % (time.time() - start_time))
    
@cli.command()
@click.argument('query_str')
def search(query_str):
    """Effectue une recherche sur l'index Whoosh."""
    # On s'assure que l'index a été chargé
    if not os.path.exists(settings.INDEX_DIR) or ix.doc_count() == 0:
        print("L'index Whoosh n'existe pas ou est vide. Veuillez d'abord le charger avec la commande 'load-index'.")
        return
    
    start_time = time.time()
    search_func(query_str, ix)
    print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == "__main__":
    cli()