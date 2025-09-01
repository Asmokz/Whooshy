from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from whoosh.qparser import QueryParser
from indexer import init_index
import uvicorn
from datetime import datetime
from settings import INDEX_DIR

# Initialise l'API FastAPI
app = FastAPI()

# Active CORS pour permettre les requêtes depuis Streamlit ou un frontend web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production (ex: ["http://localhost:8501"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Charge l'index Whoosh au démarrage de l'API
ix = init_index()

@app.get("/search")
async def search(q: str, limit: int = 10):
    """
    Endpoint pour effectuer une recherche dans l'index Whoosh.
    Exemple : /search?q=python&limit=5
    """
    try:
        with ix.searcher() as searcher:
            query_parser = QueryParser("content", ix.schema)
            query = query_parser.parse(q)
            results = searcher.search(query, limit=limit)

            # Formate les résultats pour une réponse JSON claire
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    "url": hit["url"],
                    "title": hit.get("title", "Sans titre"),
                    "snippet": hit.get("snippet", ""),
                    "crawled_date": hit.get("crawled_date", datetime.now()).isoformat()
                })

            return {"query": q, "results": formatted_results, "count": len(results)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche : {str(e)}")

@app.get("/status")
async def status():
    """Endpoint pour vérifier l'état de l'index."""
    try:
        return {
            "index_path": INDEX_DIR,
            "doc_count": ix.doc_count(),
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")

if __name__ == "__main__":
    # Lance le serveur FastAPI (pour le développement)
    uvicorn.run(app, host="0.0.0.0", port=8000)
