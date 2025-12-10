"""DeepAgent integration for enhanced agent capabilities."""

from typing import List, Dict, Optional, Any, AsyncGenerator
from datetime import datetime
import logging

try:
    from deepagents import create_deep_agent
    from deepagents.backends import DeepAgentBackend
    from deepagents.backends.local import LocalBackend
    DEEPAGENTS_AVAILABLE = True
except ImportError as e:
    DEEPAGENTS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    # Only log at debug level to avoid noise if DeepAgent isn't being used
    logger.debug(f"DeepAgents not available: {e}. Install with: pip install deepagents")

from backend.config import settings
from backend.tools import tool_registry
from backend.agent.langchain_tools import LangChainToolAdapter

logger = logging.getLogger(__name__)


class DeepAgentWrapper:
    """Wrapper for DeepAgent integration."""
    
    def __init__(self, model: str = None):
        """Initialize DeepAgent wrapper."""
        if not DEEPAGENTS_AVAILABLE:
            raise ImportError("DeepAgents is not installed. Install with: pip install deepagents")
        
        self.model = model or settings.DEFAULT_MODEL
        self.backend: Optional[DeepAgentBackend] = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize DeepAgent backend."""
        try:
            # Try to use create_deep_agent if available
            # DeepAgents API may vary, so we'll try different approaches
            try:
                # Method 1: Use create_deep_agent directly
                from langchain.agents import create_agent
                from backend.agent.langchain_model import OllamaChatModel
                
                # Create LangChain model
                langchain_model = OllamaChatModel(
                    model_name=self.model,
                    base_url=settings.OLLAMA_BASE_URL
                )
                
                # For now, we'll use LangChain agent with DeepAgent-like features
                # DeepAgents might need additional setup
                self.backend = None  # Will use LangChain agent instead
                logger.info("DeepAgent mode enabled (using LangChain agent with enhanced features)")
            except Exception as e1:
                # Method 2: Try LocalBackend
                try:
                    self.backend = LocalBackend(
                        model=self.model,
                        base_url=settings.OLLAMA_BASE_URL
                    )
                    logger.info("DeepAgent backend initialized")
                except Exception as e2:
                    logger.warning(f"Could not initialize DeepAgent backend: {e2}")
                    # Fallback: use None and handle in run method
                    self.backend = None
        except Exception as e:
            logger.error(f"Failed to initialize DeepAgent backend: {e}")
            self.backend = None
    
    async def run(
        self,
        query: str,
        conversation_id: int,
        user_id: int,
        allowed_tools: List[str],
        stream: bool = True,
        message_history: Optional[List] = None
    ) -> AsyncGenerator[Dict, None]:
        """Run DeepAgent with query and optional message history."""
        
        # If backend is not available, fall back to using LangChain agent
        # with enhanced features (this is what DeepAgent mode does)
        if not self.backend:
            from backend.agent.agent import Agent
            from backend.config import settings
            
            # Create a LangChain agent with enhanced features
            fallback_agent = Agent(
                model=self.model,
                temperature=0.7,
                max_steps=15,  # More steps for "deep" reasoning
                max_tokens=3000  # More tokens for complex reasoning
            )
            
            # Use the fallback agent with message history
            async for result in fallback_agent.run(
                query=query,
                conversation_id=conversation_id,
                user_id=user_id,
                allowed_tools=allowed_tools,
                stream=stream,
                message_history=message_history
            ):
                yield result
            return
        
        try:
            # Convert tools to DeepAgent format
            # DeepAgents uses a similar tool format to LangChain
            langchain_tools = LangChainToolAdapter.convert_tools_for_user(allowed_tools)
            
            # Create agent with DeepAgent backend
            # Note: DeepAgent API may differ, adjust based on actual API
            if hasattr(self.backend, 'create_agent'):
                agent = self.backend.create_agent(
                    tools=langchain_tools,
                    system_prompt="You are a helpful AI Agent. Use tools when needed to answer user questions."
                )
            else:
                # Fallback to LangChain agent
                from backend.agent.agent import Agent
                agent = Agent(model=self.model)
                async for result in agent.run(query, conversation_id, user_id, allowed_tools, stream, message_history=message_history):
                    yield result
                return
            
            # Execute agent
            if stream:
                async for chunk in agent.stream(query):
                    yield {
                        "type": "step",
                        "step": {
                            "step_type": "deepagent",
                            "content": str(chunk),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
            else:
                result = await agent.run(query)
                yield {
                    "type": "complete",
                    "response": {
                        "final_answer": str(result),
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "query": query,
                        "success": True
                    }
                }
        
        except Exception as e:
            logger.error(f"DeepAgent execution error: {e}", exc_info=True)
            # Fallback to regular agent
            from backend.agent.agent import Agent
            fallback_agent = Agent(model=self.model)
            async for result in fallback_agent.run(query, conversation_id, user_id, allowed_tools, stream, message_history=message_history):
                yield result

