import os
import sys
from pathlib import Path

# Ajoute le chemin racine du projet à sys.path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from api import app, ix
from indexer import init_index, add_doc_to_whoosh
from db import pages_collection
from datetime import datetime
from settings import INDEX_DIR



# Fixture pour initialiser un client de test FastAPI
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

# Fixture pour peupler l'index avec des données de test
@pytest.fixture(autouse=True)
def setup_test_data():
    # Nettoie l'index et la base de données avant chaque test
    pages_collection.delete_many({})
    if os.path.exists(INDEX_DIR):
        import shutil
        shutil.rmtree(INDEX_DIR)

    # Ajoute une page fictive
    pages_collection.insert_one({
        "url": "https://example.com",
        "title": "Test Page",
        "content": "Ceci est un test pour l'API.",
        "snippet": "Ceci est un test...",
        "crawled_date": datetime.now(),
        "status": "index_pending"
    })

    # Met à jour l'index Whoosh
    ix = init_index()
    doc = pages_collection.find_one({})
    add_doc_to_whoosh(ix, doc)

    yield
    # Nettoie après le test
    pages_collection.delete_many({})

# Test 1 : Vérifie que `/status` renvoie des informations valides
def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "index_path" in data
    assert "doc_count" in data
    assert data["doc_count"] == 1  # Doit contenir 1 document

# Test 2 : Vérifie que `/search` renvoie des résultats
def test_search_endpoint(client):
    response = client.get("/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Test Page"

# Test 3 : Vérifie que `/search` gère les erreurs
def test_search_error(client):
    # Supprime l'index pour simuler une erreur
    if os.path.exists(INDEX_DIR):
        import shutil
        shutil.rmtree(INDEX_DIR)

    response = client.get("/search?q=test")
    assert response.status_code == 500
    assert "Erreur" in response.json()["detail"]

# Test 4 : Vérifie que `/search` renvoie un message si aucun résultat
def test_search_no_results(client):
    response = client.get("/search?q=inexistant12345")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0
