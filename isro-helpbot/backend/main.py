from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from bs4 import BeautifulSoup
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

app = FastAPI()

# MongoDB setup
mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
db = mongo_client.isro_chatbot

class Session(BaseModel):
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    last_active: datetime
    context: Dict = {}

class Message(BaseModel):
    id: str
    session_id: str
    text: str
    sender: str
    timestamp: datetime
    context: Dict = {}

app = FastAPI()

# Store active websocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_json({
            "text": message,
            "timestamp": datetime.now().isoformat(),
            "sender": "bot"
        })

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Process the message
            response = await get_ai_response(data)
            
            # Send response back to client
            await websocket.send_text(json.dumps({
                "message": response,
                "type": "bot"
            }))
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)