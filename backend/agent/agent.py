"""AI Agent implementation using LangChain v1 create_agent with middleware support."""

from typing import List, Dict, Optional, Any, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio
import logging
import re

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

# Try to import LLMToolSelectorMiddleware (may not be available in all LangChain versions)
try:
    from langchain.agents.middleware import LLMToolSelectorMiddleware
    LLM_TOOL_SELECTOR_AVAILABLE = True
except ImportError:
    LLM_TOOL_SELECTOR_AVAILABLE = False

from backend.agent.langchain_tools import LangChainToolAdapter
from backend.agent.langchain_model import OllamaChatModel
from backend.agent.model_factory import create_model
from backend.tools import tool_registry
from backend.storage import get_vector_store
from backend.config import settings

logger = logging.getLogger(__name__)

# Log if LLMToolSelectorMiddleware is not available
if not LLM_TOOL_SELECTOR_AVAILABLE:
    logger.info("LLMToolSelectorMiddleware not available in this LangChain version - tool selection will rely on model's built-in capabilities")


def serialize_datetime(obj):
    """Recursively serialize datetime objects in nested structures."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj


def extract_reasoning_content(content: str) -> str:
    """Extract content from <think> tags."""
    if not content:
        return ""
    
    # Extract reasoning content from tags (support both <think> and <think>)
    matches = re.findall(r'<(?:think|redacted_reasoning)>(.*?)</(?:think|redacted_reasoning)>', content, flags=re.DOTALL | re.IGNORECASE)
    if matches:
        return " ".join(matches).strip()
    
    # Handle unclosed tags
    match = re.search(r'<(?:think|redacted_reasoning)>(.*?)(?=</(?:think|redacted_reasoning)>|$)', content, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""


def strip_reasoning_tags(content: str) -> str:
    """Remove <think> or <think> tags from content for chat display."""
    if not content:
        return content
    
    # Remove <think>...</think> or <think>...</think> tags and their content
    content = re.sub(r'<(?:think|redacted_reasoning)>.*?</(?:think|redacted_reasoning)>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Also handle unclosed tags or variations
    content = re.sub(r'<(?:think|redacted_reasoning)>.*?$', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'^.*?</(?:think|redacted_reasoning)>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up extra whitespace
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple newlines to double
    content = content.strip()
    
    return content


class AgentStep(BaseModel):
    """Single step in agent execution."""
    step_number: int
    step_type: str  # "plan", "tool_request", "tool_result", "reflection", "answer"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[Any] = None
    tool_approved: Optional[bool] = None
    reasoning: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        d = super().model_dump(*args, **kwargs)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
        return d
    
    def dict(self, *args, **kwargs):
        """Backward compatibility alias for model_dump."""
        return self.model_dump(*args, **kwargs)


class AgentResponse(BaseModel):
    """Complete agent response."""
    conversation_id: int
    user_id: int
    query: str
    steps: List[AgentStep]
    final_answer: str
    total_tokens: int
    execution_time: float
    success: bool
    
    def model_dump(self, *args, **kwargs):
        """Override model_dump to handle datetime serialization."""
        d = super().model_dump(*args, **kwargs)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
            elif isinstance(value, list):
                d[key] = [serialize_datetime(item) if isinstance(item, dict) else item for item in value]
        return d
    
    def dict(self, *args, **kwargs):
        """Backward compatibility alias for model_dump."""
        return self.model_dump(*args, **kwargs)


class Agent:
    """AI Agent using LangChain v1 create_agent with middleware support."""
    
    def __init__(
        self,
        model: str = None,
        temperature: float = 0.7,
        max_steps: int = 10,
        max_tokens: int = 2000,
        api_config: Optional[Dict] = None
    ):
        """Initialize the agent."""
        self.temperature = temperature
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.api_config = api_config or {}
        
        # Determine provider and model
        llm_provider = self.api_config.get("llm_provider", "ollama")
        
        # For Ollama, use the model name from preferences
        # For other providers, use the model from api_config
        if llm_provider == "ollama":
            self.model = model or settings.DEFAULT_MODEL
        else:
            # Use provider-specific model from api_config
            provider_model_key = f"{llm_provider}_model"
            self.model = self.api_config.get(provider_model_key) or model or settings.DEFAULT_MODEL
        
        # Initialize components
        self.vector_store = get_vector_store()
        
        # Create LangChain model based on provider
        try:
            self.langchain_model = create_model(
                provider=llm_provider,
                model_name=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_config=self.api_config
            )
            logger.info(f"Created {llm_provider} model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to create {llm_provider} model: {e}. Falling back to Ollama.")
            # Fallback to Ollama if provider setup fails
            self.langchain_model = OllamaChatModel(
                model_name=settings.DEFAULT_MODEL,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                base_url=settings.OLLAMA_BASE_URL
            )
            self.model = settings.DEFAULT_MODEL
            llm_provider = "ollama"
        
        # Agent instance (will be created with tools)
        self.agent = None
        
        # Track execution state
        self.steps: List[AgentStep] = []
        self.total_tokens = 0
        self.current_step = 0
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent."""
        return """You are a helpful AI Agent. Your job is to help users by using tools when needed.

IMPORTANT RULES:
1. When a user provides webpage content or context in their message, you should answer their question directly based on that content. You do NOT need to use tools to search for information that is already provided in the message.

2. Only use tools when:
   - The user explicitly asks you to search, find, or get information that is NOT in the provided context
   - You need to access files, databases, or external resources
   - The user asks you to perform an action (like reading a file, calculating, etc.)
   When the user asks to "search the web", "search for X", "find news on X", or similar, you MUST call the web_search tool with their query, then summarize or quote the actual results in your reply. Do not reply with only a generic phrase like "I've completed the task"—include what you found.

3. When webpage content is provided, treat it as the source of truth and answer questions based on it directly. Do not say "I've completed the task" - instead, provide a helpful answer based on the webpage content.

4. ALWAYS generate a final answer after using tools, even if the tool returns empty results or no matches. You must:
   - Acknowledge that you searched/checked
   - Explain what you found (or didn't find)
   - Provide a helpful response based on the tool results
   - If results are empty, say something like "I searched through the files but didn't find any matches for your query" or "No files matched your search criteria"

5. Never leave the user without a response after tool execution. Always provide a clear, helpful answer.

6. Use tools when appropriate to answer user questions, but prioritize using provided context when available.

7. Be concise and accurate in your responses.

8. REMINDERS AND SCHEDULING: When the user asks to set a reminder, be reminded of something, or schedule a task at a date/time (e.g. "remind me to X", "remind to X on DATE at TIME", "schedule ..."), you MUST call the schedule_job tool with job_type (e.g. "reminder"), title, and run_at. Replying only with a success message does NOT create the job—you must invoke the tool so the reminder is actually saved and will run.

9. Always provide helpful and accurate information."""
    
    def _create_agent(self, tools: List, middleware: Optional[List] = None):
        """Create LangChain agent with tools and optional middleware."""
        # Build middleware list
        middleware_list = middleware or []
        
        # Create agent with tools and middleware
        self.agent = create_agent(
            model=self.langchain_model,
            tools=tools,
            system_prompt=self._get_system_prompt(),
            middleware=middleware_list
        )
        logger.info(f"Agent created with {len(tools)} tools and {len(middleware_list)} middleware")
    
    async def run(
        self,
        query: str,
        conversation_id: int,
        user_id: int,
        allowed_tools: List[str],
        stream: bool = True,
        message_history: Optional[List] = None,
        mcp_server_ids: Optional[List[int]] = None,
        use_tool_selector_middleware: bool = True,
        image_base64_list: Optional[List[str]] = None,
        invocation_source: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Run the agent with a query and optional message history.
        mcp_server_ids: when None, load all user MCP servers; when [], load none; when [id,...], load only those.
        use_tool_selector_middleware: when False, skip LLMToolSelectorMiddleware (avoids model dict-response issues).
        image_base64_list: optional list of base64-encoded images for vision (chatbot image support).
        invocation_source: e.g. 'telegram' so tools like schedule_job can store the correct source.
        """
        start_time = datetime.utcnow()
        self.steps = []
        self.current_step = 0
        self.total_tokens = 0
        
        try:
            # Convert tools to LangChain format with user context
            langchain_tools = LangChainToolAdapter.convert_tools_for_user(
                allowed_tools, user_id=user_id, invocation_source=invocation_source
            )
            logger.info(f"Converted {len(langchain_tools)} tools for agent: {[t.name for t in langchain_tools]}")
            
            # Load MCP tools if available (mcp_server_ids=None means all; [] means none)
            try:
                from backend.services.mcp_service import mcp_service
                from backend.models import SessionLocal
                db_session = SessionLocal()
                try:
                    mcp_tools = await mcp_service.get_tools_for_user(db_session, user_id, server_ids=mcp_server_ids)
                    if mcp_tools:
                        langchain_tools.extend(mcp_tools)
                        logger.info(f"Added {len(mcp_tools)} MCP tools. Total tools: {len(langchain_tools)}")
                finally:
                    db_session.close()
            except Exception as mcp_error:
                logger.warning(f"Failed to load MCP tools: {mcp_error}")
            
            middleware_list = []
            if use_tool_selector_middleware and LLM_TOOL_SELECTOR_AVAILABLE and langchain_tools and len(langchain_tools) > 1:
                try:
                    # Use a lightweight model for tool selection (same as main model for consistency)
                    llm_provider = self.api_config.get("llm_provider", "ollama")
                    try:
                        tool_selector_model = create_model(
                            provider=llm_provider,
                            model_name=self.model,
                            temperature=0.1,  # Lower temperature for more deterministic tool selection
                            max_tokens=500,
                            api_config=self.api_config
                        )
                    except Exception as e:
                        logger.warning(f"Failed to create tool selector model with {llm_provider}: {e}. Using Ollama fallback.")
                        tool_selector_model = OllamaChatModel(
                            model_name=settings.DEFAULT_MODEL,
                            temperature=0.1,
                            max_tokens=500,
                            base_url=settings.OLLAMA_BASE_URL
                        )
                    
                    tool_selector_middleware = LLMToolSelectorMiddleware(
                        model=tool_selector_model,
                        max_tools=10  # Maximum number of tools to select
                    )
                    middleware_list.append(tool_selector_middleware)
                    logger.info("Added LLMToolSelectorMiddleware for intelligent tool selection")
                except Exception as e:
                    logger.warning(f"Failed to create LLMToolSelectorMiddleware: {e}. Continuing without it.")
            
            # Build message history from previous messages
            messages = []
            if message_history:
                for msg in message_history:
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        ai_msg = AIMessage(content=msg.content or "")
                        messages.append(ai_msg)
                    elif msg.role == "system":
                        messages.append(SystemMessage(content=msg.content))
                    elif msg.role == "tool" and msg.tool_name:
                        # Reconstruct tool message
                        tool_msg = ToolMessage(
                            content=str(msg.tool_output) if msg.tool_output else msg.content,
                            tool_call_id=msg.tool_name
                        )
                        messages.append(tool_msg)
                
                logger.info(f"Loaded {len(messages)} messages from conversation history")

            # Build current user message: text only or multimodal (text + images)
            if image_base64_list:
                # LangChain multimodal format: text part + image_url parts (OpenAI-style; Ollama adapter converts to images array)
                content_parts: List[Dict[str, Any]] = [{"type": "text", "text": query or "What do you see in these images?"}]
                for b64 in image_base64_list:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    })
                messages.append(HumanMessage(content=content_parts))
            else:
                messages.append(HumanMessage(content=query))

            # Prepare initial state with full message history
            initial_state = {
                "messages": messages
            }
            logger.info(f"Initial state prepared with {len(messages)} total messages (including current query)")

            # Create agent with tools and middleware (LangChain middleware implementation)
            self._create_agent(langchain_tools, middleware=middleware_list)

            try:
                if stream:
                    async for chunk in self._stream_agent_execution(initial_state, query, conversation_id, user_id, start_time):
                        yield chunk
                else:
                    result = await self.agent.ainvoke(initial_state)
                    final_answer = self._extract_final_answer(result)
                    end_time = datetime.utcnow()
                    response_dict = {
                        "type": "complete",
                        "response": AgentResponse(
                            conversation_id=conversation_id,
                            user_id=user_id,
                            query=query,
                            steps=self.steps,
                            final_answer=final_answer,
                            total_tokens=self.total_tokens,
                            execution_time=(end_time - start_time).total_seconds(),
                            success=True,
                        ).model_dump(),
                    }
                    yield serialize_datetime(response_dict)
            except AssertionError as e:
                err_msg = str(e)
                if "Expected dict response" in err_msg and "NoneType" in err_msg and middleware_list:
                    # Tool selector middleware expects a dict; this model returned something else.
                    # Retry without the middleware so the model uses tools directly (same as "simple agent").
                    logger.warning(
                        "Tool selector got unexpected response from model, retrying without middleware: %s",
                        e,
                    )
                    self._create_agent(langchain_tools, middleware=[])
                    self.steps = []
                    try:
                        if stream:
                            async for chunk in self._stream_agent_execution(
                                initial_state, query, conversation_id, user_id, start_time
                            ):
                                yield chunk
                        else:
                            result = await self.agent.ainvoke(initial_state)
                            final_answer = self._extract_final_answer(result)
                            end_time = datetime.utcnow()
                            response_dict = {
                                "type": "complete",
                                "response": AgentResponse(
                                    conversation_id=conversation_id,
                                    user_id=user_id,
                                    query=query,
                                    steps=self.steps,
                                    final_answer=final_answer,
                                    total_tokens=self.total_tokens,
                                    execution_time=(end_time - start_time).total_seconds(),
                                    success=True,
                                ).model_dump(),
                            }
                            yield serialize_datetime(response_dict)
                    except Exception as retry_e:
                        logger.error(f"Retry without middleware failed: {retry_e}", exc_info=True)
                        yield {"type": "error", "error": str(retry_e)}
                elif "Expected dict response" in err_msg and "NoneType" in err_msg:
                    friendly = (
                        "The AI model returned an unexpected response. "
                        "Try again or switch to another model in Settings → AI Settings."
                    )
                    logger.warning(f"Agent model response error (model compatibility): {e}")
                    yield {"type": "error", "error": friendly}
                else:
                    logger.error(f"Agent assertion error: {e}", exc_info=True)
                    yield {"type": "error", "error": err_msg}
        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def _stream_agent_execution(
        self, 
        initial_state: Dict, 
        query: str,
        conversation_id: int,
        user_id: int,
        start_time: datetime
    ) -> AsyncGenerator[Dict, None]:
        """Stream agent execution and track tool calls/results."""
        
        step_number = 1
        accumulated_content = ""
        accumulated_reasoning = ""
        seen_messages = set()  # Track processed messages to avoid duplicates
        reasoning_prefix_sent = False  # Track if we've sent the reasoning prefix
        
        try:
            logger.info(f"Starting agent stream execution for query: {query[:100]}")
            
            # Use astream_events to get token-level streaming
            chunk_count = 0
            all_messages = []  # Collect all messages from chunks
            has_seen_tool_result = False  # Track if we've seen tool results
            current_ai_content = ""  # Track current AI message content as it streams
            current_reasoning = ""  # Track current reasoning content as it streams
            
            # Use astream to get incremental state updates
            async for chunk in self.agent.astream(initial_state):
                chunk_count += 1
                logger.info(f"Chunk #{chunk_count}: {type(chunk)}, keys: {chunk.keys() if isinstance(chunk, dict) else 'not a dict'}")
                logger.debug(f"Chunk content: {chunk}")
                
                # Handle different chunk formats
                if isinstance(chunk, dict):
                    # Check for messages in various possible keys
                    if "messages" in chunk:
                        messages = chunk["messages"]
                        all_messages.extend(messages)
                    elif "model" in chunk:
                        # This might be a model response chunk
                        logger.debug(f"Model chunk: {chunk.get('model')}")
                    # Some chunks might be the messages themselves
                    elif any(isinstance(v, (list, tuple)) for v in chunk.values()):
                        for key, value in chunk.items():
                            if isinstance(value, (list, tuple)) and value:
                                if isinstance(value[0], (AIMessage, HumanMessage, ToolMessage, SystemMessage)):
                                    all_messages.extend(value)
                                    logger.info(f"Found messages in chunk key '{key}': {len(value)} messages")
            
            # Process all collected messages
            logger.info(f"Total messages collected: {len(all_messages)}")
            for msg in all_messages:
                # Create a unique identifier for the message
                msg_id = id(msg)
                if msg_id in seen_messages:
                    continue
                seen_messages.add(msg_id)
                
                logger.info(f"Processing message: {type(msg).__name__}, content preview: {str(getattr(msg, 'content', ''))[:100]}")
                
                # Handle AIMessage with tool calls
                if isinstance(msg, AIMessage):
                                # Check for tool calls
                                tool_calls = getattr(msg, 'tool_calls', None) or []
                                
                                if tool_calls:
                                    logger.info(f"Detected {len(tool_calls)} tool call(s)")
                                    for tool_call in tool_calls:
                                        # Extract tool call info
                                        if isinstance(tool_call, dict):
                                            tool_name = tool_call.get("name", "")
                                            tool_args = tool_call.get("args", {})
                                            tool_call_id = tool_call.get("id", "")
                                        else:
                                            tool_name = getattr(tool_call, "name", "")
                                            tool_args = getattr(tool_call, "args", {})
                                            tool_call_id = getattr(tool_call, "id", "")
                                        
                                        logger.info(f"Tool call: {tool_name} with args: {tool_args}")
                                        
                                        # Create tool request step
                                        request_step = AgentStep(
                                            step_number=step_number,
                                            step_type="tool_request",
                                            content=f"Calling {tool_name}",
                                            tool_name=tool_name,
                                            tool_input=tool_args,
                                            reasoning=f"Agent decided to use {tool_name} tool"
                                        )
                                        self.steps.append(request_step)
                                        step_number += 1
                                        
                                        yield {
                                            "type": "step",
                                            "step": serialize_datetime(request_step.model_dump())
                                        }
                                
                                # Stream AI message content incrementally
                                # Only stream to chat if:
                                # 1. No tool calls (direct answer), OR
                                # 2. Has tool calls but we've seen tool results (this is the final answer after processing tool results)
                                if msg.content:
                                    content = str(msg.content)
                                    if content and content.strip() and content != "None":
                                        # Determine if this is a final answer or just thinking
                                        is_final_answer = not tool_calls or (tool_calls and has_seen_tool_result)
                                        
                                        # Process content incrementally to extract reasoning
                                        if content != previous_ai_content:
                                            # Get the new part of the content
                                            new_part = content[len(previous_ai_content):] if previous_ai_content and content.startswith(previous_ai_content) else content
                                            
                                            # Extract reasoning from the new part
                                            if new_part:
                                                # Check if we're in a reasoning tag
                                                temp_full_content = content
                                                reasoning_matches = re.findall(r'<(?:think|redacted_reasoning)>(.*?)(?=</(?:think|redacted_reasoning)>|$)', temp_full_content, flags=re.DOTALL | re.IGNORECASE)
                                                if reasoning_matches:
                                                    # We have reasoning content
                                                    current_reasoning = reasoning_matches[-1]
                                                    if current_reasoning and current_reasoning != accumulated_reasoning:
                                                        # New reasoning content to stream
                                                        new_reasoning = current_reasoning[len(accumulated_reasoning):] if accumulated_reasoning else current_reasoning
                                                        if new_reasoning:
                                                            if not reasoning_prefix_sent:
                                                                # Send prefix first
                                                                yield {
                                                                    "type": "reasoning",
                                                                    "token": "AI is thinking about...: "
                                                                }
                                                                reasoning_prefix_sent = True
                                                            # Stream reasoning token by token
                                                            for char in new_reasoning:
                                                                yield {
                                                                    "type": "reasoning",
                                                                    "token": char
                                                                }
                                                            accumulated_reasoning = current_reasoning
                                                
                                                # Stream final answer (non-reasoning content) if it's a final answer
                                                if is_final_answer:
                                                    content_for_chat = strip_reasoning_tags(content)
                                                    if content_for_chat != accumulated_content:
                                                        new_content = content_for_chat[len(accumulated_content):] if accumulated_content and content_for_chat.startswith(accumulated_content) else content_for_chat
                                                        if new_content:
                                                            # Reset reasoning prefix when we start streaming answer
                                                            if reasoning_prefix_sent:
                                                                reasoning_prefix_sent = False
                                                            # Stream answer token by token
                                                            for char in new_content:
                                                                yield {
                                                                    "type": "token",
                                                                    "token": char
                                                                }
                                                            accumulated_content = content_for_chat
                                            
                                            previous_ai_content = content
                                        
                                        if is_final_answer:
                                            
                                            # Create answer step for final response
                                            # Keep full content (with reasoning) in steps for agent process
                                            step = AgentStep(
                                                step_number=step_number,
                                                step_type="answer",
                                                content=content,  # Full content with reasoning for agent process
                                                reasoning="Agent final answer" if has_seen_tool_result else "Agent response"
                                            )
                                            self.steps.append(step)
                                            step_number += 1
                                            
                                            yield {
                                                "type": "step",
                                                "step": serialize_datetime(step.model_dump())
                                            }
                                            
                                            # Reset flag after final answer
                                            has_seen_tool_result = False
                                        else:
                                            # This is thinking/planning (has tool calls but no tool results yet)
                                            # Don't stream to chat, but create a thinking step for agent process
                                            step = AgentStep(
                                                step_number=step_number,
                                                step_type="thinking",
                                                content=content,  # Full thinking content for agent process
                                                reasoning="Agent thinking process"
                                            )
                                            self.steps.append(step)
                                            step_number += 1
                                            
                                            yield {
                                                "type": "step",
                                                "step": serialize_datetime(step.model_dump())
                                            }
                
                # Handle ToolMessage (tool results)
                elif isinstance(msg, ToolMessage):
                                tool_result = str(msg.content)
                                tool_call_id = getattr(msg, "tool_call_id", "")
                                
                                logger.info(f"Tool result received (call_id: {tool_call_id}): {tool_result[:200]}...")
                                
                                # Mark that we've seen a tool result - next AI message should be final answer
                                has_seen_tool_result = True
                                
                                # Find corresponding tool request by matching tool_call_id
                                tool_name = None
                                tool_input = None
                                for step in reversed(self.steps):
                                    if step.step_type == "tool_request":
                                        tool_name = step.tool_name
                                        tool_input = step.tool_input
                                        break
                                
                                # Create tool result step
                                result_step = AgentStep(
                                    step_number=step_number,
                                    step_type="tool_result",
                                    content=tool_result,
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_output={"result": tool_result},
                                    reasoning="Tool execution completed"
                                )
                                self.steps.append(result_step)
                                step_number += 1
                                
                                yield {
                                    "type": "step",
                                    "step": serialize_datetime(result_step.model_dump())
                                }
            
            # After streaming, get final state to extract any missed tool results
            logger.info(f"Streaming completed. Processing final state for missed tool results...")
            try:
                final_state = await self.agent.ainvoke(initial_state)
                logger.info(f"Final state keys: {final_state.keys() if isinstance(final_state, dict) else 'not a dict'}")
                
                # Process final state messages to extract tool results we might have missed
                if isinstance(final_state, dict) and "messages" in final_state:
                    final_messages = final_state["messages"]
                    logger.info(f"Final state has {len(final_messages)} messages")
                    
                    # Log all message types for debugging
                    for i, msg in enumerate(final_messages):
                        msg_type = type(msg).__name__
                        has_content = bool(getattr(msg, 'content', None))
                        has_tool_calls = bool(getattr(msg, 'tool_calls', None))
                        logger.info(f"Message {i+1}: {msg_type}, has_content={has_content}, has_tool_calls={has_tool_calls}")
                        
                        if isinstance(msg, AIMessage):
                            content_preview = str(msg.content)[:200] if msg.content else 'None'
                            tool_calls_info = msg.tool_calls if hasattr(msg, 'tool_calls') and msg.tool_calls else 'None'
                            logger.info(f"  AIMessage content preview: {content_preview}")
                            logger.info(f"  AIMessage tool_calls: {tool_calls_info}")
                        elif isinstance(msg, ToolMessage):
                            content_preview = str(msg.content)[:200] if msg.content else 'None'
                            tool_call_id = getattr(msg, 'tool_call_id', 'None')
                            logger.info(f"  ToolMessage content preview: {content_preview}")
                            logger.info(f"  ToolMessage tool_call_id: {tool_call_id}")
                    
                    # Process messages in order - first check for tool calls, then tool results
                    for msg in final_messages:
                        msg_id = id(msg)
                        if msg_id in seen_messages:
                            logger.debug(f"Skipping already seen message: {type(msg).__name__}")
                            continue
                        seen_messages.add(msg_id)
                        
                        # Check for AIMessage with tool calls first
                        if isinstance(msg, AIMessage):
                            tool_calls = getattr(msg, 'tool_calls', None) or []
                            
                            if tool_calls:
                                logger.info(f"Found {len(tool_calls)} tool call(s) in final state")
                                for tool_call in tool_calls:
                                    if isinstance(tool_call, dict):
                                        tool_name = tool_call.get("name", "")
                                        tool_args = tool_call.get("args", {})
                                        tool_call_id = tool_call.get("id", "")
                                    else:
                                        tool_name = getattr(tool_call, "name", "")
                                        tool_args = getattr(tool_call, "args", {})
                                        tool_call_id = getattr(tool_call, "id", "")
                                    
                                    logger.info(f"Tool call in final state: {tool_name} with args: {tool_args}")
                                    
                                    # Check if we already have this tool request
                                    already_has_request = any(
                                        step.step_type == "tool_request" and step.tool_name == tool_name
                                        for step in self.steps
                                    )
                                    
                                    if not already_has_request:
                                        request_step = AgentStep(
                                            step_number=step_number,
                                            step_type="tool_request",
                                            content=f"Calling {tool_name}",
                                            tool_name=tool_name,
                                            tool_input=tool_args,
                                            reasoning=f"Agent decided to use {tool_name} tool"
                                        )
                                        self.steps.append(request_step)
                                        step_number += 1
                                        
                                        yield {
                                            "type": "step",
                                            "step": serialize_datetime(request_step.model_dump())
                                        }
                        
                        # Check for ToolMessage we might have missed
                        elif isinstance(msg, ToolMessage):
                            tool_result = str(msg.content)
                            tool_call_id = getattr(msg, "tool_call_id", "")
                            
                            logger.info(f"Found tool result in final state (call_id: {tool_call_id}): {tool_result[:200]}...")
                            
                            # Check if we already have this result
                            already_has_result = any(
                                step.step_type == "tool_result" and step.content == tool_result
                                for step in self.steps
                            )
                            
                            if not already_has_result:
                                # Find corresponding tool request
                                tool_name = None
                                tool_input = None
                                for step in reversed(self.steps):
                                    if step.step_type == "tool_request":
                                        tool_name = step.tool_name
                                        tool_input = step.tool_input
                                        break
                                
                                # Create tool result step (for agent process panel only)
                                result_step = AgentStep(
                                    step_number=step_number,
                                    step_type="tool_result",
                                    content=tool_result,
                                    tool_name=tool_name,
                                    tool_input=tool_input,
                                    tool_output={"result": tool_result},
                                    reasoning="Tool execution completed"
                                )
                                self.steps.append(result_step)
                                step_number += 1
                                
                                yield {
                                    "type": "step",
                                    "step": serialize_datetime(result_step.model_dump())
                                }
                                
                                # Don't stream tool result to chat - wait for LLM to process it and generate final answer
                                # The tool result is passed back to the agent via ToolMessage,
                                # and the agent will generate a sophisticated answer based on it
                        
                        # Check for final AIMessage with answer (if not already processed as tool call)
                        # This should be the LLM's response after processing tool results
                        elif isinstance(msg, AIMessage):
                            # Check if this message has content (even if empty, we should process it)
                            content = str(msg.content) if msg.content else ""
                            tool_calls = getattr(msg, 'tool_calls', None) or []
                            
                            # Only process if this is a final answer (no tool calls) OR if we've seen tool results
                            # If it has tool calls but we haven't seen results yet, it's just planning
                            is_final_answer = not tool_calls or (tool_calls and has_seen_tool_result)
                            
                            if is_final_answer and (content.strip() or not tool_calls):
                                # This is a final answer after tool execution
                                # Even if content is empty, we should acknowledge the tool execution
                                if not content.strip() and has_seen_tool_result:
                                    # LLM didn't generate content after tool results - create a helpful message
                                    # Check if tool results were empty
                                    tool_results = [step for step in self.steps if step.step_type == "tool_result"]
                                    if tool_results:
                                        last_tool_result = tool_results[-1].content if tool_results else ""
                                        if not last_tool_result or last_tool_result.strip() in ["[]", "{}", ""]:
                                            content = "I searched through the files but didn't find any matches for your query. The search returned no results."
                                        else:
                                            content = "I've completed the search using the available tools. Here are the results I found."
                                    else:
                                        content = "I've completed the task using the available tools."
                                    logger.warning("LLM didn't generate content after tool results, creating helpful response")
                                
                                if content.strip():
                                    # Check if we already have this as a step
                                    already_has_answer = any(
                                        step.step_type == "answer" and step.content == content
                                        for step in self.steps
                                    )
                                    
                                    if not already_has_answer:
                                        step = AgentStep(
                                            step_number=step_number,
                                            step_type="answer",
                                            content=content,
                                            reasoning="Agent final response after tool execution"
                                        )
                                        self.steps.append(step)
                                        step_number += 1
                                        
                                        yield {
                                            "type": "step",
                                            "step": serialize_datetime(step.model_dump())
                                        }
                                        
                                        # Stream the content if not already streamed
                                        # Strip reasoning tags for chat
                                        content_cleaned = strip_reasoning_tags(content)
                                        if content_cleaned and content_cleaned != accumulated_content:
                                            remaining = content_cleaned[len(accumulated_content):] if accumulated_content and content_cleaned.startswith(accumulated_content) else content_cleaned
                                            if remaining:
                                                for char in remaining:
                                                    yield {
                                                        "type": "token",
                                                        "token": char
                                                    }
                                                accumulated_content = content_cleaned
                                        
                                        # Reset flag after final answer
                                        has_seen_tool_result = False
                
                # Extract final answer
                final_answer = self._extract_final_answer(final_state)
                if not final_answer:
                    final_answer = self._extract_final_answer_from_steps()
                if not final_answer:
                    final_answer = accumulated_content if accumulated_content else "I've completed the task using the available tools."
                    
            except Exception as e:
                logger.warning(f"Failed to get final state: {e}")
                final_answer = self._extract_final_answer_from_steps()
                if not final_answer:
                    final_answer = accumulated_content if accumulated_content else "I've completed the task using the available tools."
            
            # If we have a final answer that wasn't streamed, stream it now
            # Make sure to strip reasoning tags from what we stream to chat
            if final_answer:
                # Clean the final answer for chat (remove reasoning tags)
                final_answer_cleaned = strip_reasoning_tags(final_answer)
                
                if final_answer_cleaned and final_answer_cleaned != accumulated_content:
                    remaining_content = final_answer_cleaned[len(accumulated_content):] if accumulated_content and final_answer_cleaned.startswith(accumulated_content) else final_answer_cleaned
                    if remaining_content:
                        for char in remaining_content:
                            yield {
                                "type": "token",
                                "token": char
                            }
                        accumulated_content = final_answer_cleaned
                
                # Update final_answer to cleaned version for the response
                final_answer = final_answer_cleaned
            
            # Use accumulated_content as the final answer since that's what was actually streamed to the user
            # This ensures the saved message matches what the user saw
            if accumulated_content and accumulated_content.strip():
                final_answer = accumulated_content.strip()
            
            # Create final response
            end_time = datetime.utcnow()
            response_dict = {
                "type": "complete",
                "response": AgentResponse(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    query=query,
                    steps=self.steps,
                    final_answer=final_answer,
                    total_tokens=self.total_tokens,
                    execution_time=(end_time - start_time).total_seconds(),
                    success=True,
                ).model_dump(),
            }
            yield serialize_datetime(response_dict)
        
        except Exception as e:
            logger.error(f"Error streaming agent execution: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def _extract_final_answer(self, state: Dict) -> str:
        """Extract final answer from agent state - only the LLM's final answer, not raw tool results."""
        messages = state.get("messages", [])
        
        # Find the last AI message that comes AFTER all tool calls/results
        # This is the LLM's sophisticated answer based on tool results
        final_ai_content = ""
        last_tool_index = -1
        has_tool_results = False
        
        # Find the index of the last tool message and check if we have tool results
        for i, message in enumerate(messages):
            if isinstance(message, ToolMessage):
                last_tool_index = i
                has_tool_results = True
        
        # Get the last AI message that comes after the last tool result
        # This is the final answer where LLM has processed tool results
        for i in range(len(messages) - 1, -1, -1):
            message = messages[i]
            if isinstance(message, AIMessage):
                # Check if this message has content and no tool calls (final answer)
                tool_calls = getattr(message, 'tool_calls', None) or []
                if not tool_calls:
                    # If this AI message comes after tool results, it's the final answer
                    if i > last_tool_index or last_tool_index == -1:
                        if message.content:
                            final_ai_content = str(message.content)
                        break
        
        # If we have tool results but no final answer (or model gave a generic one), use tool output
        generic_phrases = (
            "i've completed the task",
            "i've completed the task using the available tools",
            "task completed",
        )
        is_generic = final_ai_content and any(
            p in final_ai_content.lower().strip() for p in generic_phrases
        ) and len(final_ai_content.strip()) < 120
        if has_tool_results and (not final_ai_content or is_generic):
            tool_results = [msg for msg in messages if isinstance(msg, ToolMessage)]
            if tool_results:
                last_tool_result = str(tool_results[-1].content) if tool_results else ""
                if not last_tool_result or last_tool_result.strip() in ("[]", "{}"):
                    final_ai_content = "I searched but didn't find any results for your query."
                elif last_tool_result.strip().startswith("Error:"):
                    err_body = last_tool_result.strip()
                    if len(err_body) > 200:
                        err_body = err_body[:197] + "..."
                    final_ai_content = f"I couldn't complete that. {err_body}"
                else:
                    # Show actual tool output so user sees search results etc. (truncate if huge)
                    raw = last_tool_result.strip()
                    if len(raw) > 3500:
                        raw = raw[:3497] + "..."
                    final_ai_content = f"Here are the results:\n\n{raw}"
            else:
                final_ai_content = "I used the tools but couldn't format a reply. Try asking again."
        
        # If no AI message after tools, get the last AI message
        if not final_ai_content:
            for message in reversed(messages):
                if isinstance(message, AIMessage) and message.content:
                    final_ai_content = str(message.content)
                    break
        
        # Remove reasoning tags for chat
        if final_ai_content:
            cleaned_content = strip_reasoning_tags(final_ai_content)
            return cleaned_content
        
        return ""
    
    def _extract_final_answer_from_steps(self) -> str:
        """Extract final answer from collected steps - only LLM answers, not raw tool results."""
        # Find the last answer step that comes AFTER tool results
        # This represents the LLM's final answer after processing tool results
        last_tool_result_index = -1
        
        # Find the index of the last tool result
        for i, step in enumerate(self.steps):
            if step.step_type == "tool_result":
                last_tool_result_index = i
        
        # Get the last answer step that comes after tool results
        for i in range(len(self.steps) - 1, -1, -1):
            step = self.steps[i]
            if step.step_type == "answer" and step.content:
                # If this answer comes after tool results, it's the final answer
                if i > last_tool_result_index or last_tool_result_index == -1:
                    cleaned_content = strip_reasoning_tags(step.content)
                    if cleaned_content:
                        return cleaned_content
        
        # Fallback: get the last answer step regardless
        for step in reversed(self.steps):
            if step.step_type == "answer" and step.content:
                cleaned_content = strip_reasoning_tags(step.content)
                if cleaned_content:
                    return cleaned_content
        
        # Fallback: look for reflection steps
        for step in reversed(self.steps):
            if step.step_type == "reflection" and step.content and not step.tool_name:
                return strip_reasoning_tags(step.content)
        
        return ""
    
    async def save_to_memory(
        self,
        conversation_id: int,
        message: str,
        metadata: Dict
    ):
        """Save message to vector memory."""
        try:
            await self.vector_store.add_documents(
                documents=[message],
                metadatas=[{
                    "conversation_id": conversation_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **metadata
                }],
                collection_name="conversations"
            )
        except Exception as e:
            logger.error(f"Failed to save to memory: {e}")
    
    async def retrieve_context(
        self,
        query: str,
        conversation_id: int,
        k: int = 5
    ) -> List[Dict]:
        """Retrieve relevant context from memory."""
        try:
            results = await self.vector_store.search(
                query=query,
                k=k,
                filter={"conversation_id": conversation_id},
                collection_name="conversations"
            )
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return []
