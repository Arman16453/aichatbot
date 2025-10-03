from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import json
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
import uuid
from pydantic import BaseModel
from . import routes
from . import database

# Initialize FastAPI with metadata
app = FastAPI(
    title="ISRO HelpBot API",
    description="Real-time chat API for ISRO HelpBot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global variables
content_database: Dict[str, str] = {}
db = None

def scrape_mosdac() -> str:
    """Scrape content from MOSDAC website"""
    try:
        response = requests.get("https://www.mosdac.gov.in", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract text content
            text_content = ' '.join([p.get_text() for p in soup.find_all(['p', 'div', 'section'])])
            return text_content
        return ""
    except Exception as e:
        print(f"Error scraping MOSDAC: {e}")
        return ""

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections and data on startup"""
    try:
        # Try to connect to MongoDB (optional)
        try:
            await database.connect_to_mongodb()
            global db
            db = database.get_database()
            print("MongoDB connection established")
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            print("Continuing without MongoDB...")
            db = None
        
        # Initialize content database
        content = scrape_mosdac()
        global content_database
        content_database["mosdac"] = content
        print("Content database initialized")
        
        print("Backend initialization completed")
    except Exception as e:
        print(f"Startup error: {e}")
        # Don't raise the exception, allow the server to start
        print("Server starting without full initialization...")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    await database.close_mongodb_connection()

class Session(BaseModel):
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_active: datetime
    context: Dict = {}
    status: str = "active"  # active, ended

class Message(BaseModel):
    id: str
    session_id: str
    text: str
    sender: str
    timestamp: datetime
    context: Dict = {}
    status: str = "sent"  # sent, received, processing, completed, error
    error: Optional[str] = None

# Include routes
app.include_router(routes.router, prefix="/api")

# Store active websocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids

    async def connect(self, websocket: WebSocket, session_id: str, user_id: Optional[str] = None) -> None:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        if user_id:
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

        # Send connection acknowledgment
        await self.send_system_message(
            session_id,
            "Connected to MOSDAC AI Assistant"
        )

    def disconnect(self, session_id: str, user_id: Optional[str] = None) -> None:
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if user_id and user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]

    async def send_message(self, session_id: str, message: Dict) -> None:
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Clean message for JSON serialization
                clean_message = self.clean_message_for_json(message)
                await websocket.send_json(clean_message)
                # Store message in MongoDB
                await self.store_message(session_id, message)
            except Exception as e:
                print(f"Error sending message: {e}")
                self.disconnect(session_id)
    
    def clean_message_for_json(self, message: Dict) -> Dict:
        """Clean message to ensure JSON serialization"""
        import json
        from bson import ObjectId
        
        def convert_objectid(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_objectid(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_objectid(item) for item in obj]
            else:
                return obj
        
        return convert_objectid(message)

    async def send_system_message(self, session_id: str, text: str) -> None:
        message = {
            "id": str(uuid.uuid4()),
            "text": text,
            "sender": "system",
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        }
        await self.send_message(session_id, message)

    async def store_message(self, session_id: str, message: Dict) -> None:
        """Store message in MongoDB"""
        try:
            if db is not None:
                await db.messages.insert_one({
                    **message,
                    "session_id": session_id,
                    "created_at": datetime.now()
                })
        except Exception as e:
            print(f"Error storing message: {e}")

manager = ConnectionManager()

async def get_ai_response(question: str) -> str:
    """Generate AI response based on the question and scraped content"""
    try:
        # For now, use a simple rule-based response system
        # This can be enhanced with actual AI models later
        question_lower = question.lower().strip()
        
        # Handle greetings and casual questions
        if any(greeting in question_lower for greeting in ['hello', 'hi', 'hey', 'how are you', 'how do you do']):
            return "Hello! I'm doing well, thank you for asking. I'm here to help you with information about MOSDAC's satellite data and services. What would you like to know about our meteorological and oceanographic data?"
        
        # Handle questions about MOSDAC
        elif any(keyword in question_lower for keyword in ['what is mosdac', 'mosdac', 'satellite data', 'data']):
            return "MOSDAC (Meteorological and Oceanographic Satellite Data Archival Centre) is ISRO's data archival center that provides satellite data and services. We offer various satellite products, meteorological data, and oceanographic information. You can access real-time and historical data through our portal."
        
        # Handle weather-related questions
        elif any(keyword in question_lower for keyword in ['weather', 'meteorology', 'forecast', 'temperature', 'rain', 'climate']):
            return "MOSDAC offers comprehensive meteorological satellite data including weather monitoring, atmospheric parameters, and forecasting products. You can access real-time weather data, historical meteorological information, and climate datasets. Our data includes temperature, humidity, precipitation, and atmospheric pressure measurements."
        
        # Handle ocean-related questions
        elif any(keyword in question_lower for keyword in ['ocean', 'sea', 'marine', 'water', 'coastal']):
            return "Our oceanographic data includes sea surface temperature, ocean color, sea level measurements, and marine meteorological parameters. These datasets are essential for marine research, coastal monitoring, and oceanographic studies. You can access both real-time and historical ocean data."
        
        # Handle data access questions
        elif any(keyword in question_lower for keyword in ['download', 'access', 'get data', 'how to', 'where to']):
            return "You can download satellite data and products from our portal at www.mosdac.gov.in. Visit the data download section to access various datasets. Some products may require registration. We provide data in various formats including NetCDF, HDF, and GeoTIFF."
        
        # Handle help and support questions
        elif any(keyword in question_lower for keyword in ['help', 'support', 'assistance', 'guide']):
            return "I'm here to help you with information about MOSDAC's satellite data and services. You can ask me about specific data products, how to access them, data formats, or general information about our services. What specific information do you need?"
        
        # Handle technical questions
        elif any(keyword in question_lower for keyword in ['format', 'resolution', 'frequency', 'satellite', 'sensor']):
            return "MOSDAC provides data from various satellites including INSAT, Oceansat, and other ISRO missions. Data is available in different formats (NetCDF, HDF, GeoTIFF) with varying spatial and temporal resolutions. The data frequency depends on the satellite and sensor specifications."
        
        # Default response for other questions
        else:
            return "I can help you with information about MOSDAC's satellite data, meteorological products, oceanographic data, and services. You can ask me about:\n\n• Weather and climate data\n• Ocean and marine data\n• How to download data\n• Data formats and specifications\n• Satellite information\n\nWhat specific topic would you like to know more about?"

    except Exception as e:
        return "I apologize, but I encountered an error processing your question. Please try asking your question differently, or ask me about MOSDAC's satellite data and services."

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
    await manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("text", "")
            message_id = data.get("id", str(uuid.uuid4()))
            
            # Create message data
            message_data = {
                "id": message_id,
                "text": user_message,
                "timestamp": datetime.now().isoformat(),
                "sender": "user",
                "session_id": session_id,
                "user_id": user_id,
                "status": "received"
            }
            
            # Store user message
            if db is not None:
                try:
                    await db.messages.insert_one(message_data)
                except Exception as e:
                    print(f"Error storing user message: {e}")
            
            # Send message received acknowledgment
            await manager.send_message(session_id, {
                **message_data,
                "status": "processing"
            })
            
            try:
                # Get bot response
                bot_response = await get_ai_response(user_message)
                
                # Create bot message data
                bot_message = {
                    "id": str(uuid.uuid4()),
                    "text": bot_response,
                    "timestamp": datetime.now().isoformat(),
                    "sender": "bot",
                    "session_id": session_id,
                    "user_id": user_id,
                    "status": "sent",
                    "in_response_to": message_id
                }
                
                # Store and send bot response
                if db is not None:
                    try:
                        await db.messages.insert_one(bot_message)
                    except Exception as e:
                        print(f"Error storing bot message: {e}")
                await manager.send_message(session_id, bot_message)
                
                # Update original message status to completed
                await manager.send_message(session_id, {
                    **message_data,
                    "status": "completed"
                })
                
            except Exception as e:
                print(f"Error generating response: {e}")
                # Send error status
                await manager.send_message(session_id, {
                    **message_data,
                    "status": "error",
                    "error": str(e)
                })
                
    except WebSocketDisconnect:
        manager.disconnect(session_id, user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(session_id, user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)