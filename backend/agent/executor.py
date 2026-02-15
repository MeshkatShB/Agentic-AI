"""Agent executor for managing agent instances."""

from typing import Dict, Optional, AsyncGenerator
import asyncio
from backend.agent.agent import Agent, AgentResponse
from backend.agent.deepagent import DeepAgentWrapper
from backend.tools import tool_registry
from backend.models import User, Conversation, Message, AgentStep
from backend.config import settings
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Manages agent execution for users."""
    
    def __init__(self):
        """Initialize the executor."""
        self.active_agents: Dict[str, Agent] = {}  # agent_key (e.g., "1_langchain") -> Agent
        self.execution_locks: Dict[str, asyncio.Lock] = {}  # agent_key -> Lock
        self.cancellation_tokens: Dict[int, asyncio.Event] = {}  # user_id -> CancellationEvent
    
    def get_agent_for_user(
        self,
        user: User,
        conversation_id: int,
        use_deepagent: bool = False,
        db: Optional[Session] = None
    ) -> Agent:
        """Get or create agent for user."""
        
        # Refresh user object to ensure we have latest preferences
        # (user object might be stale if it came from a previous request)
        if db is not None:
            db.refresh(user)
        
        # Get API configuration to determine provider
        preferences = user.preferences or {}
        api_config = preferences.get("api_config", {})
        llm_provider = api_config.get("llm_provider", "ollama")
        
        # Include provider in agent key so changing providers creates a new agent
        agent_key = f"{user.id}_{'deepagent' if use_deepagent else 'langchain'}_{llm_provider}"
        
        if agent_key not in self.active_agents:
            # Create new agent with user preferences
            model = preferences.get("model", settings.DEFAULT_MODEL)
            
            # Get API keys from environment if not in user config
            from backend.config import settings as app_settings
            if not api_config.get("openai_api_key") and app_settings.OPENAI_API_KEY:
                api_config["openai_api_key"] = app_settings.OPENAI_API_KEY
            if not api_config.get("deepseek_api_key") and app_settings.DEEPSEEK_API_KEY:
                api_config["deepseek_api_key"] = app_settings.DEEPSEEK_API_KEY
            if not api_config.get("mistral_api_key") and app_settings.MISTRAL_API_KEY:
                api_config["mistral_api_key"] = app_settings.MISTRAL_API_KEY
            if not api_config.get("gemini_api_key") and app_settings.GEMINI_API_KEY:
                api_config["gemini_api_key"] = app_settings.GEMINI_API_KEY
            
            logger.info(f"Creating agent for user {user.username} with provider '{llm_provider}', model '{model}' (preferences: {preferences})")
            
            if use_deepagent:
                try:
                    from backend.agent.deepagent import DeepAgentWrapper, DEEPAGENTS_AVAILABLE
                    if not DEEPAGENTS_AVAILABLE:
                        raise ImportError("DeepAgents package is not installed")
                    agent = DeepAgentWrapper(model=model)
                except (ImportError, Exception) as e:
                    logger.warning(f"DeepAgent not available ({str(e)}), falling back to LangChain agent")
                    agent = Agent(
                        model=model,
                        temperature=preferences.get("temperature", settings.MODEL_TEMPERATURE),
                        max_steps=preferences.get("max_steps", settings.MAX_STEPS_PER_REQUEST),
                        max_tokens=preferences.get("max_tokens", settings.MAX_TOKENS_PER_STEP),
                        api_config=api_config
                    )
            else:
                agent = Agent(
                    model=model,
                    temperature=preferences.get("temperature", settings.MODEL_TEMPERATURE),
                    max_steps=preferences.get("max_steps", settings.MAX_STEPS_PER_REQUEST),
                    max_tokens=preferences.get("max_tokens", settings.MAX_TOKENS_PER_STEP),
                    api_config=api_config
                )
            
            self.active_agents[agent_key] = agent
            self.execution_locks[agent_key] = asyncio.Lock()
        
        return self.active_agents[agent_key]
    
    async def execute(
        self,
        user: User,
        conversation_id: int,
        message: str,
        db: Session,
        stream: bool = True,
        selected_tools: Optional[list] = None,
        use_deepagent: bool = False,
        file_attachments: Optional[list] = None,
        image_base64_list: Optional[list] = None,
        tool_overrides: Optional[list] = None,
        mcp_server_ids_override: Optional[list] = None,
        use_tool_selector_middleware: Optional[bool] = None,
        invocation_source: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        """Execute agent for user message. tool_overrides/... for Telegram. invocation_source e.g. 'telegram' for tool context."""
        
        # Create cancellation token for this execution
        cancellation_token = asyncio.Event()
        self.cancellation_tokens[user.id] = cancellation_token
        
        # Get agent and lock (pass db to ensure fresh user preferences)
        agent = self.get_agent_for_user(user, conversation_id, use_deepagent=use_deepagent, db=db)
        
        # Get provider for agent key
        preferences = user.preferences or {}
        api_config = preferences.get("api_config", {})
        llm_provider = api_config.get("llm_provider", "ollama")
        agent_key = f"{user.id}_{'deepagent' if use_deepagent else 'langchain'}_{llm_provider}"
        if agent_key not in self.execution_locks:
            self.execution_locks[agent_key] = asyncio.Lock()
        
        async with self.execution_locks[agent_key]:
            try:
                # Save user message with file attachments
                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    file_attachments=file_attachments if file_attachments else None
                )
                db.add(user_msg)
                db.commit()
                
                # Check if this is the first user message in the conversation
                # If so, generate a title based on the message (run in background)
                user_message_count = db.query(Message).filter(
                    Message.conversation_id == conversation_id,
                    Message.role == "user"
                ).count()
                
                # Track title generation task for first message
                title_task = None
                if user_message_count == 1:
                    # This is the first message - generate a title in the background
                    # Create a task that will return the generated title when complete
                    title_task = asyncio.create_task(
                        self._generate_conversation_title(
                            conversation_id=conversation_id,
                            first_message=message,
                            user_id=user.id
                        )
                    )
                
                # Ensure user's active custom tools are registered
                try:
                    registered = tool_registry.register_custom_tools_for_user(db, user.id)
                    logger.info(f"Registered {registered} custom tools for user {user.username}")
                except Exception as reg_err:
                    logger.warning(f"Failed to register custom tools for user {user.id}: {reg_err}")

                # Resolve which tools to use: Telegram request or Telegram conversation overrides UI
                if tool_overrides is not None:
                    tools_to_use = list(tool_overrides)
                    logger.info(f"Using overridden tools (e.g. Telegram): {tools_to_use}")
                else:
                    # If this is the Telegram conversation (same chat used by Telegram bot), use Telegram tool settings
                    conv = db.query(Conversation).filter(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user.id,
                    ).first()
                    is_telegram_conversation = conv and (conv.title or "").strip() == "Telegram"
                    if is_telegram_conversation:
                        prefs = user.preferences or {}
                        telegram_tools = prefs.get("telegram_tools")
                        if telegram_tools is not None:
                            tools_to_use = list(telegram_tools)
                            logger.info(f"Using Telegram conversation tools (from settings): {tools_to_use}")
                        else:
                            tools_to_use = user.allowed_tools or []
                            logger.info(f"Using Telegram conversation tools (all allowed): {tools_to_use}")
                    elif selected_tools is not None and len(selected_tools) > 0:
                        tools_to_use = list(selected_tools)
                        logger.info(f"Using UI-selected tools: {tools_to_use}")
                    else:
                        tools_to_use = user.allowed_tools or []
                        logger.info(f"Using allowed_tools (no/empty UI selection): {tools_to_use}")
                
                # If user has Exchange enabled and configured, add Exchange tools so the agent can use them
                try:
                    from backend.tools.implementations.exchange_tools import EXCHANGE_TOOL_NAMES
                    prefs = user.preferences or {}
                    exchange = prefs.get("exchange_config", {})
                    if exchange.get("enabled") and all([
                        exchange.get("server"),
                        exchange.get("email"),
                        exchange.get("username"),
                        exchange.get("password"),
                    ]):
                        for name in EXCHANGE_TOOL_NAMES:
                            if name not in tools_to_use:
                                tools_to_use.append(name)
                        logger.info(f"Exchange enabled: added Exchange tools. tools_to_use now has {len(tools_to_use)} tools")
                except Exception as ex:
                    logger.debug(f"Exchange tools check skipped: {ex}")
                
                # Retrieve conversation history (previous messages)
                previous_messages = db.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).order_by(Message.created_at).all()
                
                # Filter out the current message we just added (it will be added again in agent.run)
                history_messages = [msg for msg in previous_messages if msg.id != user_msg.id]
                logger.info(f"Retrieved {len(history_messages)} previous messages from conversation {conversation_id}")

                # Track if we've sent the title update
                title_sent = False

                mcp_ids = mcp_server_ids_override if mcp_server_ids_override is not None else None
                # Default False: LLMToolSelectorMiddleware expects a dict from the model; many models (e.g. qwen3) return None or non-dict and cause AssertionError
                use_middleware = use_tool_selector_middleware if use_tool_selector_middleware is not None else False
                async for event in agent.run(
                    query=message,
                    conversation_id=conversation_id,
                    user_id=user.id,
                    allowed_tools=tools_to_use,
                    stream=stream,
                    message_history=history_messages,
                    mcp_server_ids=mcp_ids,
                    use_tool_selector_middleware=use_middleware,
                    image_base64_list=image_base64_list,
                    invocation_source=invocation_source,
                ):
                    # Check for cancellation before processing each event
                    if cancellation_token.is_set():
                        logger.info(f"Execution cancelled for user {user.id}")
                        yield {
                            "type": "cancelled",
                            "message": "Generation stopped by user"
                        }
                        return
                    
                    # Check if title generation is complete and send update if ready
                    if not title_sent and user_message_count == 1 and title_task:
                        if title_task.done():
                            try:
                                generated_title = await title_task
                                if generated_title:
                                    yield {
                                        "type": "title_update",
                                        "title": generated_title,
                                        "conversation_id": conversation_id
                                    }
                                    title_sent = True
                            except Exception as title_error:
                                logger.warning(f"Error getting generated title: {title_error}")
                    
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
                        # Commit immediately to ensure data consistency - prevents data loss if stream is interrupted
                        try:
                            db.commit()
                        except Exception as commit_error:
                            logger.error(f"Failed to commit AgentStep: {commit_error}")
                            db.rollback()
                        
                        # Don't save step messages to Message table - they're stored in AgentStep
                        # Only save the final answer as a message for display in chat
                        # Steps are available in the steps panel via AgentStep table
                        
                        # Stream step to client
                        yield event
                    
                    elif event.get("type") == "permission_request":
                        # Stream permission request to client
                        yield event
                        
                        # In real implementation, wait for client response
                        # For now, auto-approve after a short delay
                        await asyncio.sleep(0.5)
                    
                    elif event.get("type") == "complete":
                        # Save final response - handle different response formats
                        response_data = event.get("response", {})
                        
                        # Extract data with fallbacks for different agent types
                        steps = response_data.get("steps", [])
                        total_tokens = response_data.get("total_tokens", 0)
                        final_answer = response_data.get("final_answer", "")
                        
                        # If final_answer is empty, try to extract from steps
                        if not final_answer or not final_answer.strip():
                            # Look for the last "answer" type step
                            if isinstance(steps, list) and steps:
                                for step in reversed(steps):
                                    if step.get("step_type") == "answer" and step.get("content"):
                                        final_answer = step.get("content", "")
                                        break
                            
                            # If still empty, use a default message
                            if not final_answer or not final_answer.strip():
                                final_answer = "I've completed the task using the available tools."
                        
                        # Save final assistant message (the actual response shown to user)
                        # This is the LLM's final answer, not the raw tool results
                        assistant_msg = Message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=final_answer.strip(),
                            tokens_used=total_tokens
                        )
                        db.add(assistant_msg)
                        db.commit()
                        logger.info(f"Saved final assistant message with {len(final_answer)} characters")
                        
                        # Update conversation
                        conversation = db.query(Conversation).filter(
                            Conversation.id == conversation_id
                        ).first()
                        
                        if conversation:
                            step_count = len(steps) if isinstance(steps, list) else 1
                            conversation.total_messages += step_count + 1
                            conversation.total_tokens += total_tokens
                            db.commit()
                        
                        # Save to vector memory if agent supports it
                        if hasattr(agent, 'save_to_memory'):
                            try:
                                await agent.save_to_memory(
                                    conversation_id=conversation_id,
                                    message=final_answer,
                                    metadata={
                                        "role": "assistant",
                                        "user_id": user.id,
                                        "tokens": total_tokens
                                    }
                                )
                            except Exception as memory_error:
                                logger.warning(f"Failed to save to memory: {memory_error}")
                        else:
                            logger.debug("Agent does not support memory saving")
                        
                        yield event
                    
                    elif event.get("type") == "error":
                        # Log error and stream to client
                        logger.error(f"Agent error: {event['error']}")
                        yield event
                
                # Final check for title update after all events are processed
                if not title_sent and user_message_count == 1 and title_task:
                    if title_task.done():
                        try:
                            generated_title = await title_task
                            if generated_title:
                                yield {
                                    "type": "title_update",
                                    "title": generated_title,
                                    "conversation_id": conversation_id
                                }
                                title_sent = True
                        except Exception as title_error:
                            logger.warning(f"Error getting generated title: {title_error}")
                    else:
                        # If title generation is still running, wait a bit and check again
                        # This ensures we send the title update even if it completes after the stream
                        try:
                            generated_title = await asyncio.wait_for(title_task, timeout=0.1)
                            if generated_title:
                                yield {
                                    "type": "title_update",
                                    "title": generated_title,
                                    "conversation_id": conversation_id
                                }
                                title_sent = True
                        except asyncio.TimeoutError:
                            # Title generation still in progress, that's okay
                            pass
                        except Exception as title_error:
                            logger.warning(f"Error getting generated title: {title_error}")
                
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
        """Clear agent for user (all agent types)."""
        # Clear all agent types for this user (langchain and deepagent)
        agent_keys_to_remove = [
            key for key in self.active_agents.keys() 
            if key.startswith(f"{user_id}_")
        ]
        for agent_key in agent_keys_to_remove:
            del self.active_agents[agent_key]
            if agent_key in self.execution_locks:
                del self.execution_locks[agent_key]
        
        # Clear cancellation token
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
    
    async def _generate_conversation_title(
        self,
        conversation_id: int,
        first_message: str,
        user_id: int
    ) -> Optional[str]:
        """Generate a conversation title based on the first user message.
        
        Returns:
            The generated title, or None if generation failed or was skipped.
        """
        from backend.agent.model_factory import create_model
        from langchain_core.messages import HumanMessage, SystemMessage
        from backend.config import settings as app_settings
        from backend.models import SessionLocal
        
        # Create a new database session for this background task
        db = SessionLocal()
        try:
            # Get user and conversation with fresh database session
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for title generation")
                return
            
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for title generation")
                return
            
            # Skip if title is already set (not "New Conversation")
            if conversation.title and conversation.title != "New Conversation":
                return
            
            # Get user's API configuration
            preferences = user.preferences or {}
            api_config = preferences.get("api_config", {})
            llm_provider = api_config.get("llm_provider", "ollama")
            
            # Get API keys from environment if not in user config
            if not api_config.get("openai_api_key") and app_settings.OPENAI_API_KEY:
                api_config["openai_api_key"] = app_settings.OPENAI_API_KEY
            if not api_config.get("deepseek_api_key") and app_settings.DEEPSEEK_API_KEY:
                api_config["deepseek_api_key"] = app_settings.DEEPSEEK_API_KEY
            if not api_config.get("mistral_api_key") and app_settings.MISTRAL_API_KEY:
                api_config["mistral_api_key"] = app_settings.MISTRAL_API_KEY
            if not api_config.get("gemini_api_key") and app_settings.GEMINI_API_KEY:
                api_config["gemini_api_key"] = app_settings.GEMINI_API_KEY
            
            # Create a lightweight LLM model for title generation
            # Use lower temperature for more consistent titles
            title_model = create_model(
                provider=llm_provider,
                model_name=None,  # Will use default for provider
                temperature=0.3,  # Lower temperature for more deterministic titles
                max_tokens=50,  # Titles should be short
                api_config=api_config
            )
            
            # Create prompt for title generation
            system_prompt = """You are a helpful assistant that generates concise, descriptive titles for conversations based on the first message.

Rules:
- Generate a title that is 3-8 words long
- Make it descriptive and specific to the user's question or request
- Do NOT include quotes, markdown, or special formatting
- Do NOT include words like "Title:", "Conversation:", or "About:"
- Just return the title text directly
- If the message is very short or unclear, create a general but relevant title
- Keep it professional and clear

Examples:
- "What is the weather today?" → "Weather Inquiry"
- "Help me write a Python function" → "Python Function Help"
- "Search for information about quantum computing" → "Quantum Computing Research"
- "How do I install Node.js?" → "Node.js Installation Guide"
- "سلام" → "General Inquiry" (or appropriate title in the message language)"""
            
            user_prompt = f"Generate a title for this conversation based on the first message:\n\n{first_message[:500]}"  # Limit to 500 chars
            
            # Generate title
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await title_model.ainvoke(messages)
            title = response.content.strip()
            
            # Remove <think>...</think> (and redacted_reasoning) tags so titles are clean
            from backend.agent.agent import strip_reasoning_tags
            title = strip_reasoning_tags(title).strip()
            
            # Clean up the title (remove quotes, markdown, etc.)
            title = title.strip('"\'`').strip()
            # Remove markdown formatting if present
            if title.startswith("#"):
                title = title.lstrip("#").strip()
            # Remove common prefixes
            for prefix in ["Title:", "Conversation:", "About:", "Topic:"]:
                if title.lower().startswith(prefix.lower()):
                    title = title[len(prefix):].strip()
            
            # Limit title length (database field is 200 chars, but keep it reasonable)
            if len(title) > 100:
                title = title[:97] + "..."
            
            # If title is empty or too short, use a fallback
            if not title or len(title) < 3:
                # Extract first few words from the message as fallback
                words = first_message.split()[:5]
                title = " ".join(words)
                if len(title) > 50:
                    title = title[:47] + "..."
            
            # Update conversation title
            conversation.title = title
            db.commit()
            logger.info(f"Generated title '{title}' for conversation {conversation_id}")
            
            # Return the generated title so it can be sent to the frontend
            return title
            
        except Exception as e:
            logger.error(f"Error generating conversation title: {e}", exc_info=True)
            # Don't raise - title generation failure shouldn't break the conversation
            db.rollback()
            return None
        finally:
            # Always close the database session
            db.close()


# Global executor instance
agent_executor = AgentExecutor()
