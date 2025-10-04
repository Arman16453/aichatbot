from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio
import os

# MongoDB client instance
client: Optional[AsyncIOMotorClient] = None
db = None
is_connected = False

# Simple MongoDB configuration; keep minimal and fast-failing for local dev
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DBNAME = os.getenv("MONGO_DBNAME", "isro_chatbot")

async def connect_to_mongodb():
    """Attempt to connect to MongoDB once with a short timeout.

    Returns the `db` instance if successful, otherwise returns None.
    The function will not raise on failure — callers should handle a None return.
    """
    global client, db, is_connected
    # Use a short server selection timeout so failures are fast and do not block startup
    options = {"serverSelectionTimeoutMS": 5000, "connectTimeoutMS": 5000}

    try:
        connection_url = f"mongodb://{MONGO_HOST}:{MONGO_PORT}"
        print(f"Attempting MongoDB connection to {connection_url}...")

        # Close existing client if present
        if client:
            try:
                client.close()
            except Exception:
                pass

        client = AsyncIOMotorClient(connection_url, **options)

        # Test connection quickly
        try:
            await asyncio.wait_for(client.admin.command("ping"), timeout=5.0)
        except Exception as e:
            # Clean up client and return None, but don't raise
            try:
                client.close()
            except Exception:
                pass
            client = None
            db = None
            is_connected = False
            print(f"MongoDB ping failed: {e}")
            return None

        # Initialize db
        db = client[MONGO_DBNAME]

        # Best-effort index creation (do not fail startup on errors)
        try:
            await db.sessions.create_index("session_id", unique=True)
            await db.messages.create_index([("session_id", 1), ("timestamp", -1)])
        except Exception as idx_e:
            print(f"Index creation warning: {idx_e}")

        is_connected = True
        print("MongoDB connection established")
        return db

    except Exception as e:
        # Any unexpected error: ensure client cleaned up and return None
        try:
            if client:
                client.close()
        except Exception:
            pass
        client = None
        db = None
        is_connected = False
        print(f"MongoDB connection error: {e}")
        return None

def get_database():
    """Return the current db instance (or None)."""
    global db
    return db

async def close_mongodb_connection():
    """Close MongoDB connection (no-op if not connected)."""
    global client, db, is_connected
    if client is not None:
        try:
            client.close()
            print("Closed MongoDB connection")
        except Exception as e:
            print(f"Error closing MongoDB client: {e}")
    client = None
    db = None
    is_connected = False