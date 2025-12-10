"""Web-related tools."""

import aiohttp
import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime
from duckduckgo_search import DDGS
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
            
            # Run synchronous DDGS in a thread pool to make it async-compatible
            def _sync_search():
                """Synchronous search function to run in thread pool."""
                ddgs = DDGS()
                search_results = ddgs.text(
                    query,
                    max_results=max_results,
                    timelimit=timelimit
                )
                # DDGS.text() returns a list, not an iterator
                return search_results if search_results else []
            
            # Execute the synchronous search in a thread pool
            search_results = await asyncio.to_thread(_sync_search)
            
            logger.debug(f"DuckDuckGo search_results type: {type(search_results)}")
            logger.debug(f"DuckDuckGo search found {len(search_results) if search_results else 0} results")
            
            # Process results
            if search_results:
                for result in search_results[:max_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", result.get("link", "")),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo"
                    })
                    logger.debug(f"DuckDuckGo result: {result}")
            
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
        
        # Validate URL is provided
        if not url:
            return ToolResult(
                success=False,
                output=None,
                error="URL is required for web scraping"
            )
        
        # Ensure URL is a string
        if not isinstance(url, str):
            return ToolResult(
                success=False,
                output=None,
                error="URL must be a string"
            )
        
        try:
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
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
                    logger.debug(f"Scraped content length: {len(content)}")
                    logger.debug(f"Content preview: {content[:500]}...")
                    
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    result = {
                        "url": url,
                        "title": soup.title.string if soup.title else "No title",
                        "status_code": response.status,
                        "content_length": len(content)
                    }
                    
                    if extract_type in ["text", "all"]:
                        # Extract text content with improved logic
                        text = ""
                        
                        # Try to find main content areas first
                        main_selectors = [
                            'main', 'article', '[role="main"]', 
                            '.main-content', '.content', '.post-content',
                            '#main', '#content', '#main-content'
                        ]
                        
                        main_content = None
                        for selector in main_selectors:
                            main_content = soup.select_one(selector)
                            if main_content:
                                logger.debug(f"Found main content using selector: {selector}")
                                break
                        
                        if main_content:
                            text = main_content.get_text()
                        else:
                            # Fallback to full page text
                            text = soup.get_text()
                        
                        # Clean up the text
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = ' '.join(chunk for chunk in chunks if chunk)
                        
                        logger.debug(f"Extracted text length: {len(text)}")
                        logger.debug(f"Text preview: {text[:200]}...")
                        
                        if len(text) > max_length:
                            text = text[:max_length] + "... [truncated]"
                        
                        result["text"] = text
                        result["text_length"] = len(text)
                        
                        # If we got very little text, provide debugging info
                        if len(text) < 100:
                            result["debug_info"] = {
                                "raw_html_length": len(content),
                                "soup_text_length": len(soup.get_text()),
                                "found_main_content": main_content is not None,
                                "title_found": soup.title is not None,
                                "body_found": soup.body is not None
                            }
                    
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


class HttpRequestTool(BaseTool):
    """Generic HTTP request tool for connecting to external services/APIs."""
    
    @property
    def name(self) -> str:
        return "http_request"
    
    @property
    def description(self) -> str:
        return "Send HTTP requests (GET, POST, PUT, DELETE) to any URL with headers and body"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
                    "default": "GET"
                },
                "url": {
                    "type": "string",
                    "description": "Request URL"
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers as key/value",
                    "default": {}
                },
                "params": {
                    "type": "object",
                    "description": "Query string parameters",
                    "default": {}
                },
                "json": {
                    "type": "object",
                    "description": "JSON body for POST/PUT/PATCH",
                    "default": None
                },
                "data": {
                    "type": "object",
                    "description": "Form body as key/value",
                    "default": None
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": max(5, min(60, settings.WEB_SEARCH_TIMEOUT if hasattr(settings, 'WEB_SEARCH_TIMEOUT') else 10))
                },
                "allow_insecure": {
                    "type": "boolean",
                    "description": "Allow insecure SSL (not recommended)",
                    "default": False
                }
            },
            "required": ["url"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute an HTTP request with aiohttp."""
        method = (kwargs.get("method") or "GET").upper()
        url = kwargs.get("url")
        headers = kwargs.get("headers") or {}
        params = kwargs.get("params") or {}
        json_body = kwargs.get("json")
        data_body = kwargs.get("data")
        timeout = int(kwargs.get("timeout", 10))
        allow_insecure = bool(kwargs.get("allow_insecure", False))
        
        if not url or not isinstance(url, str):
            return ToolResult(success=False, output=None, error="A valid 'url' is required")
        
        # Normalize URL (prepend https if scheme missing)
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            ssl_context = False if allow_insecure else None
            timeout_cfg = aiohttp.ClientTimeout(total=max(1, min(120, timeout)))
            async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    data=data_body,
                    ssl=ssl_context
                ) as response:
                    content_type = response.headers.get("Content-Type", "")
                    status = response.status
                    text = await response.text()
                    
                    output: Dict[str, Any] = {
                        "url": str(response.url),
                        "status": status,
                        "headers": dict(response.headers),
                        "ok": 200 <= status < 300
                    }
                    
                    # Try to parse JSON when applicable
                    if "application/json" in content_type.lower():
                        try:
                            output["json"] = await response.json()
                        except Exception:
                            output["text"] = text[:5000]
                    else:
                        output["text"] = text[:5000]
                    
                    return ToolResult(
                        success=200 <= status < 300,
                        output=output,
                        error=None if 200 <= status < 300 else f"HTTP {status}",
                        metadata={
                            "timestamp": datetime.now().isoformat(),
                            "method": method
                        }
                    )
        except asyncio.TimeoutError:
            return ToolResult(success=False, output=None, error="Request timeout")
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return ToolResult(success=False, output=None, error=str(e))