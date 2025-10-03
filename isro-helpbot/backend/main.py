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
from routes import router
import database

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

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    print("Starting up the application...")
    try:
        await database.connect_to_mongodb()
        print("Database connection established")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down the application...")
    await database.close_mongodb_connection()

# Initialize global variables
content_database: Dict[str, str] = {}

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
        # Connect to MongoDB
        await database.connect_to_mongodb()
        print("MongoDB connection established")
        
        # Initialize content database
        content = scrape_mosdac()
        global content_database
        content_database["mosdac"] = content
        print("Content database initialized")
    except Exception as e:
        print(f"Startup error: {e}")
        raise

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
app.include_router(router, prefix="/api")

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
                await websocket.send_json(message)
                # Store message in MongoDB
                await self.store_message(session_id, message)
            except Exception as e:
                print(f"Error sending message: {e}")
                self.disconnect(session_id)

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
            await db.messages.insert_one({
                **message,
                "session_id": session_id,
                "created_at": datetime.now()
            })
        except Exception as e:
            print(f"Error storing message: {e}")

manager = ConnectionManager()

# Store scraped content
content_database: Dict[str, str] = {}

def scrape_mosdac():
    """Scrape content from MOSDAC website"""
    try:
        response = requests.get("https://www.mosdac.gov.in")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract text content
            text_content = ' '.join([p.get_text() for p in soup.find_all(['p', 'div', 'section'])])
            return text_content
        return ""
    except Exception as e:
        print(f"Error scraping MOSDAC: {e}")
        return ""

async def get_ai_response(question: str) -> str:
    """Generate AI response based on the question and scraped content"""
    try:
        # Prepare input for the model
        inputs = tokenizer(
            question,
            str(content_database),
            return_tensors="pt",
            max_length=512,
            truncation=True
        )

        # Get model output
        outputs = model(**inputs)
        
        # Extract answer
        answer_start = outputs.start_logits.argmax()
        answer_end = outputs.end_logits.argmax()
        
        answer = tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end+1])
        
        if not answer or answer.strip() == "":
            return "I apologize, but I couldn't find specific information about that. Please try rephrasing your question or ask something else about MOSDAC's services."
        
        return answer

    except Exception as e:
        return f"I apologize, but I encountered an error. Please try asking your question differently."

@app.on_event("startup")
def startup_event():
    """Initialize content database on startup"""
    content = scrape_mosdac()
    content_database["mosdac"] = content

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
    await manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("text", "")
            message_id = str(uuid.uuid4())
            
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
            await db.messages.insert_one(message_data)
            
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
                await db.messages.insert_one(bot_message)
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