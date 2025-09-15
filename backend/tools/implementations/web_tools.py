"""Web-related tools."""

import aiohttp
import asyncio
from typing import Dict, Any, List
from duckduckgo_search import AsyncDDGS
from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


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
        
        if not settings.ENABLE_WEB_SEARCH:
            return ToolResult(
                success=False,
                output=None,
                error="Web search is disabled in settings"
            )
        
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 5)
        time_range = kwargs.get("time_range", "all")
        
        try:
            # Use DuckDuckGo for privacy-preserving search
            results = await self._search_duckduckgo(query, max_results, time_range)
            
            return ToolResult(
                success=True,
                output=results,
                metadata={
                    "count": len(results),
                    "source": "duckduckgo"
                }
            )
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
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
                
                # Search
                search_results = ddgs.text(
                    query,
                    max_results=max_results,
                    timelimit=timelimit
                )
                
                async for result in search_results:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", ""),
                        "snippet": result.get("body", ""),
                        "source": "duckduckgo"
                    })
        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            
            # Fallback to SearxNG if configured
            if settings.SEARXNG_URL:
                results = await self._search_searxng(query, max_results)
        
        return results
    
    async def _search_searxng(
        self,
        query: str,
        max_results: int
    ) -> List[Dict]:
        """Search using SearxNG instance."""
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": query,
                    "format": "json",
                    "language": "en",
                    "safesearch": 1
                }
                
                async with session.get(
                    f"{settings.SEARXNG_URL}/search",
                    params=params,
                    timeout=settings.WEB_SEARCH_TIMEOUT
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for result in data.get("results", [])[:max_results]:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "snippet": result.get("content", ""),
                                "source": "searxng"
                            })
        
        except Exception as e:
            logger.error(f"SearxNG search error: {e}")
        
        return results
