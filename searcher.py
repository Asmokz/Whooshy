from whoosh.qparser import MultifieldParser
from whoosh import scoring
from db import pages_collection

def search(query_str, ix, limit=10):
    parser = MultifieldParser(["title", "content"], ix.schema, fieldboosts={"title": 2.0, "content": 1.0})
    query = parser.parse(query_str)
    with ix.searcher(weighting=scoring.BM25F()) as searcher:
        results = searcher.search(query, limit=limit)
        print(f"🔎 Recherche '{query_str}' → {len(results)} résultat(s)")
        for r in results:
            url, title = r["url"], r["title"]
            snippet = pages_collection.find_one({"url": url}, {"snippet": 1}).get("snippet", "")
            print(f"- {title} ({url})\n  {snippet}\n")