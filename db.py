import pymongo
from settings import MONGO_URI

client = pymongo.MongoClient(MONGO_URI)
db = client["Whooshy"]

# Crée des indexes utiles si pas déjà présents
db["urls"].create_index("url", unique=True)
db["urls"].create_index("status")
db["pages"].create_index("url", unique=True)

urls_collection = db["urls"]
pages_collection = db["pages"]