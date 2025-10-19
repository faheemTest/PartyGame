from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/partydb")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()
