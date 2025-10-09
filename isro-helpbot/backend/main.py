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
from contextlib import asynccontextmanager
import routes
import database
import nlp_engine
from admin_routes import setup_admin_routes
from content_manager import initialize_content_manager

# Initialize global variables
content_database: Dict[str, dict] = {}
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
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
        
        # Initialize content manager
        try:
            await initialize_content_manager()
            print("Content manager initialized")
        except Exception as e:
            print(f"Content manager initialization failed: {e}")
        
        # Initialize content database by scraping and splitting into documents
        global content_database
        docs = scrape_and_index_mosdac()
        for d in docs:
            content_database[d['id']] = d
        print("Content database initialized")
        
        print("Backend initialization completed")
    except Exception as e:
        print(f"Startup error: {e}")
        # Don't raise the exception, allow the server to start
        print("Server starting without full initialization...")
    
    yield
    
    # Shutdown
    await database.close_mongodb_connection()

# Initialize FastAPI with metadata and lifespan
app = FastAPI(
    title="ISRO HelpBot API",
    description="Real-time chat API for ISRO HelpBot with MOSDAC integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup admin routes
setup_admin_routes(app)

def scrape_mosdac() -> str:
    """Scrape content from MOSDAC website"""
    try:
        response = requests.get("https://www.mosdac.gov.in", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove scripts/styles and common layout elements
            for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside', 'form']):
                tag.decompose()

            # Prefer semantic containers: <main>, <article>, or a content div
            main_content = None
            main_content = soup.find('main') or soup.find('article')
            if not main_content:
                # look for common content id/class patterns
                main_content = soup.find('div', id=re.compile(r'content|main|page', re.I))
            if not main_content:
                main_content = soup.find('div', class_=re.compile(r'content|main|page', re.I))

            if main_content:
                # Gather meaningful paragraph-like text, preserve headings, lists and links
                parts = []
                for el in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li', 'a']):
                    txt = el.get_text(separator=' ', strip=True)
                    if not txt:
                        continue
                    # If the element is an anchor, try to capture the href
                    href = None
                    try:
                        if el.name == 'a' and el.has_attr('href'):
                            href = el['href']
                        else:
                            # also check for anchors inside list items or headings
                            a = el.find('a')
                            if a and a.has_attr('href'):
                                href = a['href']
                    except Exception:
                        href = None

                    if href:
                        # normalize relative URLs
                        if href.startswith('/'):
                            href = 'https://www.mosdac.gov.in' + href
                        parts.append(f"{txt} (link: {href})")
                    else:
                        parts.append(txt)
                text_content = '\n'.join(parts)
            else:
                # Fallback: minimal body text but try to avoid menus
                body = soup.body
                if body:
                    parts = [p.get_text(separator=' ', strip=True) for p in body.find_all(['p', 'article', 'section'])]
                    text_content = '\n'.join(parts)
                else:
                    text_content = ''

            # Remove obvious navigation/footer repeats and very short menu fragments
            # and common site boilerplate phrases to avoid returning them as answers.
            blacklist_phrases = [
                'skip to main', 'signup', 'sign up', 'login', 'logout', 'secondary menu',
                'served by', 'copyright', 'privacy policy', 'terms & conditions', 'hyperlink policy',
                'contact us', 'feedback', 'due to preventive maintenance', 'sitemap', 'help'
            ]
            cleaned_lines = []
            for line in text_content.splitlines():
                l = line.strip()
                if not l:
                    continue
                low = l.lower()
                # drop lines that are mostly uppercase menu tokens or contain blacklist phrases
                if any(bp in low for bp in blacklist_phrases):
                    continue
                # drop lines which are too short or are just repeated tokens
                if len(l) < 30:
                    # small chance it's useful; keep if contains a verb-like token
                    if re.search(r'\b(is|are|provide|offers|access|data|download|product)\b', low):
                        cleaned_lines.append(l)
                    continue
                cleaned_lines.append(l)

            cleaned = '\n'.join(cleaned_lines)
            # Truncate content to a reasonable size to avoid huge responses
            max_len = 20000
            if len(cleaned) > max_len:
                cleaned = cleaned[:max_len]
            return cleaned
        return ""
    except Exception as e:
        print(f"Error scraping MOSDAC: {e}")
        return ""


def scrape_and_index_mosdac() -> list:
    """Scrape MOSDAC and produce a list of structured content documents.

    Returns a list of documents suitable for indexing/searching. Each anchor
    (announcement/link) becomes a separate doc when possible, plus a main page
    doc as a fallback.
    """
    docs = []
    try:
        response = requests.get("https://www.mosdac.gov.in", timeout=10)
        if response.status_code != 200:
            return docs

        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside', 'form']):
            tag.decompose()

        main_content = soup.find('main') or soup.find('article')
        if not main_content:
            main_content = soup.find('div', id=re.compile(r'content|main|page', re.I))
        if not main_content:
            main_content = soup.find('div', class_=re.compile(r'content|main|page', re.I))

        seen_urls = set()

        if main_content:
            # first, index anchor items (announcements, pdf links, etc.)
            for a in main_content.find_all('a'):
                try:
                    text = a.get_text(separator=' ', strip=True)
                    href = a.get('href')
                    if not text or not href:
                        continue
                    # normalize href
                    if href.startswith('/'):
                        href = 'https://www.mosdac.gov.in' + href
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # gather surrounding context (parent paragraph or list item)
                    parent = a.find_parent(['p', 'li', 'div', 'section', 'article'])
                    context_text = ''
                    if parent:
                        context_text = parent.get_text(separator=' ', strip=True)

                    doc = {
                        'id': str(uuid.uuid4()),
                        'title': text,
                        'content': context_text or text,
                        'url': href,
                        'content_type': 'link',
                        'indexed_at': datetime.now(),
                        'word_count': len((context_text or text).split())
                    }
                    docs.append(doc)
                except Exception:
                    continue

            # also add paragraphs/headings as separate docs if they look important
            for el in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'p']):
                try:
                    txt = el.get_text(separator=' ', strip=True)
                    if not txt or len(txt) < 40:
                        continue
                    # avoid duplicating already indexed urls/text
                    if txt in [d['content'] for d in docs]:
                        continue
                    doc = {
                        'id': str(uuid.uuid4()),
                        'title': (el.name + ': ' + txt[:80]) if el.name.startswith('h') else txt[:60],
                        'content': txt,
                        'url': 'https://www.mosdac.gov.in',
                        'content_type': 'paragraph',
                        'indexed_at': datetime.now(),
                        'word_count': len(txt.split())
                    }
                    docs.append(doc)
                except Exception:
                    continue

        # If nothing found, create a fallback doc with body text
        if not docs:
            body = soup.body
            text_content = ''
            if body:
                parts = [p.get_text(separator=' ', strip=True) for p in body.find_all(['p', 'section', 'article'])]
                text_content = '\n'.join([p for p in parts if p])
            docs.append({
                'id': 'mosdac',
                'title': 'MOSDAC Main Page',
                'content': text_content,
                'url': 'https://www.mosdac.gov.in',
                'content_type': 'webpage',
                'indexed_at': datetime.now(),
                'word_count': len(text_content.split())
            })

        # truncate and clean docs
        for d in docs:
            if d.get('content') and len(d['content']) > 20000:
                d['content'] = d['content'][:20000]

        return docs
    except Exception as e:
        print('Error in scrape_and_index_mosdac:', e)
        return docs

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

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": db is not None,
        "content_database_size": len(content_database),
        "version": "1.0.0"
    }

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
        # await self.send_system_message(
        #     session_id,
        #     "Connected to MOSDAC AI Assistant"
        # )

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
                # Use upsert to avoid duplicate key errors
                await db.messages.replace_one(
                    {"id": message["id"], "session_id": session_id},  # Filter by message id and session
                    {
                        **message,
                        "session_id": session_id,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    },
                    upsert=True  # Insert if doesn't exist, update if exists
                )
        except Exception as e:
            print(f"Error storing message: {e}")

manager = ConnectionManager()

async def get_ai_response(question: str, session_id: str) -> str:
    """Delegate response generation to the NLP engine module."""
    try:
        return await nlp_engine.get_ai_response(question, session_id, db, content_database)
    except Exception as e:
        print(f"Error in NLP engine: {e}")
        return "I apologize, something went wrong while generating the response. Please try again."

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
                    await db.messages.replace_one(
                        {"id": message_data["id"], "session_id": session_id},
                        {
                            **message_data,
                            "session_id": session_id,
                            "created_at": datetime.now(),
                            "updated_at": datetime.now()
                        },
                        upsert=True
                    )
                except Exception as e:
                    print(f"Error storing user message: {e}")
            
            # Send message received acknowledgment
            await manager.send_message(session_id, {
                **message_data,
                "status": "processing"
            })
            
            try:
                # Get bot response
                bot_response = await get_ai_response(user_message, session_id)
                
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
                        await db.messages.replace_one(
                            {"id": bot_message["id"], "session_id": session_id},
                            {
                                **bot_message,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            upsert=True
                        )
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)