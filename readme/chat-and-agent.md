# Chat And Agent

The Chat page is the main workspace for asking the agent questions, attaching files, using tools, and seeing execution steps.

## What Chat Supports

- Create, list, rename, and delete conversations.
- Stream assistant responses with server-sent events.
- Stop an active generation.
- Persist user and assistant messages.
- Persist detailed agent steps separately from the visible chat messages.
- Auto-generate a conversation title from the first user message.
- Select tools for a message.
- Attach text documents for direct context.
- Attach images for multimodal model input.
- Receive page context from the Chrome extension.
- Search a conversation through vector memory.
- Produce a simple conversation summary.

## Step-By-Step Use

1. Sign in and open Chat.
2. Start a new conversation or select an existing one.
3. Choose tools if the UI exposes a tool selector for the message.
4. Optionally upload files.
5. Ask your question.
6. Watch streamed output and the steps panel.
7. Stop generation if needed.
8. Reopen the conversation later to continue with its saved history.

## Message Processing

The chat API endpoint is:

```text
POST /api/chat/conversations/{conversation_id}/messages
```

The request supports:

- `content`: user text.
- `stream`: whether to stream events.
- `selected_tools`: tools selected for this request.
- `use_deepagent`: optional DeepAgent attempt.
- `file_contents`: parsed uploaded file content.
- `file_attachments`: attachment metadata.
- `page_context`: content sent by the Chrome extension.

For page context, the backend prepends a structured block containing URL, title, and page text. The system prompt tells the model to answer from provided webpage content instead of unnecessarily searching.

For text file attachments, the backend appends sections like:

```text
--- Content from file: filename.ext ---
...
--- End of file: filename.ext ---
```

For image attachments, the backend sends base64 image parts to the agent so compatible multimodal providers can inspect them.

## Streaming Events

The backend streams events as SSE records.

Common event types:

- `token`: a single streamed output token or character.
- `step`: an agent step such as tool request, tool result, answer, or reflection.
- `complete`: final response payload.
- `title_update`: generated conversation title after the first user message.
- `cancelled`: generation was stopped.
- `error`: execution failed.

## Agent Selection And Models

The normal agent is `backend.agent.agent.Agent`, built on LangChain `create_agent`.

Provider selection comes from user preferences:

- `ollama`
- `openai`
- `deepseek`
- `mistral`
- `gemini`

If provider initialization fails, the agent falls back to Ollama with `DEFAULT_MODEL`.

`use_deepagent` attempts `DeepAgentWrapper` if the `deepagents` package is available. If not, it logs a warning and uses the normal LangChain agent.

## Tool Resolution

For each request, `AgentExecutor` chooses tools in this order:

1. Explicit tool overrides, used by integrations such as Telegram.
2. Telegram-specific tool preferences if the conversation is the Telegram conversation.
3. UI-selected tools if provided.
4. The user's full `allowed_tools` list.

Then it adds Exchange/EWS tools automatically when Exchange is enabled and configured.

MCP tools are loaded separately from enabled user MCP servers unless an override disables or narrows MCP server IDs.

## System Prompt Behavior

The agent is instructed to:

- Use provided webpage or file context directly.
- Use tools only when needed.
- Use `web_search` when the user explicitly asks for web search or current external information.
- Always produce a final answer after tool calls.
- Call `schedule_job` when the user asks for reminders or scheduled tasks.
- Avoid leaving the user with raw tool execution but no answer.

## Persistence

Visible messages:

- User messages are saved before execution.
- The final assistant answer is saved after completion.

Agent steps:

- Tool requests, tool results, reflections, and answer steps are saved in `agent_steps`.
- Chat retrieval filters out internal tool messages so the user sees clean conversation history.

Vector memory:

- Final assistant output is added to the `conversations` vector collection when memory saving succeeds.

## File Uploads In Chat

Endpoint:

```text
POST /api/chat/conversations/{conversation_id}/upload
```

Limits and behavior:

- Max chat upload size is 10 MB.
- Images are returned as base64 for vision.
- Non-images are parsed with `backend.utils.file_parser.extract_file_content`.
- Parsed content is sent with the message rather than added to long-term document RAG storage.

Use the Documents page when you want persistent indexed retrieval across future chats.

## Conversation Utilities

- `GET /api/chat/conversations` lists conversations.
- `GET /api/chat/conversations/{id}` returns messages.
- `GET /api/chat/conversations/{id}/steps` returns detailed steps.
- `PUT /api/chat/conversations/{id}` updates title/model/temperature/max steps.
- `POST /api/chat/conversations/{id}/stop` cancels current user generation.
- `POST /api/chat/conversations/{id}/search` searches vector memory for that conversation.
- `POST /api/chat/conversations/{id}/summarize` stores a simple summary.
- `GET /api/chat/conversations/{id}/files` lists attachment metadata.
- `DELETE /api/chat/conversations/{id}/files/{message_id}?filename=...` removes one attachment entry from a message.
