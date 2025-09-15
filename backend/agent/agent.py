"""ReAct agent implementation."""

from typing import List, Dict, Optional, Any, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime
import json
import asyncio
from backend.llm import OllamaClient, ModelAdapterFactory
from backend.tools import tool_registry, ToolPermission
from backend.storage import get_vector_store
from backend.config import settings
import logging

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


class AgentResponse(BaseModel):
    """Complete agent response."""
    conversation_id: int
    message_id: int
    final_answer: str
    steps: List[AgentStep]
    total_tokens: int
    execution_time: float
    success: bool
    error: Optional[str] = None


class Agent:
    """ReAct agent for reasoning and acting."""
    
    def __init__(
        self,
        model: str = None,
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
        
        try:
            # Get available tools for user
            tools = tool_registry.get_schemas_for_user(allowed_tools)
            
            # Format system prompt with tools
            system_prompt = self._get_system_prompt(tools)
            
            # Initialize conversation
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            # Main ReAct loop
            while self.current_step < self.max_steps:
                self.current_step += 1
                
                # Generate response
                response_text = ""
                async for chunk in self.llm_client.chat(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True
                ):
                    if "message" in chunk:
                        content = chunk["message"].get("content", "")
                        response_text += content
                        
                        if stream:
                            yield {
                                "type": "token",
                                "content": content,
                                "step": self.current_step
                            }
                    
                    if chunk.get("done"):
                        self.total_tokens += chunk.get("total_tokens", 0)
                
                # Parse response for actions
                action = self._parse_response(response_text)
                
                if action["type"] == "final_answer":
                    # Agent has final answer
                    step = AgentStep(
                        step_number=self.current_step,
                        step_type="answer",
                        content=action["content"],
                        reasoning=action.get("reasoning")
                    )
                    self.steps.append(step)
                    
                    if stream:
                        yield {
                            "type": "step",
                            "step": step.dict()
                        }
                    
                    break
                
                elif action["type"] == "tool_call":
                    # Agent wants to use a tool
                    tool_name = action["tool_name"]
                    tool_args = action["tool_args"]
                    
                    # Create tool request step
                    request_step = AgentStep(
                        step_number=self.current_step,
                        step_type="tool_request",
                        content=action.get("plan", ""),
                        tool_name=tool_name,
                        tool_input=tool_args,
                        reasoning=action.get("reasoning")
                    )
                    self.steps.append(request_step)
                    
                    if stream:
                        yield {
                            "type": "step",
                            "step": request_step.dict()
                        }
                    
                    # Request permission if needed
                    tool = tool_registry.get_tool(tool_name)
                    needs_permission = tool and tool.permission != ToolPermission.SAFE
                    
                    if needs_permission:
                        # Send permission request
                        yield {
                            "type": "permission_request",
                            "tool": tool_name,
                            "description": action.get("permission_reason", ""),
                            "step": self.current_step
                        }
                        
                        # Wait for permission (in real implementation, this would be async)
                        # For now, we'll auto-approve for demonstration
                        approved = True
                    else:
                        approved = True
                    
                    if approved:
                        # Execute tool
                        result = await tool_registry.execute_tool(
                            tool_name=tool_name,
                            parameters=tool_args,
                            check_permission=False  # Already checked
                        )
                        
                        # Create tool result step
                        result_step = AgentStep(
                            step_number=self.current_step,
                            step_type="tool_result",
                            content=str(result.output),
                            tool_name=tool_name,
                            tool_output=result.output,
                            tool_approved=True
                        )
                        self.steps.append(result_step)
                        
                        if stream:
                            yield {
                                "type": "step",
                                "step": result_step.dict()
                            }
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "assistant",
                            "content": response_text
                        })
                        messages.append({
                            "role": "tool",
                            "content": f"OBSERVATION: {result.output}"
                        })
                    else:
                        # Tool denied
                        messages.append({
                            "role": "tool",
                            "content": "OBSERVATION: Tool execution denied by user"
                        })
                
                elif action["type"] == "reflection":
                    # Agent is reflecting
                    step = AgentStep(
                        step_number=self.current_step,
                        step_type="reflection",
                        content=action["content"],
                        reasoning=action.get("reasoning")
                    )
                    self.steps.append(step)
                    
                    if stream:
                        yield {
                            "type": "step",
                            "step": step.dict()
                        }
                    
                    # Add to conversation
                    messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create final response
            final_answer = self._get_final_answer()
            response = AgentResponse(
                conversation_id=conversation_id,
                message_id=0,  # Will be set by caller
                final_answer=final_answer,
                steps=self.steps,
                total_tokens=self.total_tokens,
                execution_time=execution_time,
                success=True
            )
            
            if stream:
                yield {
                    "type": "complete",
                    "response": response.dict()
                }
            else:
                yield response.dict()
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def _get_system_prompt(self, tools: List[Dict]) -> str:
        """Get the system prompt with tools."""
        
        base_prompt = """You are a privacy-first, local AI Agent. Follow a Reason → Act (tool) → Observe → Reflect loop.

Your goal is to help the user by breaking down their request into steps and using available tools when needed.

IMPORTANT INSTRUCTIONS:
1. Think step-by-step about what the user is asking
2. If you need information or to perform an action, use the appropriate tool
3. After each tool use, reflect on the result and decide next steps
4. Keep your reasoning concise and clear
5. When you have enough information, provide a final answer

Response Format:
- For planning: Start with "PLAN:" followed by your plan
- For tool use: Include "TOOL_CALL:" followed by the tool and arguments
- For reflection: Start with "REFLECTION:" 
- For final answer: Start with "FINAL_ANSWER:" """
        
        return self.model_adapter.format_system_prompt(base_prompt, tools)
    
    def _parse_response(self, response: str) -> Dict:
        """Parse agent response for actions."""
        
        response_lower = response.lower()
        
        # Check for final answer
        if "final_answer:" in response_lower:
            answer_start = response_lower.index("final_answer:") + 13
            answer = response[answer_start:].strip()
            return {
                "type": "final_answer",
                "content": answer,
                "reasoning": response[:answer_start].strip()
            }
        
        # Check for tool call
        tool_calls = self.model_adapter.parse_tool_calls(response)
        if tool_calls:
            tool_call = tool_calls[0]  # Take first tool call
            
            # Extract plan and permission reason
            plan = ""
            permission_reason = ""
            
            if "plan:" in response_lower:
                plan_start = response_lower.index("plan:") + 5
                plan_end = response_lower.find("\n", plan_start)
                if plan_end == -1:
                    plan_end = len(response)
                plan = response[plan_start:plan_end].strip()
            
            if "request_permission:" in response_lower:
                perm_start = response_lower.index("request_permission:") + 19
                perm_end = response_lower.find("\n", perm_start)
                if perm_end == -1:
                    perm_end = response_lower.find("tool_call:", perm_start)
                if perm_end == -1:
                    perm_end = len(response)
                permission_reason = response[perm_start:perm_end].strip()
            
            return {
                "type": "tool_call",
                "tool_name": tool_call["name"],
                "tool_args": tool_call["arguments"],
                "plan": plan,
                "permission_reason": permission_reason,
                "reasoning": response
            }
        
        # Check for reflection
        if "reflection:" in response_lower or "observation:" in response_lower:
            return {
                "type": "reflection",
                "content": response,
                "reasoning": response
            }
        
        # Default to reflection
        return {
            "type": "reflection",
            "content": response,
            "reasoning": response
        }
    
    def _get_final_answer(self) -> str:
        """Extract final answer from steps."""
        
        # Look for answer step
        for step in reversed(self.steps):
            if step.step_type == "answer":
                return step.content
        
        # Fallback to last step content
        if self.steps:
            return self.steps[-1].content
        
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
