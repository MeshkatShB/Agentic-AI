"""LangChain model adapter for Ollama."""

import re
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage, ToolCall
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from pydantic import Field, ConfigDict

from backend.llm import OllamaClient
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)


def _human_message_to_ollama(msg: "HumanMessage") -> Dict[str, Any]:
    """Convert HumanMessage to Ollama API format. Supports text and multimodal (text + images)."""
    content = msg.content
    if isinstance(content, list):
        text_parts = []
        images = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    url = (part.get("image_url") or {}).get("url", "")
                    # data:image/png;base64,<b64> or data:image/jpeg;base64,<b64>
                    m = re.match(r"data:image/[^;]+;base64,(.+)", url)
                    if m:
                        images.append(m.group(1).strip())
        out = {"role": "user", "content": "\n".join(text_parts) or "What do you see?"}
        if images:
            out["images"] = images
        return out
    return {"role": "user", "content": content if isinstance(content, str) else str(content)}


class OllamaChatModel(BaseChatModel):
    """LangChain-compatible chat model for Ollama."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")
    
    model_name: str = Field(default="qwen3:latest")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    base_url: str = Field(default="http://127.0.0.1:11434")
    bound_tools: Optional[List[BaseTool]] = Field(default=None, exclude=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Store ollama_client as a private attribute (not a Pydantic field)
        self._ollama_client = OllamaClient(base_url=self.base_url)
        # Initialize bound_tools if not set
        if not hasattr(self, 'bound_tools'):
            self.bound_tools = None
    
    @property
    def ollama_client(self) -> OllamaClient:
        """Get or create the Ollama client."""
        if not hasattr(self, '_ollama_client') or self._ollama_client is None:
            self._ollama_client = OllamaClient(base_url=self.base_url)
        return self._ollama_client
    
    @property
    def _llm_type(self) -> str:
        return "ollama"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation (not used in async context)."""
        raise NotImplementedError("Use async generation instead")
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generation."""
        
        # Convert LangChain messages to Ollama format
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                ollama_messages.append(_human_message_to_ollama(msg))
            elif isinstance(msg, AIMessage):
                ollama_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                ollama_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                # Tool messages are typically included in the conversation
                ollama_messages.append({"role": "assistant", "content": f"Tool result: {msg.content}"})
        
        # Convert tools to Ollama format if bound
        ollama_tools = self._convert_tools_to_ollama_format()
        
        # Generate response
        response_text = ""
        chat_kwargs = {
            "model": self.model_name,
            "messages": ollama_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }
        if ollama_tools:
            chat_kwargs["tools"] = ollama_tools
        
        tool_calls_list = []
        async for chunk in self.ollama_client.chat(**chat_kwargs):
            logger.debug(f"Ollama chunk: {chunk}")
            if "message" in chunk:
                msg = chunk["message"]
                logger.debug(f"Ollama message: {msg}")
                # Extract content
                if msg.get("content"):
                    content = str(msg["content"])
                    if content and content != "None" and content != "undefined":
                        response_text += content
                # Extract tool calls if present
                if "tool_calls" in msg and msg["tool_calls"]:
                    logger.info(f"Found tool_calls in Ollama response: {msg['tool_calls']}")
                    tool_calls_list.extend(msg["tool_calls"])
            if chunk.get("done"):
                break
        
        # Create AI message with tool calls if any
        ai_message = AIMessage(content=response_text)
        if tool_calls_list:
            # Convert Ollama tool calls to LangChain format
            langchain_tool_calls = []
            for tc in tool_calls_list:
                try:
                    if isinstance(tc, dict):
                        # Handle different Ollama tool call formats
                        func_data = tc.get("function", tc)
                        if isinstance(func_data, dict):
                            name = func_data.get("name", "")
                            args_raw = func_data.get("arguments", {})
                            # Parse args if it's a string
                            if isinstance(args_raw, str):
                                try:
                                    args = json.loads(args_raw)
                                except:
                                    args = {"query": args_raw}
                            else:
                                args = args_raw
                        else:
                            name = tc.get("name", "")
                            args = tc.get("arguments", {})
                        
                        # Create ToolCall object
                        tool_call = ToolCall(
                            name=name,
                            args=args if isinstance(args, dict) else {},
                            id=tc.get("id", "")
                        )
                        langchain_tool_calls.append(tool_call)
                        logger.debug(f"Created ToolCall: name={name}, args={args}, id={tc.get('id', '')}")
                    elif isinstance(tc, ToolCall):
                        # Already a ToolCall object
                        langchain_tool_calls.append(tc)
                except Exception as e:
                    logger.error(f"Error creating ToolCall from {tc}: {e}", exc_info=True)
            
            if langchain_tool_calls:
                ai_message.tool_calls = langchain_tool_calls
                tool_names = [tc.name if hasattr(tc, 'name') else str(tc) for tc in langchain_tool_calls]
                logger.info(f"Detected {len(langchain_tool_calls)} tool call(s) in Ollama response: {tool_names}")
        
        # Create generation
        generation = ChatGeneration(message=ai_message)
        
        return ChatResult(generations=[generation])
    
    async def astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> AsyncIterator[BaseMessage]:
        """Stream responses."""
        
        # Convert LangChain messages to Ollama format
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                ollama_messages.append(_human_message_to_ollama(msg))
            elif isinstance(msg, AIMessage):
                ollama_messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                ollama_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                ollama_messages.append({"role": "assistant", "content": f"Tool result: {msg.content}"})
        
        # Convert tools to Ollama format if bound
        ollama_tools = self._convert_tools_to_ollama_format()
        
        # Stream response
        chat_kwargs = {
            "model": self.model_name,
            "messages": ollama_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }
        if ollama_tools:
            chat_kwargs["tools"] = ollama_tools
        
        accumulated_content = ""
        tool_calls_list = []
        async for chunk in self.ollama_client.chat(**chat_kwargs):
            logger.debug(f"Ollama streaming chunk: {chunk}")
            if "message" in chunk:
                msg = chunk["message"]
                logger.debug(f"Ollama streaming message: {msg}")
                # Extract content
                if msg.get("content"):
                    content = str(msg["content"])
                    if content and content != "None" and content != "undefined":
                        accumulated_content += content
                # Extract tool calls if present
                if "tool_calls" in msg and msg["tool_calls"]:
                    logger.info(f"Found tool_calls in Ollama streaming response: {msg['tool_calls']}")
                    tool_calls_list.extend(msg["tool_calls"])
            
            # Yield incremental content updates
            if accumulated_content:
                ai_msg = AIMessage(content=accumulated_content)
                # Add tool calls if we have them
                if tool_calls_list:
                    langchain_tool_calls = []
                    for tc in tool_calls_list:
                        try:
                            if isinstance(tc, dict):
                                # Handle different Ollama tool call formats
                                func_data = tc.get("function", tc)
                                if isinstance(func_data, dict):
                                    name = func_data.get("name", "")
                                    args_raw = func_data.get("arguments", {})
                                    # Parse args if it's a string
                                    if isinstance(args_raw, str):
                                        try:
                                            args = json.loads(args_raw)
                                        except:
                                            args = {"query": args_raw}
                                    else:
                                        args = args_raw
                                else:
                                    name = tc.get("name", "")
                                    args = tc.get("arguments", {})
                                
                                # Create ToolCall object
                                tool_call = ToolCall(
                                    name=name,
                                    args=args if isinstance(args, dict) else {},
                                    id=tc.get("id", "")
                                )
                                langchain_tool_calls.append(tool_call)
                                logger.debug(f"Created ToolCall in stream: name={name}, args={args}, id={tc.get('id', '')}")
                            elif isinstance(tc, ToolCall):
                                # Already a ToolCall object
                                langchain_tool_calls.append(tc)
                        except Exception as e:
                            logger.error(f"Error creating ToolCall from {tc}: {e}", exc_info=True)
                    
                    if langchain_tool_calls:
                        ai_msg.tool_calls = langchain_tool_calls
                        tool_names = [tc.name if hasattr(tc, 'name') else str(tc) for tc in langchain_tool_calls]
                        logger.info(f"Added {len(langchain_tool_calls)} tool call(s) to streaming message: {tool_names}")
                yield ai_msg
            
            if chunk.get("done"):
                break
    
    def bind_tools(
        self,
        tools: Union[List[BaseTool], List[Dict], BaseTool, Dict],
        **kwargs: Any,
    ) -> "OllamaChatModel":
        """Bind tools to the model. Returns a new model instance with tools bound."""
        # Convert tools to list if needed
        if isinstance(tools, (BaseTool, dict)):
            tools = [tools]
        
        # Convert dict tools to BaseTool if needed
        tool_list = []
        for tool in tools:
            if isinstance(tool, dict):
                # Skip dict tools for now - they'll be handled by the agent
                continue
            elif isinstance(tool, BaseTool):
                tool_list.append(tool)
        
        # Create a new instance with bound tools
        new_model = self.__class__(
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            base_url=self.base_url
        )
        new_model.bound_tools = tool_list if tool_list else None
        
        return new_model
    
    def _convert_tools_to_ollama_format(self) -> Optional[List[Dict]]:
        """Convert bound tools to Ollama's tool format."""
        if not self.bound_tools:
            return None
        
        ollama_tools = []
        for tool in self.bound_tools:
            # Get tool schema
            tool_schema = {}
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # Use Pydantic v2 method if available, fallback to v1
                    if hasattr(tool.args_schema, 'model_json_schema'):
                        tool_schema = tool.args_schema.model_json_schema()
                    elif hasattr(tool.args_schema, 'schema'):
                        tool_schema = tool.args_schema.schema()
                    else:
                        tool_schema = {"type": "object", "properties": {}}
                except Exception:
                    # Fallback to empty schema
                    tool_schema = {"type": "object", "properties": {}}
            
            # Convert to Ollama format
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool_schema
                }
            }
            ollama_tools.append(ollama_tool)
        
        return ollama_tools if ollama_tools else None

