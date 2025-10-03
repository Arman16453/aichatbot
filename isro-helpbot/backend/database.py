from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio

# MongoDB client instance
client: Optional[AsyncIOMotorClient] = None
db = None
is_connected = False

# MongoDB Configuration
MONGO_CONFIG = {
    'host': 'localhost',
    'port': 27017,
    'db_name': 'isro_chatbot',
    'options': {
        'serverSelectionTimeoutMS': 30000,     # Increased server selection timeout
        'connectTimeoutMS': 30000,            # Increased connection timeout
        'socketTimeoutMS': 45000,             # Increased socket timeout
        'retryWrites': True,
        'retryReads': True,
        'w': 1,                               # Changed from majority to 1 for faster writes
        'wtimeoutMS': 30000,                  # Increased write timeout
        'maxPoolSize': 10,                    # Reduced pool size for better stability
        'minPoolSize': 1,
        'serverSelectionTimeoutMS': 30000,   # Server selection timeout
        'waitQueueTimeoutMS': 30000           # Wait queue timeout
    }
}

async def connect_to_mongodb():
    """Connect to MongoDB and initialize the database"""
    global client, db
    max_retries = 3
    retry_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to MongoDB (attempt {attempt + 1}/{max_retries})...")
            connection_url = f"mongodb://{MONGO_CONFIG['host']}:{MONGO_CONFIG['port']}"
            print(f"Connection URL: {connection_url}")
            
            # Create client with retry writes enabled
            if client:
                print("Closing existing client connection...")
                client.close()
            
            client = AsyncIOMotorClient(
                connection_url,
                **MONGO_CONFIG['options']
            )
            
            # Test connection with timeout
            print("Testing MongoDB connection...")
            try:
                await asyncio.wait_for(
                    client.admin.command('ping'),
                    timeout=10.0  # Increased timeout for ping
                )
                print("MongoDB ping successful")
            except asyncio.TimeoutError:
                print(f"MongoDB connection test timed out (attempt {attempt + 1})")
                if attempt == max_retries - 1:  # Last attempt
                    raise Exception(f"MongoDB connection test timed out after {max_retries} attempts")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            
            # Initialize database and collections
            print("Initializing database and collections...")
            db = client[MONGO_CONFIG['db_name']]
            
            # Create indexes
            print("Creating indexes...")
            await db.sessions.create_index("session_id", unique=True)
            await db.messages.create_index([
                ("session_id", 1),
                ("timestamp", -1)
            ])
            
            print("Successfully connected to MongoDB and initialized collections")
            global is_connected
            is_connected = True
            return db
            
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:  # Last attempt
                if client:
                    print("Closing failed connection...")
                    client.close()
                    client = None
                    db = None
                    is_connected = False
                raise Exception(f"MongoDB connection failed after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
            continue
    
    return None  # Should never reach here due to the raise in the last attempt

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global client, db, is_connected
    if client is not None:
        client.close()
        print("Closed MongoDB connection")
        client = None
        db = None
        is_connected = False

def get_database():
    """Get the database instance"""
    global db
    return db

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global client, db, is_connected
    if client is not None:
        client.close()
        print("Closed MongoDB connection")
        client = None
        db = None
        is_connected = False