# ISRO HelpBot - Real-Time Chat System

AI-powered chatbot for MOSDAC portal with real-time messaging capabilities.

## Quick Start

### Backend
```bash
cd isro-helpbot
python start.py
```

### Frontend
```bash
cd isro-helpbot/frontend
npm run dev
```

## Features

- ✅ Real-time messaging via WebSocket
- ✅ AI responses for MOSDAC queries
- ✅ Message persistence in MongoDB
- ✅ Modern Material-UI interface
- ✅ Automatic reconnection
- ✅ Error handling

## URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **WebSocket**: ws://localhost:8001/ws/{session_id}

## Requirements

- Python 3.8+
- Node.js 16+
- MongoDB

## Installation

```bash
# Backend dependencies
cd isro-helpbot/backend
pip install -r requirements.txt

# Frontend dependencies
cd isro-helpbot/frontend
npm install
```

## Usage

1. Start MongoDB
2. Run backend: `python start.py`
3. Run frontend: `npm run dev`
4. Open http://localhost:3000
5. Start chatting with the AI bot!
