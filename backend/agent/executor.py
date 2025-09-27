"""Agent executor for managing agent instances."""

from typing import Dict, Optional, AsyncGenerator
import asyncio
from backend.agent.agent import Agent, AgentResponse
from backend.models import User, Conversation, Message, AgentStep
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Manages agent execution for users."""
    
    def __init__(self):
        """Initialize the executor."""
        self.active_agents: Dict[int, Agent] = {}  # user_id -> Agent
        self.execution_locks: Dict[int, asyncio.Lock] = {}  # user_id -> Lock
        self.cancellation_tokens: Dict[int, asyncio.Event] = {}  # user_id -> CancellationEvent
    
    def get_agent_for_user(
        self,
        user: User,
        conversation_id: int
    ) -> Agent:
        """Get or create agent for user."""
        
        if user.id not in self.active_agents:
            # Create new agent with user preferences
            preferences = user.preferences or {}
            
            agent = Agent(
                model=preferences.get("model", "qwen3:latest"),
                temperature=preferences.get("temperature", 0.7),
                max_steps=preferences.get("max_steps", 10),
                max_tokens=preferences.get("max_tokens", 2000)
            )
            
            self.active_agents[user.id] = agent
            self.execution_locks[user.id] = asyncio.Lock()
        
        return self.active_agents[user.id]
    
    async def execute(
        self,
        user: User,
        conversation_id: int,
        message: str,
        db: Session,
        stream: bool = True,
        selected_tools: Optional[list] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute agent for user message."""
        
        # Create cancellation token for this execution
        cancellation_token = asyncio.Event()
        self.cancellation_tokens[user.id] = cancellation_token
        
        # Get agent and lock
        agent = self.get_agent_for_user(user, conversation_id)
        
        if user.id not in self.execution_locks:
            self.execution_locks[user.id] = asyncio.Lock()
        
        async with self.execution_locks[user.id]:
            try:
                # Save user message
                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message
                )
                db.add(user_msg)
                db.commit()
                
                # Determine which tools to use
                if selected_tools:
                    # Use selected tools from chat interface
                    tools_to_use = selected_tools
                    logger.info(f"Using selected tools: {tools_to_use}")
                else:
                    # Use user's allowed tools from permissions
                    tools_to_use = user.allowed_tools or []
                    logger.info(f"User {user.username} allowed_tools: {tools_to_use}")
                
                # Run agent
                async for event in agent.run(
                    query=message,
                    conversation_id=conversation_id,
                    user_id=user.id,
                    allowed_tools=tools_to_use,
                    stream=stream
                ):
                    # Check for cancellation before processing each event
                    if cancellation_token.is_set():
                        logger.info(f"Execution cancelled for user {user.id}")
                        yield {
                            "type": "cancelled",
                            "message": "Generation stopped by user"
                        }
                        return
                    
                    # Handle different event types
                    if event.get("type") == "token":
                        # Stream token to client
                        yield event
                    
                    elif event.get("type") == "step":
                        # Save detailed step to AgentStep table
                        step_data = event["step"]
                        
                        # Determine step type based on content
                        step_type = step_data.get("step_type", "unknown")
                        if step_data.get("tool_name"):
                            if step_data.get("tool_output") is not None:
                                step_type = "tool_result"
                            else:
                                step_type = "tool_request"
                        elif "thinking" in step_data.get("content", "").lower():
                            step_type = "thinking"
                        else:
                            step_type = "reflection"
                        
                        # Create detailed agent step record
                        agent_step = AgentStep(
                            conversation_id=conversation_id,
                            step_type=step_type,
                            step_number=step_data.get("step_number", 0),
                            title=step_data.get("title", ""),
                            content=step_data.get("content", ""),
                            tool_name=step_data.get("tool_name"),
                            tool_input=step_data.get("tool_input"),
                            tool_output=step_data.get("tool_output"),
                            tool_success=step_data.get("tool_success"),
                            tool_error=step_data.get("tool_error"),
                            execution_time=step_data.get("execution_time"),
                            tokens_used=step_data.get("tokens_used")
                        )
                        db.add(agent_step)
                        
                        # Also save as message for compatibility (simplified)
                        step_msg = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=step_data.get("content", ""),
                            tool_name=step_data.get("tool_name"),
                            tool_input=step_data.get("tool_input"),
                            tool_output=step_data.get("tool_output"),
                            tool_approved=step_data.get("tool_approved"),
                            reasoning=step_data.get("reasoning"),
                            step_number=step_data.get("step_number", 0)
                        )
                        db.add(step_msg)
                        db.commit()
                        
                        # Update step with message_id
                        agent_step.message_id = step_msg.id
                        db.commit()
                        
                        # Stream step to client
                        yield event
                    
                    elif event.get("type") == "permission_request":
                        # Stream permission request to client
                        yield event
                        
                        # In real implementation, wait for client response
                        # For now, auto-approve after a short delay
                        await asyncio.sleep(0.5)
                    
                    elif event.get("type") == "complete":
                        # Save final response
                        response_data = event["response"]
                        
                        # Update conversation
                        conversation = db.query(Conversation).filter(
                            Conversation.id == conversation_id
                        ).first()
                        
                        if conversation:
                            conversation.total_messages += len(response_data["steps"]) + 1
                            conversation.total_tokens += response_data["total_tokens"]
                            db.commit()
                        
                        # Save to vector memory
                        await agent.save_to_memory(
                            conversation_id=conversation_id,
                            message=response_data["final_answer"],
                            metadata={
                                "role": "assistant",
                                "user_id": user.id,
                                "tokens": response_data["total_tokens"]
                            }
                        )
                        
                        yield event
                    
                    elif event.get("type") == "error":
                        # Log error and stream to client
                        logger.error(f"Agent error: {event['error']}")
                        yield event
                
            except Exception as e:
                logger.error(f"Executor error: {e}")
                yield {
                    "type": "error",
                    "error": str(e)
                }
            finally:
                # Clean up cancellation token
                if user.id in self.cancellation_tokens:
                    del self.cancellation_tokens[user.id]
    
    def clear_agent(self, user_id: int):
        """Clear agent for user."""
        if user_id in self.active_agents:
            del self.active_agents[user_id]
        if user_id in self.execution_locks:
            del self.execution_locks[user_id]
        if user_id in self.cancellation_tokens:
            # Set the cancellation token to stop current execution
            self.cancellation_tokens[user_id].set()
            del self.cancellation_tokens[user_id]
    
    def clear_all_agents(self):
        """Clear all active agents."""
        # Set all cancellation tokens before clearing
        for token in self.cancellation_tokens.values():
            token.set()
        self.active_agents.clear()
        self.execution_locks.clear()
        self.cancellation_tokens.clear()


# Global executor instance
agent_executor = AgentExecutor()
