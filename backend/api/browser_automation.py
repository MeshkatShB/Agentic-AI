"""Browser-use API endpoints.

This module provides browser automation using browser-use library with:
- User's own LLM models (Ollama, OpenAI, DeepSeek, Mistral, Gemini) - NO ChatBrowserUse, NO cloud APIs
- Local browser instances only - NO cloud browsers
- Native browser-use LLM classes (no LangChain dependencies)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
import asyncio
import os

from backend.models import get_db, User
from backend.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_api_config(current_user: User) -> dict:
    """Get user's API configuration."""
    from backend.config import settings as app_settings
    
    prefs = current_user.preferences or {}
    api_config = prefs.get("api_config", {})
    
    def get_api_key(key_name: str, env_key: str) -> Optional[str]:
        user_key = api_config.get(key_name)
        if user_key:
            return user_key
        env_key_value = getattr(app_settings, env_key, None)
        if env_key_value:
            return env_key_value
        return None
    
    # Build API config dict
    config = {
        "llm_provider": api_config.get("llm_provider", "ollama"),
        "openai_api_key": get_api_key("openai_api_key", "OPENAI_API_KEY"),
        "openai_api_endpoint": api_config.get("openai_api_endpoint", "https://api.openai.com/v1"),
        "openai_model": api_config.get("openai_model", "gpt-4o-mini"),
        "deepseek_api_key": get_api_key("deepseek_api_key", "DEEPSEEK_API_KEY"),
        "deepseek_api_endpoint": api_config.get("deepseek_api_endpoint", "https://api.deepseek.com/v1"),
        "deepseek_model": api_config.get("deepseek_model", "deepseek-chat"),
        "mistral_api_key": get_api_key("mistral_api_key", "MISTRAL_API_KEY"),
        "mistral_api_endpoint": api_config.get("mistral_api_endpoint", "https://api.mistral.ai/v1"),
        "mistral_model": api_config.get("mistral_model", "mistral-small"),
        "gemini_api_key": get_api_key("gemini_api_key", "GEMINI_API_KEY"),
        "gemini_api_endpoint": api_config.get("gemini_api_endpoint", "https://generativelanguage.googleapis.com/v1"),
        "gemini_model": api_config.get("gemini_model", "gemini-pro"),
    }
    
    return config


@router.post("/execute")
async def execute_browser_task(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Execute a browser task using browser-use with local browser and user's LLM model."""
    
    try:
        from browser_use import Agent, Browser, ChatOpenAI, ChatOllama, ChatMistral, ChatGoogle
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="browser-use package is not installed. Please install it with: pip install browser-use"
        )
    
    # Parse request body
    body = await request.json()
    task = body.get("task", "")
    stream = body.get("stream", True)
    
    async def generate():
        """Generate streaming response."""
        browser = None
        # CRITICAL: Unset BROWSER_USE_API_KEY to prevent cloud browser usage (exactly like test.py)
        # Save original value if it exists
        original_browser_use_key = os.environ.pop("BROWSER_USE_API_KEY", None)
        # Also explicitly delete it to be absolutely sure
        if "BROWSER_USE_API_KEY" in os.environ:
            del os.environ["BROWSER_USE_API_KEY"]
        
        # Verify it's unset
        if "BROWSER_USE_API_KEY" in os.environ:
            logger.warning("BROWSER_USE_API_KEY still exists after deletion attempt!")
        else:
            logger.info("BROWSER_USE_API_KEY successfully unset - using local browser only")
        
        try:
            # Get user's API configuration
            api_config = await get_user_api_config(current_user)
            user_preferences = current_user.preferences or {}
            provider = api_config.get("llm_provider", "ollama")
            
            # Create LLM using browser-use's native classes (like test.py)
            if provider == "openai":
                model_name = api_config.get("openai_model", "gpt-4o-mini")
                api_key = api_config.get("openai_api_key")
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key
                llm = ChatOpenAI(model=model_name)
            elif provider == "ollama":
                from backend.config import settings
                if user_preferences:
                    model_name = user_preferences.get("model") or api_config.get("ollama_model") or settings.DEFAULT_MODEL or "llama3.2"
                else:
                    model_name = api_config.get("ollama_model") or settings.DEFAULT_MODEL or "llama3.2"
                llm = ChatOllama(model=model_name)
            elif provider == "mistral":
                model_name = api_config.get("mistral_model", "mistral-small")
                api_key = api_config.get("mistral_api_key")
                if api_key:
                    os.environ["MISTRAL_API_KEY"] = api_key
                llm = ChatMistral(model=model_name)
            elif provider == "gemini":
                model_name = api_config.get("gemini_model", "gemini-pro")
                api_key = api_config.get("gemini_api_key")
                if api_key:
                    os.environ["GEMINI_API_KEY"] = api_key
                llm = ChatGoogle(model=model_name)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            
            # Create browser (local only) with better settings (exactly like test.py)
            # CRITICAL: Double-check BROWSER_USE_API_KEY is unset before Browser creation
            if "BROWSER_USE_API_KEY" in os.environ:
                logger.warning("BROWSER_USE_API_KEY found before Browser creation - unsetting")
                del os.environ["BROWSER_USE_API_KEY"]
            
            # CRITICAL: Explicitly set cloud-related params to None to prevent cloud mode
            browser = Browser(
                use_cloud=False,  # Force local browser
                cloud_browser=False,  # Explicitly disable cloud browser
                cloud_browser_params=None,  # Explicitly set to None
                cloud_profile_id=None,  # Explicitly set to None
                cloud_proxy_country_code=None,  # Explicitly set to None
                cloud_timeout=None,  # Explicitly set to None
                headless=False,
                keep_alive=True,
                minimum_wait_page_load_time=3.0,  # Wait longer for page to load
                wait_for_network_idle_page_load_time=5.0,  # Wait longer for network to be idle
                wait_between_actions=2.0,  # Wait longer between actions
                cross_origin_iframes=False,  # Disable cross-origin iframes to avoid frame errors
                max_iframes=5,  # Limit iframes to avoid complexity
                max_iframe_depth=2,  # Limit iframe depth
            )
            logger.info("Browser created successfully with use_cloud=False")
            
            # Create agent with configuration (matching test.py)
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
                max_failures=10,  # Allow more retries
                page_extraction_llm=llm,  # Use same LLM for page extraction (critical!)
                llm_timeout=120,  # Longer timeout for LLM calls
                step_timeout=180,  # Longer timeout for each step
                max_history_items=None,  # Keep all history
                use_vision=False,  # Disable vision first to see if that's causing issues
                directly_open_url=True,  # Directly open URLs found in task
            )
            
            # Stream agent execution
            if stream:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Starting browser task with local browser...'})}\n\n"
                
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Initializing local browser...'})}\n\n"
                    
                    # Add a delay to ensure browser is fully initialized
                    await asyncio.sleep(2)
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Browser ready. Running task...'})}\n\n"
                    
                    try:
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Waiting for page to fully load...'})}\n\n"
                        await asyncio.sleep(5)
                        
                        # CRITICAL: Ensure BROWSER_USE_API_KEY is still unset before agent.run()
                        # Browser-use checks this during session start (agent.run())
                        if "BROWSER_USE_API_KEY" in os.environ:
                            logger.warning("BROWSER_USE_API_KEY found before agent.run() - unsetting again")
                            del os.environ["BROWSER_USE_API_KEY"]
                        
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Running agent task...'})}\n\n"
                        history = await agent.run()
                    except Exception as agent_error:
                        logger.error(f"Agent execution error: {agent_error}")
                        error_msg = str(agent_error)
                        
                        # Provide specific error messages
                        if "cloud" in error_msg.lower() and ("api_key" in error_msg.lower() or "authentication" in error_msg.lower() or "forbidden" in error_msg.lower() or "subscription" in error_msg.lower()):
                            logger.error("Cloud browser error occurred despite use_cloud=False")
                            yield f"data: {json.dumps({'type': 'error', 'message': 'Browser initialization failed. Please ensure Chromium is installed locally: uvx browser-use install'})}\n\n"
                        elif "items" in error_msg.lower():
                            yield f"data: {json.dumps({'type': 'status', 'message': 'Agent failed to parse page elements. This may be due to page complexity or slow loading...'})}\n\n"
                        elif "timeout" in error_msg.lower() or "Navigation failed" in error_msg:
                            yield f"data: {json.dumps({'type': 'status', 'message': 'Navigation timeout occurred. The page may be taking too long to load...'})}\n\n"
                        elif "detached" in error_msg.lower() or "unstable" in error_msg.lower():
                            yield f"data: {json.dumps({'type': 'status', 'message': 'Browser session became unstable...'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'status', 'message': f'Agent error: {error_msg[:100]}...'})}\n\n"
                        await asyncio.sleep(5)
                        raise
                    
                    # Parse history to extract useful information
                    history_str = str(history) if history else "No history recorded"
                    
                    history_details = []
                    if hasattr(history, 'all_results'):
                        for i, result in enumerate(history.all_results, 1):
                            result_info = {
                                "step": i,
                                "success": result.success if hasattr(result, 'success') else None,
                                "error": result.error if hasattr(result, 'error') else None,
                                "judgement": result.judgement if hasattr(result, 'judgement') else None,
                            }
                            if result_info["error"]:
                                error_msg = result_info["error"]
                                yield f"data: {json.dumps({'type': 'browser_action', 'action': f'Step {i} error: {error_msg}'})}\n\n"
                            history_details.append(result_info)
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Processing results...'})}\n\n"
                    
                    # Determine if task was successful
                    task_success = True
                    error_messages = []
                    
                    if history_details:
                        for detail in history_details:
                            if detail.get("error"):
                                task_success = False
                                error_msg = detail['error']
                                if error_msg == "items":
                                    error_messages.append(
                                        f"Step {detail['step']}: Failed to parse page elements. "
                                        "This may be due to page complexity or loading issues."
                                    )
                                else:
                                    error_messages.append(f"Step {detail['step']}: {error_msg}")
                    
                    # Stream final result
                    if task_success:
                        final_result = {
                            "type": "complete",
                            "message": "Task completed successfully",
                            "history": history_str,
                            "details": history_details if history_details else None
                        }
                    else:
                        final_result = {
                            "type": "complete",
                            "message": "Task completed with errors",
                            "history": history_str,
                            "details": history_details if history_details else None,
                            "errors": error_messages
                        }
                    yield f"data: {json.dumps(final_result)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Browser task execution error: {e}", exc_info=True)
                    error_message = str(e)
                    error_traceback = None
                    if hasattr(e, '__traceback__'):
                        import traceback
                        error_traceback = traceback.format_exc()
                    
                    error_data = {
                        "type": "error",
                        "error": error_message,
                        "traceback": error_traceback
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            else:
                # Non-streaming execution
                yield f"data: {json.dumps({'type': 'status', 'message': 'Running task...'})}\n\n"
                history = await agent.run()
                result = {
                    "type": "complete",
                    "message": "Task completed",
                    "history": str(history) if history else "No history"
                }
                yield f"data: {json.dumps(result)}\n\n"
                
        except Exception as e:
            logger.error(f"Browser task error: {e}", exc_info=True)
            error_message = str(e)
            
            # Provide better error messages
            if "cloud" in error_message.lower() and ("api_key" in error_message.lower() or "authentication" in error_message.lower() or "forbidden" in error_message.lower() or "subscription" in error_message.lower()):
                error_message = "Browser initialization error. Please ensure Chromium is installed locally. Run: uvx browser-use install"
            
            error_data = {
                "type": "error",
                "error": error_message
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            # Cleanup browser
            if browser:
                try:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Task finished. Browser will stay open for 10 seconds...'})}\n\n"
                    await asyncio.sleep(10)
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Closing browser...'})}\n\n"
                    
                    if hasattr(browser, 'close'):
                        await browser.close()
                    elif hasattr(browser, 'quit'):
                        await browser.quit()
                    elif hasattr(browser, 'stop'):
                        await browser.stop()
                except Exception as close_error:
                    logger.warning(f"Error closing browser: {close_error}")
                    pass
            
            # Restore original BROWSER_USE_API_KEY if it existed
            if original_browser_use_key:
                os.environ["BROWSER_USE_API_KEY"] = original_browser_use_key
    
    if stream:
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    else:
        # For non-streaming, collect all events
        events = []
        async for event in generate():
            events.append(json.loads(event.replace("data: ", "")))
        return events[-1] if events else {"error": "No response generated"}


@router.get("/status")
async def get_browser_status(
    current_user: User = Depends(get_current_user)
):
    """Get browser-use status and configuration."""
    try:
        from browser_use import Browser
        browser_available = True
    except ImportError:
        browser_available = False
    
    api_config = await get_user_api_config(current_user)
    
    return {
        "browser_available": browser_available,
        "llm_provider": api_config.get("llm_provider", "ollama"),
        "uses_local_browser": True,  # Always true - we never use cloud browsers
        "uses_user_llm": True  # Always true - we never use ChatBrowserUse
    }
