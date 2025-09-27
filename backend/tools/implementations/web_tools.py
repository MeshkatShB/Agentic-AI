"""Web-related tools."""

import aiohttp
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime
from duckduckgo_search import AsyncDDGS
from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG level


class WebSearchTool(BaseTool):
    """Tool for searching the web."""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for information (requires permission)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for results",
                    "enum": ["day", "week", "month", "year", "all"],
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute web search."""
        
        logger.debug(f"Web search called with kwargs: {kwargs}")
        logger.debug(f"Web search enabled: {settings.ENABLE_WEB_SEARCH}")
        logger.debug(f"SearxNG URL: {settings.SEARXNG_URL}")
        
        if not settings.ENABLE_WEB_SEARCH:
            return ToolResult(
                success=False,
                output=None,
                error="Web search is disabled in settings"
            )
        
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 5)
        time_range = kwargs.get("time_range", "all")
        
        if not query:
            return ToolResult(
                success=False,
                output=None,
                error="No search query provided"
            )
        
        try:
            # SearxNG is now working, use it as primary source
            results = []
            if settings.SEARXNG_URL:
                logger.debug("Using SearxNG for search...")
                results = await self._search_searxng(query, max_results)
                
                # Fall back to DuckDuckGo if SearxNG returns no results
                if not results:
                    logger.debug("SearxNG returned no results, falling back to DuckDuckGo...")
                    results = await self._search_duckduckgo(query, max_results, time_range)
            else:
                logger.debug("SearxNG not configured, using DuckDuckGo...")
                results = await self._search_duckduckgo(query, max_results, time_range)
            
            logger.debug(f"Final search results count: {len(results)}")
            logger.debug(f"Search results: {results}")
            
            # Determine actual source used
            actual_source = "duckduckgo"
            if results:
                actual_source = results[0].get("source", "duckduckgo")
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    "count": len(results),
                    "source": actual_source,
                    "query": query
                }
            )
            
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    async def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        time_range: str
    ) -> List[Dict]:
        """Search using DuckDuckGo."""
        
        results = []
        
        try:
            async with AsyncDDGS() as ddgs:
                # Convert time range
                timelimit = None
                if time_range == "day":
                    timelimit = "d"
                elif time_range == "week":
                    timelimit = "w"
                elif time_range == "month":
                    timelimit = "m"
                elif time_range == "year":
                    timelimit = "y"
                
                logger.debug(f"DuckDuckGo search params: query={query}, max_results={max_results}, timelimit={timelimit}")
                
                # Search
                try:
                    search_results = ddgs.text(
                        query,
                        max_results=max_results,
                        timelimit=timelimit
                    )
                    
                    logger.debug(f"DuckDuckGo search_results type: {type(search_results)}")
                    
                    # Handle both async and sync iterators
                    if hasattr(search_results, '__aiter__'):
                        async for result in search_results:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", result.get("link", "")),
                                "snippet": result.get("body", ""),
                                "source": "duckduckgo"
                            })
                            logger.debug(f"DuckDuckGo result: {result}")
                            if len(results) >= max_results:
                                break
                    else:
                        # Handle as regular list/iterator
                        for result in search_results:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", result.get("link", "")),
                                "snippet": result.get("body", ""),
                                "source": "duckduckgo"
                            })
                            logger.debug(f"DuckDuckGo result: {result}")
                            if len(results) >= max_results:
                                break
                except Exception as search_error:
                    logger.error(f"DuckDuckGo search iteration error: {search_error}")
                    # Try alternative approach
                    try:
                        search_results = list(ddgs.text(query, max_results=max_results, timelimit=timelimit))
                        logger.debug(f"DuckDuckGo alternative search found {len(search_results)} results")
                        for result in search_results[:max_results]:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", result.get("link", "")),
                                "snippet": result.get("body", ""),
                                "source": "duckduckgo"
                            })
                    except Exception as alt_error:
                        logger.error(f"DuckDuckGo alternative search failed: {alt_error}")
                
                logger.debug(f"DuckDuckGo search completed with {len(results)} results")
        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}", exc_info=True)
            
            # Only fall back to SearxNG if DuckDuckGo fails with an error
            if settings.SEARXNG_URL:
                logger.debug("Falling back to SearxNG due to DuckDuckGo error")
                results = await self._search_searxng(query, max_results)
        
        return results
    
    async def _search_searxng(
        self,
        query: str,
        max_results: int
    ) -> List[Dict]:
        """Search using SearxNG instance with HTML parsing fallback."""
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # First try JSON format
                params_json = {
                    "q": query,
                    "format": "json",
                    "language": "auto",
                    "safesearch": "0",
                    "categories": "general"
                }
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/html, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": settings.SEARXNG_URL
                }
                
                logger.debug(f"SearxNG search: {settings.SEARXNG_URL}/search with query: {query}")
                
                # Try JSON first
                try:
                    async with session.get(
                        f"{settings.SEARXNG_URL}/search",
                        params=params_json,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=settings.WEB_SEARCH_TIMEOUT)
                    ) as response:
                        logger.debug(f"SearxNG JSON response status: {response.status}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                search_results = data.get("results", [])
                                
                                logger.debug(f"SearxNG JSON returned {len(search_results)} results")
                                
                                for result in search_results[:max_results]:
                                    title = result.get("title", "")
                                    url = result.get("url", "")
                                    snippet = result.get("content", "")
                                    
                                    if title and url:
                                        results.append({
                                            "title": title,
                                            "url": url,
                                            "snippet": snippet,
                                            "source": "searxng"
                                        })
                                return results
                                        
                            except json.JSONDecodeError:
                                logger.debug("Failed to parse JSON, will try HTML parsing")
                        else:
                            logger.debug(f"JSON request failed with {response.status}, will try HTML parsing")
                except Exception as e:
                    logger.debug(f"JSON request failed: {e}, will try HTML parsing")
                
                # Fallback to HTML parsing
                logger.debug("Falling back to HTML parsing")
                params_html = {
                    "q": query,
                    "language": "auto",
                    "safesearch": "0",
                    "categories": "general"
                }
                
                async with session.get(
                    f"{settings.SEARXNG_URL}/search",
                    params=params_html,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=settings.WEB_SEARCH_TIMEOUT)
                ) as response:
                    logger.debug(f"SearxNG HTML response status: {response.status}")
                    
                    if response.status == 200:
                        html_content = await response.text()
                        results = self._parse_searxng_html(html_content, max_results)
                        logger.debug(f"SearxNG HTML parsing returned {len(results)} results")
                    else:
                        response_text = await response.text()
                        logger.error(f"SearxNG HTML error {response.status}: {response_text[:500]}")
        
        except Exception as e:
            logger.error(f"SearxNG search failed: {str(e)}")
        
        logger.debug(f"SearxNG search completed with {len(results)} results")
        return results
    
    def _parse_searxng_html(self, html_content: str, max_results: int) -> List[Dict]:
        """Parse SearxNG HTML response to extract search results."""
        results = []
        
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find result containers - SearxNG typically uses div.result or article
            result_containers = soup.find_all(['div', 'article'], class_=lambda x: x and ('result' in x.lower() or 'search-result' in x.lower()))
            
            if not result_containers:
                # Try alternative selectors
                result_containers = soup.find_all('div', class_=lambda x: x and 'result' in str(x).lower())
            
            logger.debug(f"Found {len(result_containers)} result containers in HTML")
            
            for container in result_containers[:max_results]:
                try:
                    # Extract title
                    title_elem = container.find(['h3', 'h2', 'h1', 'a'], class_=lambda x: x and ('title' in str(x).lower() or 'heading' in str(x).lower()))
                    if not title_elem:
                        title_elem = container.find('a')
                    
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    # Extract URL
                    url_elem = title_elem if title_elem and title_elem.name == 'a' else container.find('a')
                    url = url_elem.get('href', '') if url_elem else ""
                    
                    # Extract snippet/description
                    snippet_elem = container.find(['p', 'div'], class_=lambda x: x and ('content' in str(x).lower() or 'snippet' in str(x).lower() or 'description' in str(x).lower()))
                    if not snippet_elem:
                        # Try to find any paragraph or div with text
                        snippet_elem = container.find(['p', 'div'], string=lambda text: text and len(text.strip()) > 20)
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source": "searxng"
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing result container: {e}")
                    continue
                    
        except ImportError:
            logger.error("BeautifulSoup not available for HTML parsing")
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
        
        return results


class WebScrapeTool(BaseTool):
    """Tool for scraping web pages."""
    
    @property
    def name(self) -> str:
        return "scrape_webpage"
    
    @property
    def description(self) -> str:
        return "Scrape and extract content from web pages"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to scrape"
                },
                "extract_type": {
                    "type": "string",
                    "description": "Type of content to extract",
                    "enum": ["text", "links", "images", "all"],
                    "default": "text"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length of extracted text",
                    "default": 5000,
                    "minimum": 100,
                    "maximum": 50000
                }
            },
            "required": ["url"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.WEB_ACCESS
    
    async def execute(self, **kwargs) -> ToolResult:
        """Scrape webpage content."""
        url = kwargs.get("url")
        extract_type = kwargs.get("extract_type", "text")
        max_length = kwargs.get("max_length", 5000)
        
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"HTTP {response.status}: {response.reason}"
                        )
                    
                    content = await response.text()
                    
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    result = {
                        "url": url,
                        "title": soup.title.string if soup.title else "No title",
                        "status_code": response.status
                    }
                    
                    if extract_type in ["text", "all"]:
                        # Extract text content
                        text = soup.get_text()
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        if len(text) > max_length:
                            text = text[:max_length] + "... [truncated]"
                        
                        result["text"] = text
                        result["text_length"] = len(text)
                    
                    if extract_type in ["links", "all"]:
                        # Extract links
                        links = []
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('http'):
                                links.append({
                                    "url": href,
                                    "text": link.get_text(strip=True)
                                })
                        result["links"] = links[:50]  # Limit to 50 links
                        result["links_count"] = len(links)
                    
                    if extract_type in ["images", "all"]:
                        # Extract images
                        images = []
                        for img in soup.find_all('img', src=True):
                            src = img['src']
                            if src.startswith('http') or src.startswith('//'):
                                images.append({
                                    "src": src,
                                    "alt": img.get('alt', ''),
                                    "title": img.get('title', '')
                                })
                        result["images"] = images[:20]  # Limit to 20 images
                        result["images_count"] = len(images)
                    
                    return ToolResult(
                        success=True,
                        output=result,
                        metadata={
                            "extract_type": extract_type,
                            "content_length": len(content),
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error="Request timeout - webpage took too long to respond"
            )
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Scraping failed: {str(e)}"
            )