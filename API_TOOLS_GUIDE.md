# API Tools Guide

This guide shows you how to use APIs with your AI Agent system.

## Table of Contents

1. [Using the Built-in HTTP Request Tool](#option-1-built-in-http-request-tool)
2. [Creating Custom API Tools](#option-2-custom-api-tools)
3. [Examples](#examples)
4. [Best Practices](#best-practices)

---

## Option 1: Built-in HTTP Request Tool

The system includes a generic `http_request` tool that can call any API.

### Features:

- ✅ All HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD)
- ✅ Custom headers and authentication
- ✅ Query parameters
- ✅ JSON and form data bodies
- ✅ Timeout configuration
- ✅ SSL/TLS support

### Usage Examples:

**Simple GET request:**

```
User: "Call the API at https://api.example.com/users"
Agent: Uses http_request tool with method=GET
```

**POST with JSON body:**

```
User: "POST to https://api.example.com/data with JSON {name: 'test', value: 42}"
Agent: Uses http_request tool with method=POST and JSON body
```

**With headers:**

```
User: "GET https://api.example.com/protected with Authorization: Bearer mytoken"
Agent: Uses http_request tool with custom headers
```

---

## Option 2: Custom API Tools

For frequently used APIs, create dedicated tools for better user experience.

### Benefits:

- 🎯 **Simplified usage**: Users don't need to specify URLs, methods, or headers
- 📝 **Better documentation**: Tool description explains what the API does
- 🔒 **Security**: API keys stored in config, not exposed to users
- ✨ **Better responses**: Format API results in user-friendly way

### Step 1: Create Your API Tool

Create a new file or add to `backend/tools/implementations/api_tools.py`:

```python
from typing import Dict, Any
import aiohttp
from backend.tools.base import BaseTool, ToolPermission, ToolResult

class YourAPITool(BaseTool):
    """Tool for calling your specific API."""

    @property
    def name(self) -> str:
        return "your_api_name"  # e.g., "get_stock_price"

    @property
    def description(self) -> str:
        return "What your API does"  # e.g., "Get real-time stock prices"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "your_param": {
                    "type": "string",
                    "description": "What this parameter does"
                }
            },
            "required": ["your_param"]
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(self, **kwargs) -> ToolResult:
        """Execute API call."""
        param = kwargs.get("your_param")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://your-api.com/endpoint",
                    params={"param": param},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return ToolResult(
                            success=True,
                            output=data
                        )
                    else:
                        return ToolResult(
                            success=False,
                            error=f"API error: {response.status}"
                        )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
```

### Step 2: Register Your Tool

Add to `backend/tools/implementations/__init__.py`:

```python
from .api_tools import YourAPITool

__all__ = [
    # ... existing tools ...
    "YourAPITool"
]
```

### Step 3: Add API Configuration

Add your API keys to `.env` or `backend/config.py`:

```python
# .env
YOUR_API_KEY=your_secret_key_here
```

```python
# backend/config.py
class Settings:
    YOUR_API_KEY: str = os.getenv("YOUR_API_KEY", "")
```

---

## Examples

### Example 1: Weather API Tool

```python
class WeatherAPITool(BaseTool):
    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get current weather for a city"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name"
                }
            },
            "required": ["city"]
        }
```

**Usage:**

```
User: "What's the weather in Tehran?"
Agent: Uses get_weather tool with city="Tehran"
```

### Example 2: Stock Price API

```python
class StockPriceTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_stock_price"

    @property
    def description(self) -> str:
        return "Get real-time stock price"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (e.g., 'AAPL', 'GOOGL')"
                }
            },
            "required": ["symbol"]
        }
```

**Usage:**

```
User: "What's the current price of Apple stock?"
Agent: Uses get_stock_price tool with symbol="AAPL"
```

### Example 3: Translation API

```python
class TranslationAPITool(BaseTool):
    @property
    def name(self) -> str:
        return "translate_text"

    @property
    def description(self) -> str:
        return "Translate text between languages"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to translate"
                },
                "source_lang": {
                    "type": "string",
                    "description": "Source language code"
                },
                "target_lang": {
                    "type": "string",
                    "description": "Target language code"
                }
            },
            "required": ["text", "target_lang"]
        }
```

---

## Best Practices

### 1. Error Handling

Always handle API errors gracefully:

```python
try:
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            return ToolResult(success=True, output=data)
        elif response.status == 401:
            return ToolResult(success=False, error="Authentication failed")
        elif response.status == 429:
            return ToolResult(success=False, error="Rate limit exceeded")
        else:
            return ToolResult(success=False, error=f"API error: {response.status}")
except asyncio.TimeoutError:
    return ToolResult(success=False, error="Request timed out")
except Exception as e:
    return ToolResult(success=False, error=str(e))
```

### 2. Response Formatting

Format API responses to be user-friendly:

```python
# Instead of returning raw API JSON:
return ToolResult(success=True, output=raw_api_response)

# Format it for users:
formatted_result = {
    "summary": "Key information here",
    "details": relevant_data,
    "source": "API Name"
}
return ToolResult(success=True, output=formatted_result)
```

### 3. API Key Security

Never hardcode API keys:

```python
# ❌ BAD
api_key = "sk-1234567890abcdef"

# ✅ GOOD
from backend.config import settings
api_key = settings.YOUR_API_KEY
```

### 4. Timeouts

Always set appropriate timeouts:

```python
async with session.get(url, timeout=10) as response:
    # ... handle response
```

### 5. Logging

Add logging for debugging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Calling API: {url}")
logger.debug(f"Parameters: {params}")
```

### 6. Rate Limiting

Respect API rate limits:

```python
import asyncio

# Add delay between requests if needed
await asyncio.sleep(0.5)
```

---

## Testing Your API Tool

1. **Register the tool** in the system
2. **Grant permission** to users in the database
3. **Test with the agent**:
   ```
   User: "Use [your_tool_name] to [do something]"
   ```

---

## Summary

- **Quick solution**: Use the built-in `http_request` tool for any API
- **Better UX**: Create custom tools for frequently used APIs
- **General approach**: The agent's LLM-based response generator works automatically with any tool
- **No hardcoding**: The system intelligently formats responses based on tool results

Your agent can now call any API, and the general response generation system we implemented will automatically format the results in a user-friendly way! 🎉
