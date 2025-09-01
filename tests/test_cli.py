import sys
import os
import shutil  # Ajout de l'import manquant
from pathlib import Path

# Ajoute le chemin racine du projet
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from click.testing import CliRunner
from cli import cli, crawl, update_index, search
from indexer import init_index
from db import pages_collection, urls_collection
from settings import INDEX_DIR

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Nettoyage avant les tests
    urls_collection.delete_many({})
    pages_collection.delete_many({})
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)

    # Crée un index vide pour éviter EmptyIndexError
    ix = init_index()

    yield
    # Nettoyage après les tests
    urls_collection.delete_many({})
    pages_collection.delete_many({})
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)

def test_crawl_command():
    runner = CliRunner()
    result = runner.invoke(crawl, ["--start-url", "https://example.com", "--max-pages", "1"])
    assert result.exit_code == 0
    assert urls_collection.count_documents({}) >= 1

def test_update_index_command():
    # Ajoute une page fictive dans MongoDB
    pages_collection.insert_one({
        "url": "https://example.com",
        "title": "Test Page",
        "content": "Ceci est un test.",
        "snippet": "Ceci est un test...",
        "crawled_date": "2025-01-01T00:00:00",
        "status": "index_pending"
    })

    runner = CliRunner()
    result = runner.invoke(update_index)
    assert result.exit_code == 0
    assert "Index mis à jour" in result.output

def test_search_command():
    # Ajoute une page fictive
    pages_collection.insert_one({
        "url": "https://example.com",
        "title": "Test Page",
        "content": "Ceci est un test.",
        "snippet": "Ceci est un test...",
        "crawled_date": "2025-01-01T00:00:00",
        "status": "index_pending"
    })

    # Met à jour l'index
    runner = CliRunner()
    update_result = runner.invoke(update_index)
    assert update_result.exit_code == 0

    # Teste la commande search
    search_result = runner.invoke(search, ["test"])
    assert search_result.exit_code == 0
    assert "Test Page" in search_result.output

def test_search_without_index():
    # Supprime l'index pour simuler un index non chargé
    if os.path.exists(INDEX_DIR):
        shutil.rmtree(INDEX_DIR)
    assert not os.path.exists(INDEX_DIR)  # Vérification

    runner = CliRunner()
    result = runner.invoke(search, ["test"])

    assert result.exit_code == 1  # Doit échouer avec un code d'erreur non-zéro
    assert "Index Whoosh n'est pas chargé" in result.output
