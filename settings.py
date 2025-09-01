import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
INDEX_DIR = "indexdir"
MY_USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
RECRAWL_DELAY_DAYS = 7
MAX_RETRIES = 3