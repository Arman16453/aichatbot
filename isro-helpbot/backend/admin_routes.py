"""
Admin Dashboard Routes for ISRO HelpBot
Provides administrative interfaces and analytics
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
from content_manager import get_content_manager, ContentManager
import database

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic models for request/response
class SyncRequest(BaseModel):
    force: bool = False

class ContentUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    is_active: Optional[bool] = None

class FeedbackRequest(BaseModel):
    content_id: str
    feedback_score: float  # 1-5 rating
    feedback_text: Optional[str] = None
    user_id: Optional[str] = None

class AnalyticsQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    content_type: Optional[str] = None
    event_type: Optional[str] = None

# Admin authentication (simplified for hackathon)
async def verify_admin_access():
    """Simple admin verification - in production use proper auth"""
    # For hackathon purposes, we'll allow all access
    # In production, implement proper JWT/session authentication
    return True

@admin_router.get("/dashboard/stats")
async def get_dashboard_stats(admin_verified: bool = Depends(verify_admin_access)):
    """Get comprehensive dashboard statistics"""
    try:
        content_manager = await get_content_manager()
        
        # Get content statistics
        content_stats = await content_manager.get_content_statistics()
        
        # Get sync history
        sync_history = await content_manager.get_sync_history(limit=5)
        
        # Get recent analytics if database is available
        recent_analytics = {}
        if content_manager.db is not None:
            try:
                # Most viewed content
                pipeline = [
                    {"$match": {"is_active": True}},
                    {"$sort": {"view_count": -1}},
                    {"$limit": 10},
                    {"$project": {"title": 1, "view_count": 1, "url": 1, "content_type": 1}}
                ]
                most_viewed = await content_manager.db.content.aggregate(pipeline).to_list(length=10)
                recent_analytics['most_viewed'] = most_viewed
                
                # Recent activity
                pipeline = [
                    {"$match": {"timestamp": {"$gte": datetime.now() - timedelta(days=7)}}},
                    {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                activity = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=None)
                recent_analytics['activity_by_type'] = {item['_id']: item['count'] for item in activity}
                
                # Daily activity for the last 7 days
                pipeline = [
                    {"$match": {"timestamp": {"$gte": datetime.now() - timedelta(days=7)}}},
                    {"$group": {
                        "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "count": {"$sum": 1}
                    }},
                    {"$sort": {"_id": 1}}
                ]
                daily_activity = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=7)
                recent_analytics['daily_activity'] = {item['_id']: item['count'] for item in daily_activity}
                
            except Exception as e:
                logger.warning(f"Error fetching analytics: {e}")
        
        return {
            "content_stats": content_stats,
            "sync_history": sync_history,
            "analytics": recent_analytics,
            "system_status": {
                "database_connected": content_manager.db is not None,
                "last_sync": content_manager.last_sync.isoformat() if content_manager.last_sync else None,
                "uptime": "Running"  # Could be calculated from app start time
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard statistics: {str(e)}")

@admin_router.post("/content/sync")
async def trigger_content_sync(sync_request: SyncRequest, admin_verified: bool = Depends(verify_admin_access)):
    """Trigger content synchronization"""
    try:
        content_manager = await get_content_manager()
        result = await content_manager.sync_content(force=sync_request.force)
        return result
        
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering sync: {str(e)}")

@admin_router.get("/content/search")
async def admin_search_content(
    query: str = Query(..., description="Search query"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    admin_verified: bool = Depends(verify_admin_access)
):
    """Search content with admin privileges"""
    try:
        content_manager = await get_content_manager()
        results = await content_manager.search_content(
            query=query,
            content_type=content_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "query": query,
            "content_type": content_type,
            "total_results": len(results),
            "offset": offset,
            "limit": limit,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in admin search: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@admin_router.get("/content/{content_id}")
async def get_content_details(content_id: str, admin_verified: bool = Depends(verify_admin_access)):
    """Get detailed information about specific content"""
    try:
        content_manager = await get_content_manager()
        content = await content_manager.get_content_by_id(content_id)
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get analytics for this content
        analytics = {}
        if content_manager.db is not None:
            try:
                # View history
                pipeline = [
                    {"$match": {"content_id": content_id}},
                    {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                event_stats = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=None)
                analytics['events'] = {item['_id']: item['count'] for item in event_stats}
                
                # Recent activity
                recent_activity = await content_manager.db.content_analytics.find(
                    {"content_id": content_id}
                ).sort("timestamp", -1).limit(10).to_list(length=10)
                analytics['recent_activity'] = recent_activity
                
            except Exception as e:
                logger.warning(f"Error fetching content analytics: {e}")
        
        return {
            "content": content,
            "analytics": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content details: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching content: {str(e)}")

@admin_router.put("/content/{content_id}")
async def update_content(
    content_id: str, 
    update_request: ContentUpdateRequest,
    admin_verified: bool = Depends(verify_admin_access)
):
    """Update content information"""
    try:
        content_manager = await get_content_manager()
        
        if content_manager.db is None:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Prepare update data
        update_data = {}
        if update_request.title is not None:
            update_data['title'] = update_request.title
        if update_request.content is not None:
            update_data['content'] = update_request.content
        if update_request.content_type is not None:
            update_data['content_type'] = update_request.content_type
        if update_request.is_active is not None:
            update_data['is_active'] = update_request.is_active
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        update_data['last_updated'] = datetime.now()
        
        # Update content
        result = await content_manager.db.content.update_one(
            {"id": content_id},
            {"$set": update_data, "$inc": {"version": 1}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {
            "content_id": content_id,
            "updated": True,
            "modified_fields": list(update_data.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating content: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating content: {str(e)}")

@admin_router.delete("/content/{content_id}")
async def deactivate_content(content_id: str, admin_verified: bool = Depends(verify_admin_access)):
    """Deactivate content (soft delete)"""
    try:
        content_manager = await get_content_manager()
        
        if content_manager.db is None:
            raise HTTPException(status_code=503, detail="Database not available")
        
        result = await content_manager.db.content.update_one(
            {"id": content_id},
            {"$set": {"is_active": False, "last_updated": datetime.now()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return {
            "content_id": content_id,
            "deactivated": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating content: {e}")
        raise HTTPException(status_code=500, detail=f"Error deactivating content: {str(e)}")

@admin_router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, admin_verified: bool = Depends(verify_admin_access)):
    """Submit feedback for content"""
    try:
        content_manager = await get_content_manager()
        
        # Validate feedback score
        if not 1 <= feedback.feedback_score <= 5:
            raise HTTPException(status_code=400, detail="Feedback score must be between 1 and 5")
        
        # Update content feedback
        await content_manager.update_content_feedback(feedback.content_id, feedback.feedback_score)
        
        # Store detailed feedback if database is available
        if content_manager.db is not None and feedback.feedback_text:
            feedback_doc = {
                "content_id": feedback.content_id,
                "feedback_score": feedback.feedback_score,
                "feedback_text": feedback.feedback_text,
                "user_id": feedback.user_id,
                "timestamp": datetime.now()
            }
            await content_manager.db.feedback.insert_one(feedback_doc)
        
        return {
            "content_id": feedback.content_id,
            "feedback_submitted": True,
            "score": feedback.feedback_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@admin_router.get("/analytics/overview")
async def get_analytics_overview(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    admin_verified: bool = Depends(verify_admin_access)
):
    """Get analytics overview for specified time period"""
    try:
        content_manager = await get_content_manager()
        
        if content_manager.db is None:
            return {"message": "Analytics not available - database not connected"}
        
        start_date = datetime.now() - timedelta(days=days)
        
        analytics = {}
        
        # Total events in period
        total_events = await content_manager.db.content_analytics.count_documents({
            "timestamp": {"$gte": start_date}
        })
        analytics['total_events'] = total_events
        
        # Events by type
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$event_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        events_by_type = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=None)
        analytics['events_by_type'] = {item['_id']: item['count'] for item in events_by_type}
        
        # Daily breakdown
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        daily_breakdown = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=days)
        analytics['daily_breakdown'] = daily_breakdown
        
        # Top content by views
        pipeline = [
            {"$match": {"event_type": "view", "timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$content_id", "view_count": {"$sum": 1}}},
            {"$sort": {"view_count": -1}},
            {"$limit": 10}
        ]
        top_content_ids = await content_manager.db.content_analytics.aggregate(pipeline).to_list(length=10)
        
        # Get content details for top content
        top_content = []
        for item in top_content_ids:
            content = await content_manager.get_content_by_id(item['_id'])
            if content:
                top_content.append({
                    "content_id": item['_id'],
                    "title": content.get('title', 'Unknown'),
                    "view_count": item['view_count'],
                    "content_type": content.get('content_type', 'unknown')
                })
        
        analytics['top_content'] = top_content
        
        # Unique sessions
        unique_sessions = len(await content_manager.db.content_analytics.distinct(
            "session_id", 
            {"timestamp": {"$gte": start_date}}
        ))
        analytics['unique_sessions'] = unique_sessions
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.now().isoformat(),
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics overview: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching analytics: {str(e)}")

@admin_router.get("/system/health")
async def get_system_health(admin_verified: bool = Depends(verify_admin_access)):
    """Get system health status"""
    try:
        content_manager = await get_content_manager()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # Database health
        if content_manager.db is not None:
            try:
                # Test database connection
                await content_manager.db.command("ping")
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "message": "Connected and responsive"
                }
            except Exception as e:
                health_status["components"]["database"] = {
                    "status": "unhealthy",
                    "message": f"Database error: {str(e)}"
                }
                health_status["status"] = "degraded"
        else:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": "Not connected"
            }
            health_status["status"] = "degraded"
        
        # Content stats
        try:
            content_stats = await content_manager.get_content_statistics()
            health_status["components"]["content"] = {
                "status": "healthy",
                "total_content": content_stats.get("total_content", 0),
                "recent_content": content_stats.get("recent_content", 0)
            }
        except Exception as e:
            health_status["components"]["content"] = {
                "status": "unhealthy",
                "message": f"Content system error: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # Sync status
        sync_history = await content_manager.get_sync_history(limit=1)
        if sync_history:
            last_sync = sync_history[0]
            health_status["components"]["sync"] = {
                "status": "healthy" if last_sync.get("status") == "completed" else "warning",
                "last_sync": last_sync.get("completed_at", last_sync.get("started_at")),
                "last_status": last_sync.get("status")
            }
        else:
            health_status["components"]["sync"] = {
                "status": "warning",
                "message": "No sync history available"
            }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@admin_router.get("/sync/history")
async def get_sync_history(
    limit: int = Query(20, ge=1, le=100, description="Number of sync records to return"),
    admin_verified: bool = Depends(verify_admin_access)
):
    """Get synchronization history"""
    try:
        content_manager = await get_content_manager()
        sync_history = await content_manager.get_sync_history(limit=limit)
        
        return {
            "sync_history": sync_history,
            "total_records": len(sync_history)
        }
        
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching sync history: {str(e)}")

# Add admin router to main app (this would be done in main.py)
def setup_admin_routes(app):
    """Setup admin routes in the main FastAPI app"""
    app.include_router(admin_router)