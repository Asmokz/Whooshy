import os, shutil
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.index import create_in, open_dir

from settings import INDEX_DIR

def init_index():
    schema = Schema(
        url=ID(stored=True, unique=True),
        title=TEXT(stored=True, field_boost=2.0),
        content=TEXT,
        snippet=TEXT(stored=True),
        crawled_date=DATETIME(stored=True)
    )
    if not os.path.exists(INDEX_DIR):
        os.mkdir(INDEX_DIR)
        return create_in(INDEX_DIR, schema)
    else:
        return open_dir(INDEX_DIR)

def add_doc_to_whoosh(ix, doc):
    with ix.writer() as writer:
        writer.update_document(
            url=doc["url"],
            title=doc["title"],
            content=doc["content"],
            snippet=doc.get("snippet", ""),
            crawled_date=doc.get("crawled_date")
        )