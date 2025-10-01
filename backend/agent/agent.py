"""AI Agent implementation with automatic tool selection."""

from typing import List, Dict, Optional, Any, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio


from backend.llm import OllamaClient, ModelAdapterFactory
from backend.tools import tool_registry, ToolPermission
from backend.storage import get_vector_store
from backend.config import settings
from backend.agent.tool_selector import ToolSelector
import logging


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

logger = logging.getLogger(__name__)


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

    def dict(self, *args, **kwargs):
        """Override dict to handle datetime serialization."""
        d = super().dict(*args, **kwargs)
        # Handle datetime serialization for any datetime fields
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
        return d


class AgentResponse(BaseModel):
    """Complete agent response."""
    conversation_id: int
    user_id: int
    query: str
    final_answer: str
    steps: List[AgentStep]
    total_tokens: int
    execution_time: float
    success: bool
    error: Optional[str] = None

    def dict(self, *args, **kwargs):
        """Override dict to handle datetime serialization in steps."""
        d = super().dict(*args, **kwargs)
        if "steps" in d:
            d["steps"] = [
                step.dict(*args, **kwargs) if isinstance(step, AgentStep) else step
                for step in d["steps"]
            ]
        # Handle datetime serialization for any datetime fields
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
        return d


class Agent:
    """AI Agent with automatic tool selection."""
    
    def __init__(
        self,
        model: str = "qwen3:latest",
        temperature: float = 0.7,
        max_steps: int = 10,
        max_tokens: int = 2000
    ):
        """Initialize the agent."""
        self.model = model or settings.DEFAULT_MODEL
        self.temperature = temperature
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        
        # Initialize components
        self.llm_client = OllamaClient()
        self.model_adapter = ModelAdapterFactory.get_adapter(self.model)
        self.vector_store = get_vector_store()
        self.tool_selector = ToolSelector()
        
        # Track execution state
        self.steps: List[AgentStep] = []
        self.total_tokens = 0
        self.current_step = 0
    
    async def run(
        self,
        query: str,
        conversation_id: int,
        user_id: int,
        allowed_tools: List[str],
        stream: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """Run the agent with a query."""
        
        start_time = datetime.utcnow()
        self.steps = []
        self.current_step = 0
        self._current_query = query  # Store query for forced tool calls
        
        try:
            # Step 1: If multiple tools are available, build a multi-step plan; otherwise single-tool logic
            planned_steps: List[Dict[str, Any]] = []
            if allowed_tools and len(allowed_tools) > 1:
                plan = await self.tool_selector.plan_tools(query, allowed_tools)
                if plan:
                    # Execute each planned tool step-by-step
                    for tool_name, suggested_args in plan:
                        async for result in self._execute_selected_tool(tool_name, suggested_args, stream):
                            yield result
                    # After running plan, produce final answer
                    end_time = datetime.utcnow()
                    final_answer = self._get_final_answer()
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
                        ).dict(),
                    }
                    yield serialize_datetime(response_dict)
                    return

            # Fallback single-tool selection
            if allowed_tools and len(allowed_tools) == 1:
                forced_tool = allowed_tools[0]
                suggested_args: Dict[str, Any] = {}
                q_lower = (query or "").strip()
                if forced_tool in ["search_local_files", "rag_search", "web_search"]:
                    suggested_args["query"] = q_lower
                tool_selection = (forced_tool, suggested_args)
            else:
                tool_selection = await self.tool_selector.analyze_query(query, allowed_tools)
            
            # If a tool was explicitly selected in the UI but the selector returned None,
            # force using the first selected tool with sensible default arguments.
            if not tool_selection and allowed_tools:
                forced_tool = allowed_tools[0]
                suggested_args: Dict[str, Any] = {}
                q_lower = (query or "").strip()
                if forced_tool in ["search_local_files", "rag_search", "web_search"]:
                    suggested_args["query"] = q_lower
                # If we cannot infer required params, fall back to selector/LLM
                if suggested_args:
                    logger.info(f"Forcing tool '{forced_tool}' with args inferred from query")
                    tool_selection = (forced_tool, suggested_args)
            
            if not tool_selection:
                # No tool selected or forced, provide a direct response
                direct_response = await self._generate_direct_response(query)
                
                step = AgentStep(
                    step_number=1,
                    step_type="answer",
                    content=direct_response,
                    reasoning="No specific tool required for this query"
                )
                self.steps.append(step)
                
                if stream:
                    yield {
                        "type": "step",
                        "step": serialize_datetime(step.dict())
                    }
                
                # Create final response
                end_time = datetime.utcnow()
                response_dict = {
                    "type": "complete",
                    "response": AgentResponse(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        query=query,
                        steps=self.steps,
                        final_answer=direct_response,
                        total_tokens=self.total_tokens,
                        execution_time=(end_time - start_time).total_seconds(),
                        success=True
                    ).dict()
                }
                
                yield serialize_datetime(response_dict)
                return
            
            # Step 2: Execute the selected tool
            selected_tool, suggested_args = tool_selection
            
            # Ensure query parameter is present for search tools
            if selected_tool in ["search_local_files", "rag_search"] and "query" not in suggested_args:
                # Extract search terms from the original query as fallback
                suggested_args["query"] = query.strip()
                logger.info(f"Added fallback query parameter: {suggested_args['query']}")
            
            async for result in self._execute_selected_tool(selected_tool, suggested_args, stream):
                yield result
            
            # Create final response
            end_time = datetime.utcnow()
            final_answer = self._get_final_answer()
            
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
                    success=True
                ).dict()
            }
            
            yield serialize_datetime(response_dict)
            return
        
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def _get_system_prompt(self, tools: List[Dict]) -> str:
        """Get the system prompt with tools."""
        
        base_prompt = """You are a helpful AI Agent. Your job is to help users by using tools when needed.

IMPORTANT: When a user asks you to search, find, or get information, you MUST use a tool immediately. Don't just think about it - DO IT!

FORMAT FOR USING TOOLS:
Use this EXACT format (no variations):

TOOL_CALL: search_local_files
{"query": "bug", "top_k": 5}

AVAILABLE TOOLS:
- search_local_files: Search local files for content
- web_search: Search the internet
- read_file: Read a specific file
- get_system_info: Get system information
- analyze_code: Analyze code files
- scrape_webpage: Extract content from web pages

EXAMPLE:
User: "search local files for bug"
Your response: 
TOOL_CALL: search_local_files
{"query": "bug", "top_k": 5}

DO NOT just think about using tools - USE THEM immediately when the user asks for information!

- Note: If the User Query is in Persian, the response MUST be in Persian. even if it contains a single persian letter."""
        
        return self.model_adapter.format_system_prompt(base_prompt, tools)
    
    def _parse_response(self, response: str) -> Dict:
        """Parse agent response for actions."""
        
        # Clean the response to remove any thinking tags first
        cleaned_response = self._clean_response_text(response)
        
        response_lower = cleaned_response.lower()
        
        # Continue with normal parsing on the cleaned response
        working_response_lower = response_lower
        
        # Special case: If user asked to search but model is just thinking, force a tool call
        original_query = getattr(self, '_current_query', '').lower()
        if (original_query and 
            ('search' in original_query or 'find' in original_query) and 
            'local files' in original_query and
            not cleaned_response and  # No remaining response after thinking
            not any(pattern in response.lower() for pattern in ['tool_call:', 'final_answer:'])):
            
            # Extract search term from query
            search_term = "bug"  # Default, but try to extract
            if 'for ' in original_query:
                search_term = original_query.split('for ')[-1].strip()
            
            return {
                "type": "tool_call",
                "tool_name": "search_local_files", 
                "tool_args": {"query": search_term, "top_k": 5},
                "plan": f"Search local files for '{search_term}'",
                "reasoning": "User requested to search local files"
            }
        
        # Check for final answer
        if "final_answer:" in working_response_lower:
            answer_start = working_response_lower.index("final_answer:") + 13
            answer = cleaned_response[answer_start:].strip()
            return {
                "type": "final_answer",
                "content": answer,
                "reasoning": cleaned_response[:answer_start].strip()
            }
        
        # Check for tool call
        logger.debug(f"Checking for tool calls in cleaned_response: {cleaned_response}")
        tool_calls = self.model_adapter.parse_tool_calls(cleaned_response)
        logger.debug(f"Parsed tool calls: {tool_calls}")
        if tool_calls:
            tool_call = tool_calls[0]  # Take first tool call
            logger.debug(f"Using tool call: {tool_call}")
            
            # Extract plan and permission reason
            plan = ""
            permission_reason = ""
            
            if "plan:" in response_lower:
                plan_start = response_lower.index("plan:") + 5
                plan_end = response_lower.find("\n", plan_start)
                if plan_end == -1:
                    plan_end = len(cleaned_response)
                plan = cleaned_response[plan_start:plan_end].strip()
            
            if "request_permission:" in response_lower:
                perm_start = response_lower.index("request_permission:") + 19
                perm_end = response_lower.find("\n", perm_start)
                if perm_end == -1:
                    perm_end = response_lower.find("tool_call:", perm_start)
                if perm_end == -1:
                    perm_end = len(cleaned_response)
                permission_reason = cleaned_response[perm_start:perm_end].strip()
            
            return {
                "type": "tool_call",
                "tool_name": tool_call["name"],
                "tool_args": tool_call["arguments"],
                "plan": plan,
                "permission_reason": permission_reason,
                "reasoning": cleaned_response
            }
        
        # Check for reflection
        if "reflection:" in response_lower or "observation:" in response_lower:
            return {
                "type": "reflection",
                "content": cleaned_response,
                "reasoning": cleaned_response
            }
        
        # Default to reflection
        return {
            "type": "reflection",
            "content": cleaned_response,
            "reasoning": cleaned_response
        }
    
    def _get_final_answer(self) -> str:
        """Extract final answer from steps."""
        
        logger.debug(f"Extracting final answer from {len(self.steps)} steps")
        for i, step in enumerate(self.steps):
            logger.debug(f"Step {i}: type={step.step_type}, content_preview={step.content[:100] if step.content else 'None'}...")
        
        # Look for answer step
        for step in reversed(self.steps):
            if step.step_type == "answer":
                logger.debug(f"Found answer step: {step.content}")
                return self._clean_response_text(step.content)
        
        # Look for final answer in reflection content
        for step in reversed(self.steps):
            if step.step_type == "reflection" and step.content:
                content_lower = step.content.lower()
                if "final_answer:" in content_lower:
                    answer_start = content_lower.index("final_answer:") + 13
                    answer = step.content[answer_start:].strip()
                    if answer:
                        return self._clean_response_text(answer)
        
        # If we have thinking steps, look for the last non-thinking step as the answer
        non_thinking_steps = [step for step in self.steps if step.step_type != "thinking"]
        logger.debug(f"Found {len(non_thinking_steps)} non-thinking steps")
        if non_thinking_steps:
            last_step = non_thinking_steps[-1]
            logger.debug(f"Last non-thinking step: type={last_step.step_type}, content={last_step.content[:100] if last_step.content else 'None'}...")
            # If it's a reflection step that doesn't contain tool calls, treat it as the answer
            if (last_step.step_type == "reflection" and 
                last_step.content and 
                "tool_call:" not in last_step.content.lower() and
                not last_step.tool_name):
                logger.debug(f"Using reflection step as final answer: {last_step.content}")
                return self._clean_response_text(last_step.content)
        
        # Fallback to last step content
        if self.steps:
            return self._clean_response_text(self.steps[-1].content)
        
        return "No answer generated"
    
    async def save_to_memory(
        self,
        conversation_id: int,
        message: str,
        metadata: Dict
    ):
        """Save message to vector memory."""
        
        try:
            # Generate embedding and save
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
            # Search for relevant messages
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
    
    async def _generate_direct_response(self, query: str) -> str:
        """Generate a direct response when no tool is needed."""
        try:
            async def _run() -> str:
                response_text = ""
                async for chunk in self.llm_client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": query}],
                    temperature=self.temperature,
                    max_tokens=min(self.max_tokens, 512),
                    stream=False
                ):
                    if "message" in chunk and chunk["message"].get("content"):
                        content = str(chunk["message"]["content"])
                        if content and content != "None" and content != "undefined":
                            response_text += content
                    if chunk.get("done"):
                        break
                return response_text

            # Use configurable timeout from settings with a small safety buffer
            step_timeout = getattr(settings, "STEP_TIMEOUT_SECONDS", 30)
            response_text = await asyncio.wait_for(_run(), timeout=step_timeout + 5)

            cleaned_response = self._clean_response_text(response_text)
            return cleaned_response if cleaned_response else "I couldn't generate a response."

        except Exception as e:
            logger.error(f"Error generating direct response: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def _execute_selected_tool(self, tool_name: str, tool_args: Dict, stream: bool = True):
        """Execute the selected tool with the given arguments."""
        try:
            # Create tool request step
            request_step = AgentStep(
                step_number=1,
                step_type="tool_request",
                content=f"Using {tool_name} tool",
                tool_name=tool_name,
                tool_input=tool_args,
                reasoning=f"Selected {tool_name} as the most appropriate tool for this query"
            )
            self.steps.append(request_step)
            
            if stream:
                yield {
                    "type": "step",
                    "step": serialize_datetime(request_step.dict())
                }
            
            # Execute the tool
            tool = tool_registry.get_tool(tool_name)
            if not tool:
                error_msg = f"Tool '{tool_name}' not found in registry"
                error_step = AgentStep(
                    step_number=2,
                    step_type="error",
                    content=error_msg,
                    reasoning="Tool execution failed"
                )
                self.steps.append(error_step)
                
                if stream:
                    yield {
                        "type": "step", 
                        "step": serialize_datetime(error_step.dict())
                    }
                return
            
            # Check permissions
            if tool.permission != ToolPermission.SAFE:
                # For now, auto-approve all tools - in production you'd want proper permission handling
                pass
            
            # Execute tool
            tool_result = await tool.execute(**tool_args)
            
            # Create tool result step
            result_step = AgentStep(
                step_number=2,
                step_type="tool_result",
                content=str(tool_result.output) if tool_result.success else f"Error: {tool_result.error}",
                tool_name=tool_name,
                tool_output=tool_result.dict(),
                reasoning="Tool execution completed"
            )
            self.steps.append(result_step)
            
            if stream:
                yield {
                    "type": "step",
                    "step": serialize_datetime(result_step.dict())
                }
            
            # Generate final response based on tool result
            if tool_result.success:
                final_answer = await self._generate_response_from_tool_result(tool_result, tool_name)
            else:
                final_answer = f"I encountered an error while using the {tool_name} tool: {tool_result.error}"
            
            # Create answer step
            answer_step = AgentStep(
                step_number=3,
                step_type="answer",
                content=final_answer,
                reasoning="Generated final response based on tool results"
            )
            self.steps.append(answer_step)
            
            if stream:
                yield {
                    "type": "step",
                    "step": serialize_datetime(answer_step.dict())
                }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            error_step = AgentStep(
                step_number=len(self.steps) + 1,
                step_type="error",
                content=f"Failed to execute {tool_name}: {str(e)}",
                reasoning="Tool execution error"
            )
            self.steps.append(error_step)
            
            if stream:
                yield {
                    "type": "step",
                    "step": serialize_datetime(error_step.dict())
                }
    
    def _clean_response_text(self, text: str) -> str:
        """Remove thinking tags and clean up response text."""
        import re
        
        # Remove <think></think> and <thinking></thinking> tags and their content
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up extra whitespace and newlines
        text = re.sub(r'\n\s*\n', '\n', text).strip()
        
        return text
    
    async def _generate_response_from_tool_result(self, tool_result: Any, tool_name: str) -> str:
        """Generate a natural language response from tool results."""
        try:
            # Simple rule-based response for search tools
            if tool_name == "search_local_files" and hasattr(tool_result, 'output'):
                output_data = tool_result.output
                if isinstance(output_data, dict) and output_data.get('results'):
                    results = output_data['results']
                    if results:
                        response_parts = []
                        response_parts.append(f"بر اساس جستجو در فایل‌ها، {len(results)} نتیجه پیدا شد:")
                        
                        for i, result in enumerate(results[:3], 1):  # Show top 3 results
                            file_name = result.get('file_name', 'نامشخص')
                            content = result.get('content', '')
                            response_parts.append(f"\n{i}. فایل: {file_name}")
                            response_parts.append(f"   محتوا: {content}")
                        
                        return "\n".join(response_parts)
                    else:
                        return "متأسفم، هیچ نتیجه‌ای در فایل‌ها پیدا نشد."
            
            # Fallback to LLM for other tools
            prompt = f"""A user asked a question and I used the '{tool_name}' tool to help answer it. 

Tool Result:
{json.dumps(tool_result.output, indent=2) if hasattr(tool_result, 'output') else str(tool_result)}

Please provide a clear, helpful response to the user based on these results. Be concise but informative.

- Note: If the User Query is in Persian, the response MUST be in Persian. even if it contains a single persian letter.

"""

            async def _run() -> str:
                response_text = ""
                async for chunk in self.llm_client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=min(self.max_tokens, 400),
                    stream=False
                ):
                    if "message" in chunk and chunk["message"].get("content"):
                        content = str(chunk["message"]["content"])
                        if content and content != "None" and content != "undefined":
                            response_text += content
                    if chunk.get("done"):
                        break
                return response_text

            step_timeout = getattr(settings, "STEP_TIMEOUT_SECONDS", 30)
            response_text = await asyncio.wait_for(_run(), timeout=step_timeout + 5)

            cleaned_response = self._clean_response_text(response_text)
            return cleaned_response if cleaned_response else f"I used the {tool_name} tool and got results."
            
        except Exception as e:
            logger.error(f"Error generating response from tool result: {e}")
            return f"I successfully used the {tool_name} tool, but encountered an error formatting the response: {str(e)}"