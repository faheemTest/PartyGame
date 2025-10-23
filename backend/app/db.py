# backend/app/db.py
import os
from dotenv import load_dotenv

load_dotenv()

# read MONGO_URL from environment (set this in Render)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/partygame")

# Use Motor (async MongoDB driver) so it works with FastAPI async code
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
# get default database from connection string if provided, else use "partygame"
try:
    db_name = client.get_default_database().name
except Exception:
    db_name = "partygame"

db = client.get_database(db_name)
