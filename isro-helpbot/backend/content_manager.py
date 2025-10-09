"""
Content Manager for ISRO HelpBot
Handles content storage, indexing, and synchronization
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json
import hashlib
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import IndexModel, TEXT, ASCENDING, DESCENDING
from scraper import MOSDACWebScraper, ScrapedContent
import database

logger = logging.getLogger(__name__)

@dataclass
class ContentDocument:
    """Document structure for content storage"""
    id: str
    title: str
    content: str
    url: str
    content_type: str
    meta_tags: Dict[str, str]
    tables: List[Dict]
    links: List[str]
    images: List[str]
    keywords: List[str]
    indexed_at: datetime
    last_updated: datetime
    version: int
    relevance_score: float = 0.0
    view_count: int = 0
    feedback_score: float = 0.0
    is_active: bool = True

class ContentManager:
    """Manages content storage, indexing, and synchronization"""
    
    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.scraper = MOSDACWebScraper()
        self.sync_interval = 3600  # 1 hour in seconds
        self.last_sync = None
        
    async def initialize(self):
        """Initialize database connection and indexes"""
        self.db = await database.connect_to_mongodb()
        if self.db is not None:
            await self.create_indexes()
            logger.info("Content manager initialized")
        else:
            logger.error("Failed to initialize content manager - no database connection")
    
    async def create_indexes(self):
        """Create database indexes for efficient querying"""
        if self.db is None:
            return
        
        try:
            # Content collection indexes
            content_indexes = [
                IndexModel([("id", ASCENDING)], unique=True),
                IndexModel([("url", ASCENDING)], unique=True),
                IndexModel([("content_type", ASCENDING)]),
                IndexModel([("indexed_at", DESCENDING)]),
                IndexModel([("last_updated", DESCENDING)]),
                IndexModel([("relevance_score", DESCENDING)]),
                IndexModel([("is_active", ASCENDING)]),
                # Text index for full-text search
                IndexModel([("title", TEXT), ("content", TEXT), ("keywords", TEXT)]),
                # Compound indexes for common queries
                IndexModel([("content_type", ASCENDING), ("relevance_score", DESCENDING)]),
                IndexModel([("is_active", ASCENDING), ("indexed_at", DESCENDING)])
            ]
            
            await self.db.content.create_indexes(content_indexes)
            
            # Sync history collection
            sync_indexes = [
                IndexModel([("sync_id", ASCENDING)], unique=True),
                IndexModel([("started_at", DESCENDING)]),
                IndexModel([("status", ASCENDING)])
            ]
            
            await self.db.sync_history.create_indexes(sync_indexes)
            
            # Content analytics collection
            analytics_indexes = [
                IndexModel([("content_id", ASCENDING)]),
                IndexModel([("event_type", ASCENDING)]),
                IndexModel([("timestamp", DESCENDING)]),
                IndexModel([("session_id", ASCENDING)])
            ]
            
            await self.db.content_analytics.create_indexes(analytics_indexes)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def extract_keywords(self, content: str, title: str = "") -> List[str]:
        """Extract keywords from content for better searchability"""
        import re
        from collections import Counter
        
        # Combine title and content
        text = f"{title} {content}".lower()
        
        # Remove special characters and extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        
        # Define stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'way', 'will', 'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'
        }
        
        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Get most common keywords
        word_freq = Counter(keywords)
        top_keywords = [word for word, count in word_freq.most_common(20)]
        
        # Add domain-specific keywords
        domain_keywords = []
        if 'satellite' in text:
            domain_keywords.append('satellite')
        if 'data' in text:
            domain_keywords.append('data')
        if 'isro' in text:
            domain_keywords.append('isro')
        if 'mosdac' in text:
            domain_keywords.append('mosdac')
        
        return list(set(top_keywords + domain_keywords))
    
    async def store_content(self, scraped_content: ScrapedContent) -> bool:
        """Store scraped content in database"""
        if self.db is None:
            logger.error("Database not available for content storage")
            return False
        
        try:
            # Extract keywords
            keywords = self.extract_keywords(scraped_content.content, scraped_content.title)
            
            # Create content document
            content_doc = ContentDocument(
                id=scraped_content.id,
                title=scraped_content.title,
                content=scraped_content.content,
                url=scraped_content.url,
                content_type=scraped_content.content_type,
                meta_tags=scraped_content.meta_tags,
                tables=scraped_content.tables,
                links=scraped_content.links,
                images=scraped_content.images,
                keywords=keywords,
                indexed_at=scraped_content.scraped_at,
                last_updated=datetime.now(),
                version=1
            )
            
            # Check if content already exists
            existing = await self.db.content.find_one({"url": scraped_content.url})
            
            if existing:
                # Update existing content if changed
                if existing.get('content') != scraped_content.content:
                    update_data = asdict(content_doc)
                    update_data['version'] = existing.get('version', 1) + 1
                    update_data['last_updated'] = datetime.now()
                    
                    await self.db.content.update_one(
                        {"url": scraped_content.url},
                        {"$set": update_data}
                    )
                    logger.info(f"Updated content: {scraped_content.title}")
                else:
                    logger.info(f"Content unchanged: {scraped_content.title}")
            else:
                # Insert new content
                await self.db.content.insert_one(asdict(content_doc))
                logger.info(f"Stored new content: {scraped_content.title}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing content {scraped_content.url}: {e}")
            return False
    
    async def bulk_store_content(self, scraped_contents: List[ScrapedContent]) -> Dict[str, int]:
        """Store multiple content items efficiently"""
        if self.db is None:
            return {"stored": 0, "updated": 0, "errors": 0}
        
        stored = 0
        updated = 0
        errors = 0
        
        for content in scraped_contents:
            try:
                success = await self.store_content(content)
                if success:
                    stored += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(f"Error in bulk store for {content.url}: {e}")
                errors += 1
        
        logger.info(f"Bulk storage completed: {stored} stored, {updated} updated, {errors} errors")
        return {"stored": stored, "updated": updated, "errors": errors}
    
    async def search_content(self, query: str, content_type: Optional[str] = None, 
                           limit: int = 20, offset: int = 0) -> List[Dict]:
        """Search content in database"""
        if self.db is None:
            return []
        
        try:
            # Build search pipeline
            pipeline = []
            
            # Text search stage
            if query:
                pipeline.append({
                    "$match": {
                        "$text": {"$search": query},
                        "is_active": True
                    }
                })
                
                # Add text score
                pipeline.append({
                    "$addFields": {
                        "text_score": {"$meta": "textScore"}
                    }
                })
            else:
                pipeline.append({
                    "$match": {"is_active": True}
                })
            
            # Filter by content type
            if content_type:
                pipeline.append({
                    "$match": {"content_type": content_type}
                })
            
            # Sort by relevance and text score
            sort_criteria = {}
            if query:
                sort_criteria["text_score"] = {"$meta": "textScore"}
            sort_criteria["relevance_score"] = -1
            sort_criteria["indexed_at"] = -1
            
            pipeline.append({"$sort": sort_criteria})
            
            # Skip and limit
            pipeline.extend([
                {"$skip": offset},
                {"$limit": limit}
            ])
            
            # Execute search
            cursor = self.db.content.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return []
    
    async def get_content_by_id(self, content_id: str) -> Optional[Dict]:
        """Get content by ID"""
        if self.db is None:
            return None
        
        try:
            content = await self.db.content.find_one({"id": content_id})
            return content
        except Exception as e:
            logger.error(f"Error getting content by ID {content_id}: {e}")
            return None
    
    async def update_content_analytics(self, content_id: str, event_type: str, 
                                     session_id: str, metadata: Optional[Dict] = None):
        """Update content analytics"""
        if self.db is None:
            return
        
        try:
            analytics_doc = {
                "content_id": content_id,
                "event_type": event_type,  # view, click, feedback, etc.
                "session_id": session_id,
                "timestamp": datetime.now(),
                "metadata": metadata or {}
            }
            
            await self.db.content_analytics.insert_one(analytics_doc)
            
            # Update content view count if it's a view event
            if event_type == "view":
                await self.db.content.update_one(
                    {"id": content_id},
                    {"$inc": {"view_count": 1}}
                )
            
        except Exception as e:
            logger.error(f"Error updating analytics for {content_id}: {e}")
    
    async def update_content_feedback(self, content_id: str, feedback_score: float):
        """Update content feedback score"""
        if self.db is None:
            return
        
        try:
            # Get current feedback score and calculate new average
            content = await self.db.content.find_one({"id": content_id})
            if content:
                current_score = content.get('feedback_score', 0.0)
                view_count = content.get('view_count', 1)
                
                # Simple weighted average
                new_score = ((current_score * view_count) + feedback_score) / (view_count + 1)
                
                await self.db.content.update_one(
                    {"id": content_id},
                    {"$set": {"feedback_score": new_score}}
                )
                
                logger.info(f"Updated feedback score for {content_id}: {new_score}")
            
        except Exception as e:
            logger.error(f"Error updating feedback for {content_id}: {e}")
    
    async def sync_content(self, force: bool = False) -> Dict[str, Any]:
        """Synchronize content from MOSDAC website"""
        # Check if sync is needed
        if not force and self.last_sync:
            time_since_sync = (datetime.now() - self.last_sync).total_seconds()
            if time_since_sync < self.sync_interval:
                return {
                    "status": "skipped",
                    "message": f"Last sync was {time_since_sync:.0f} seconds ago",
                    "next_sync_in": self.sync_interval - time_since_sync
                }
        
        sync_id = hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()
        start_time = datetime.now()
        
        # Record sync start
        if self.db is not None:
            await self.db.sync_history.insert_one({
                "sync_id": sync_id,
                "started_at": start_time,
                "status": "running",
                "forced": force
            })
        
        try:
            logger.info(f"Starting content sync {sync_id}")
            
            # Scrape website
            scraped_content = await self.scraper.scrape_website(max_pages=100, max_depth=2)
            
            # Store content
            results = await self.bulk_store_content(scraped_content)
            
            # Update sync record
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            sync_result = {
                "sync_id": sync_id,
                "status": "completed",
                "started_at": start_time,
                "completed_at": end_time,
                "duration_seconds": duration,
                "pages_scraped": len(scraped_content),
                "storage_results": results
            }
            
            if self.db is not None:
                await self.db.sync_history.update_one(
                    {"sync_id": sync_id},
                    {"$set": sync_result}
                )
            
            self.last_sync = end_time
            logger.info(f"Content sync {sync_id} completed in {duration:.2f} seconds")
            
            return sync_result
            
        except Exception as e:
            logger.error(f"Error in content sync {sync_id}: {e}")
            
            # Update sync record with error
            if self.db is not None:
                await self.db.sync_history.update_one(
                    {"sync_id": sync_id},
                    {"$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now()
                    }}
                )
            
            return {
                "sync_id": sync_id,
                "status": "failed",
                "error": str(e)
            }
    
    async def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """Get sync history"""
        if self.db is None:
            return []
        
        try:
            cursor = self.db.sync_history.find().sort("started_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return []
    
    async def get_content_statistics(self) -> Dict[str, Any]:
        """Get content statistics"""
        if self.db is None:
            return {}
        
        try:
            stats = {}
            
            # Total content count
            stats['total_content'] = await self.db.content.count_documents({"is_active": True})
            
            # Content by type
            pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {"_id": "$content_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            content_by_type = await self.db.content.aggregate(pipeline).to_list(length=None)
            stats['content_by_type'] = {item['_id']: item['count'] for item in content_by_type}
            
            # Recent content
            stats['recent_content'] = await self.db.content.count_documents({
                "is_active": True,
                "indexed_at": {"$gte": datetime.now() - timedelta(days=7)}
            })
            
            # Total views
            pipeline = [
                {"$match": {"is_active": True}},
                {"$group": {"_id": None, "total_views": {"$sum": "$view_count"}}}
            ]
            view_stats = await self.db.content.aggregate(pipeline).to_list(length=1)
            stats['total_views'] = view_stats[0]['total_views'] if view_stats else 0
            
            # Average feedback score
            pipeline = [
                {"$match": {"is_active": True, "feedback_score": {"$gt": 0}}},
                {"$group": {"_id": None, "avg_feedback": {"$avg": "$feedback_score"}}}
            ]
            feedback_stats = await self.db.content.aggregate(pipeline).to_list(length=1)
            stats['average_feedback'] = feedback_stats[0]['avg_feedback'] if feedback_stats else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting content statistics: {e}")
            return {}

# Global content manager instance
content_manager = ContentManager()

async def initialize_content_manager():
    """Initialize the global content manager"""
    await content_manager.initialize()

# Utility functions for external use
async def get_content_manager() -> ContentManager:
    """Get the global content manager instance"""
    if not content_manager.db:
        await content_manager.initialize()
    return content_manager