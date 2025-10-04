from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
import uuid
import database
from pydantic import BaseModel

router = APIRouter()

class SessionCreate(BaseModel):
    user_id: Optional[str] = None

@router.post("/sessions/create")
async def create_session(session_data: Optional[SessionCreate] = None):
    """Create a new chat session"""
    # Create session document
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    session = {
        "session_id": session_id,
        "user_id": session_data.user_id if session_data else None,
        "created_at": now,
        "last_active": now,
        "context": {},
        "status": "active",
    }

    try:
        # Try to persist session if DB is available, but do not fail if DB is down
        persisted = False
        if database.db is None:
            print("No database connection, attempting to connect...")
            await database.connect_to_mongodb()

        if database.db is not None:
            try:
                print(f"Creating session with ID: {session_id}")
                result = await database.db.sessions.insert_one(session)
                if result and getattr(result, "inserted_id", None):
                    persisted = True
                    print(f"Successfully created session with ID: {session_id}")
            except Exception as db_error:
                print(f"Database write failed (will continue without persistence): {db_error}")

        # Return created session payload even if not persisted
        return {
            "session_id": session_id,
            "status": "created",
            "created_at": now.isoformat(),
            "persisted": persisted,
        }

    except HTTPException as http_error:
        print(f"HTTP error in create_session: {http_error.detail}")
        raise http_error
    except Exception as e:
        print(f"Unexpected error in create_session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error occurred: {str(e)}",
        )

@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str):
    """Get all sessions for a user"""
    try:
        if database.db is None:
            await database.connect_to_mongodb()
            if database.db is None:
                raise HTTPException(
                    status_code=503,
                    detail="Database connection not available",
                )

        sessions = await database.db.sessions.find({"user_id": user_id}).to_list(length=None)
        return sessions
    except Exception as e:
        print(f"Error getting user sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")

@router.get("/messages/{session_id}")
async def get_session_messages(session_id: str, limit: int = 50):
    """Get messages for a session"""
    try:
        if database.db is None:
            await database.connect_to_mongodb()
            if database.db is None:
                raise HTTPException(
                    status_code=503,
                    detail="Database connection not available",
                )

        messages = await database.db.messages.find(
            {"session_id": session_id},
            {"_id": 0}  # Exclude MongoDB ObjectId
        ).sort("timestamp", -1).limit(limit).to_list(length=None)
        
        if messages is None:
            return []
            
        return messages
    except Exception as e:
        print(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")

@router.post("/sessions/{session_id}/context")
async def update_session_context(session_id: str, context: dict):
    """Update session context"""
    try:
        if not database.db:
            raise HTTPException(
                status_code=503,
                detail="Database connection not available"
            )

        result = await database.db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "context": context,
                    "last_active": datetime.utcnow()
                }
            }
        )
        
        if not result.matched_count:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
            
        return {"status": "updated"}
    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        print(f"Error updating session context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update session context"
        )