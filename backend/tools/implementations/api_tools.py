"""API-specific tools for calling external services."""

import aiohttp
import asyncio
from typing import Dict, Any
from datetime import datetime
from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class WeatherAPITool(BaseTool):
    """Tool for getting weather information from a weather API."""
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "Get current weather information for a city"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name (e.g., 'Tehran', 'New York')"
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units",
                    "enum": ["metric", "imperial"],
                    "default": "metric"
                }
            },
            "required": ["city"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute weather API request."""
        city = kwargs.get("city")
        units = kwargs.get("units", "metric")
        
        if not city:
            return ToolResult(
                success=False,
                output=None,
                error="City name is required"
            )
        
        try:
            # Example: OpenWeatherMap API (you'd need an API key)
            api_key = getattr(settings, "WEATHER_API_KEY", "demo")
            url = f"https://api.openweathermap.org/data/2.5/weather"
            
            params = {
                "q": city,
                "units": units,
                "appid": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract relevant weather info
                        result = {
                            "city": data.get("name", city),
                            "country": data.get("sys", {}).get("country", ""),
                            "temperature": data.get("main", {}).get("temp"),
                            "feels_like": data.get("main", {}).get("feels_like"),
                            "humidity": data.get("main", {}).get("humidity"),
                            "description": data.get("weather", [{}])[0].get("description", ""),
                            "wind_speed": data.get("wind", {}).get("speed"),
                            "units": units
                        }
                        
                        return ToolResult(
                            success=True,
                            output=result,
                            metadata={
                                "timestamp": datetime.now().isoformat(),
                                "api": "OpenWeatherMap"
                            }
                        )
                    else:
                        error_msg = f"API returned status {response.status}"
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("message", error_msg)
                        except:
                            pass
                        
                        return ToolResult(
                            success=False,
                            output=None,
                            error=error_msg
                        )
                        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output=None,
                error="Weather API request timed out"
            )
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to fetch weather: {str(e)}"
            )


class CustomAPITool(BaseTool):
    """
    Generic template for creating custom API tools.
    
    Copy this class and modify it for your specific API.
    """
    
    @property
    def name(self) -> str:
        return "custom_api"  # Change this to your API name
    
    @property
    def description(self) -> str:
        return "Call your custom API endpoint"  # Describe what your API does
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                # Define your API parameters here
                "query": {
                    "type": "string",
                    "description": "Search query or input parameter"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute your custom API request."""
        query = kwargs.get("query")
        limit = kwargs.get("limit", 10)
        
        try:
            # Replace with your actual API endpoint
            api_url = "https://your-api.com/endpoint"
            api_key = getattr(settings, "YOUR_API_KEY", None)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Example: GET request
            params = {
                "q": query,
                "limit": limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    api_url,
                    params=params,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return ToolResult(
                            success=True,
                            output=data,
                            metadata={
                                "timestamp": datetime.now().isoformat(),
                                "query": query
                            }
                        )
                    else:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"API returned status {response.status}"
                        )
                        
        except Exception as e:
            logger.error(f"Custom API error: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"API call failed: {str(e)}"
            )

