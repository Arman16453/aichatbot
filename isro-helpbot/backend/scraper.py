"""
Enhanced MOSDAC Web Scraper
Comprehensive scraping of MOSDAC portal for content indexing
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Dict, List, Set, Optional
import re
from datetime import datetime
import logging
import time
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapedContent:
    """Data class for scraped content"""
    id: str
    title: str
    content: str
    url: str
    content_type: str
    meta_tags: Dict[str, str]
    tables: List[Dict]
    links: List[str]
    images: List[str]
    last_modified: Optional[datetime]
    scraped_at: datetime

class MOSDACWebScraper:
    """Enhanced web scraper for MOSDAC portal"""
    
    def __init__(self, base_url: str = "https://www.mosdac.gov.in"):
        self.base_url = base_url
        self.visited_urls: Set[str] = set()
        self.scraped_content: List[ScrapedContent] = []
        self.session = None
        self.rate_limit_delay = 1.0  # seconds between requests
        
        # Define URL patterns to prioritize
        self.priority_patterns = [
            r'/faq',
            r'/help',
            r'/documentation',
            r'/products',
            r'/services',
            r'/tutorials',
            r'/about',
            r'/data',
            r'/catalog'
        ]
        
        # URLs to skip
        self.skip_patterns = [
            r'/download/',
            r'\.pdf$',
            r'\.zip$',
            r'\.tar$',
            r'/login',
            r'/signup',
            r'/register'
        ]
    
    async def create_session(self):
        """Create aiohttp session with proper headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10)
        )
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    def should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped"""
        for pattern in self.skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def get_url_priority(self, url: str) -> int:
        """Get priority score for URL (higher = more important)"""
        priority = 0
        for i, pattern in enumerate(self.priority_patterns):
            if re.search(pattern, url, re.IGNORECASE):
                priority += (len(self.priority_patterns) - i) * 10
        return priority
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single page with error handling"""
        try:
            if not self.session:
                await self.create_session()
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info(f"Successfully fetched: {url}")
                    return content
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags from HTML"""
        meta_tags = {}
        
        # Standard meta tags
        for tag in soup.find_all('meta'):
            name = tag.get('name') or tag.get('property') or tag.get('http-equiv')
            content = tag.get('content')
            if name and content:
                meta_tags[name.lower()] = content
        
        # Title tag
        title_tag = soup.find('title')
        if title_tag:
            meta_tags['title'] = title_tag.get_text().strip()
        
        return meta_tags
    
    def extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract table data from HTML"""
        tables_data = []
        
        for table in soup.find_all('table'):
            table_data = {
                'headers': [],
                'rows': [],
                'caption': ''
            }
            
            # Extract caption
            caption = table.find('caption')
            if caption:
                table_data['caption'] = caption.get_text().strip()
            
            # Extract headers
            header_row = table.find('tr')
            if header_row:
                headers = header_row.find_all(['th', 'td'])
                table_data['headers'] = [h.get_text().strip() for h in headers]
            
            # Extract rows
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text().strip() for cell in cells]
                if row_data:  # Only add non-empty rows
                    table_data['rows'].append(row_data)
            
            if table_data['headers'] or table_data['rows']:
                tables_data.append(table_data)
        
        return tables_data
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links from HTML"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                if base_url in href:  # Internal link
                    links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(base_url, href))
        
        return list(set(links))  # Remove duplicates
    
    def extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from HTML"""
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            elif src.startswith('/'):
                images.append(urljoin(base_url, src))
        
        return images
    
    def clean_content(self, soup: BeautifulSoup) -> str:
        """Extract and clean main content from HTML"""
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            tag.decompose()
        
        # Look for main content containers
        content_selectors = [
            'main',
            'article',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.post-content',
            '.entry-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body') or soup
        
        # Extract text content
        text = main_content.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    def generate_content_id(self, url: str) -> str:
        """Generate unique content ID from URL"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
    
    async def scrape_page(self, url: str) -> Optional[ScrapedContent]:
        """Scrape a single page and extract content"""
        if url in self.visited_urls or self.should_skip_url(url):
            return None
        
        self.visited_urls.add(url)
        
        # Fetch page content
        html_content = await self.fetch_page(url)
        if not html_content:
            return None
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract content
        title = soup.find('title')
        title_text = title.get_text().strip() if title else url.split('/')[-1]
        
        content = self.clean_content(soup)
        meta_tags = self.extract_meta_tags(soup)
        tables = self.extract_tables(soup)
        links = self.extract_links(soup, self.base_url)
        images = self.extract_images(soup, self.base_url)
        
        # Determine content type
        content_type = "webpage"
        if "/faq" in url.lower():
            content_type = "faq"
        elif "/doc" in url.lower():
            content_type = "documentation"
        elif "/product" in url.lower():
            content_type = "product"
        elif "/service" in url.lower():
            content_type = "service"
        
        # Create content object
        scraped_content = ScrapedContent(
            id=self.generate_content_id(url),
            title=title_text,
            content=content,
            url=url,
            content_type=content_type,
            meta_tags=meta_tags,
            tables=tables,
            links=links,
            images=images,
            last_modified=None,  # Could be extracted from headers
            scraped_at=datetime.now()
        )
        
        logger.info(f"Scraped: {title_text} ({len(content)} chars)")
        return scraped_content
    
    async def discover_urls(self, start_url: str, max_depth: int = 2) -> List[str]:
        """Discover URLs to scrape"""
        discovered_urls = set([start_url])
        current_urls = [start_url]
        
        for depth in range(max_depth):
            next_urls = []
            
            for url in current_urls:
                html_content = await self.fetch_page(url)
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    links = self.extract_links(soup, self.base_url)
                    
                    for link in links:
                        if link not in discovered_urls and not self.should_skip_url(link):
                            discovered_urls.add(link)
                            next_urls.append(link)
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
            
            current_urls = next_urls
            if not current_urls:
                break
            
            logger.info(f"Depth {depth + 1}: Found {len(next_urls)} new URLs")
        
        # Sort by priority
        url_list = list(discovered_urls)
        url_list.sort(key=self.get_url_priority, reverse=True)
        
        return url_list
    
    async def scrape_website(self, max_pages: int = 100, max_depth: int = 2) -> List[ScrapedContent]:
        """Main scraping method"""
        logger.info(f"Starting scrape of {self.base_url}")
        
        try:
            # Discover URLs
            urls = await self.discover_urls(self.base_url, max_depth)
            logger.info(f"Discovered {len(urls)} URLs to scrape")
            
            # Limit to max_pages
            urls = urls[:max_pages]
            
            # Scrape pages
            scraped_content = []
            for i, url in enumerate(urls):
                content = await self.scrape_page(url)
                if content:
                    scraped_content.append(content)
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                # Progress update
                if (i + 1) % 10 == 0:
                    logger.info(f"Scraped {i + 1}/{len(urls)} pages")
            
            logger.info(f"Scraping completed. {len(scraped_content)} pages scraped.")
            return scraped_content
            
        finally:
            await self.close_session()
    
    def save_to_json(self, filename: str):
        """Save scraped content to JSON file"""
        data = []
        for content in self.scraped_content:
            data.append({
                'id': content.id,
                'title': content.title,
                'content': content.content,
                'url': content.url,
                'content_type': content.content_type,
                'meta_tags': content.meta_tags,
                'tables': content.tables,
                'links': content.links,
                'images': content.images,
                'scraped_at': content.scraped_at.isoformat()
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(data)} items to {filename}")

# Example usage
async def main():
    scraper = MOSDACWebScraper()
    scraped_content = await scraper.scrape_website(max_pages=50, max_depth=2)
    
    # Save to JSON
    scraper.scraped_content = scraped_content
    scraper.save_to_json('mosdac_content.json')
    
    return scraped_content

if __name__ == "__main__":
    asyncio.run(main())