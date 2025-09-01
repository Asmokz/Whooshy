import click
import time
import asyncio
from crawler import crawl_async, load_seeds, update_whoosh_index

@click.group()
def cli():
    """Whooshy Searcher CLI"""
    pass

@cli.command()
@click.option('--start-url', default="https://books.toscrape.com/", help="URL de départ du crawl.")
@click.option('--max-pages', default=50, type=int, help="Nombre maximum de pages à crawler.")
@click.option('--max-tasks', default=10, type=int, help="Nombre maximum de tâches simultanées.")
def crawl(start_url, max_pages, max_tasks):
    """Lance le crawler asynchrone à partir d'une URL unique."""
    click.echo(f"🚀 Démarrage du crawl asynchrone pour {max_pages} pages (max {max_tasks} tâches simultanées) depuis {start_url}...")
    start_time = time.time()
    # Appelle crawl_async avec une liste contenant une seule URL
    asyncio.run(crawl_async(seeds=[start_url], max_pages=max_pages, max_concurrent_tasks=max_tasks))
    click.echo(f"✅ Crawl terminé en {time.time() - start_time:.2f} secondes.")

@cli.command()
def update_index():
    """Met à jour l'index Whoosh avec les pages en attente."""
    start_time = time.time()
    update_whoosh_index()
    click.echo(f"✅ Index mis à jour en {time.time() - start_time:.2f} secondes.")

@cli.command()
@click.option('--max-pages', default=20000, type=int, help="Nombre maximum de pages à crawler.")
@click.option('--max-tasks', default=50, type=int, help="Nombre maximum de tâches simultanées.")
def crawl_seeds(max_pages, max_tasks):
    """Lance le crawler asynchrone à partir d'une liste de seeds."""
    seeds = load_seeds()
    click.echo(f"🌱 Démarrage du crawl à partir de {len(seeds)} seeds : {seeds}")
    click.echo(f"🚀 Max pages: {max_pages}, tâches simultanées: {max_tasks}")
    start_time = time.time()
    asyncio.run(crawl_async(seeds=seeds, max_pages=max_pages, max_concurrent_tasks=max_tasks))
    click.echo(f"✅ Crawl terminé en {time.time() - start_time:.2f} secondes.")

@cli.command()
@click.argument('query')
def search(query):
    """Effectue une recherche dans l'index Whoosh."""
    from whoosh.index import open_dir
    from whoosh.qparser import QueryParser
    try:
        ix = open_dir("indexdir")
    except Exception as e:
        click.echo("❌ Index Whoosh non trouvé. Exécutez d'abord 'update-index'.", err=True)
        return
    with ix.searcher() as searcher:
        query_parser = QueryParser("content", ix.schema)
        whoosh_query = query_parser.parse(query)
        results = searcher.search(whoosh_query, limit=10)
        for hit in results:
            click.echo(f"📄 {hit['title']} ({hit['url']}): {hit['snippet']}")
        if not results:
            click.echo("🔍 Aucun résultat trouvé.")

if __name__ == "__main__":
    cli()
