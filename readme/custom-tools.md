# Custom Tools

Custom tools let each user create additional agent tools without modifying the repository. Tools are stored in SQLite, registered at runtime, and can be enabled like built-in tools.

## What A Custom Tool Contains

A `CustomTool` row stores:

- `name`: machine-readable snake_case identifier.
- `display_name`: human-readable label.
- `description`: tool description used by the model.
- `permission_level`: permission gate.
- `code`: Python code defining an `execute` function.
- `parameters_schema`: JSON Schema-like tool parameters.
- `is_active`: active/inactive toggle.
- `created_by`: user ID.
- `usage_count`: tracking field.

## Step-By-Step Manual Creation

1. Open Tools.
2. Choose to add a tool.
3. Enter a unique `name` containing only letters, numbers, and underscores.
4. Write a clear display name and description.
5. Choose the permission level.
6. Define the JSON parameter schema.
7. Write Python code that defines `execute`.
8. Save the tool.
9. Enable the tool in the user's allowed tools.
10. Ask Chat to use it.

## Required Code Shape

The custom tool runtime expects code that defines a callable named `execute`.

Recommended async shape:

```python
from backend.tools.base import ToolResult

async def execute(self, query: str, **parameters):
    try:
        return ToolResult(success=True, output={"query": query})
    except Exception as e:
        return ToolResult(success=False, output=None, error=str(e))
```

Sync functions are also supported; they run in an executor so they do not block the event loop.

## Parameter Schema Shape

Example:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "The query to process"
    },
    "limit": {
      "type": "integer",
      "description": "Maximum results",
      "default": 10
    }
  },
  "required": ["query"]
}
```

The base tool validator checks required fields and basic types.

## AI-Assisted Tool Generation

Endpoint:

```text
POST /api/custom-tools/generate
```

The user provides:

- Natural language description.
- Optional tool name.
- Permission level.

The backend uses the user's configured LLM provider to generate:

- Tool code.
- Parameter schema.
- Suggested name.
- Suggested display name.
- Suggested description.

The generation endpoint expects raw JSON from the model and includes fallback parsing for common malformed responses. It also strips reasoning tags and compiles generated code before returning it.

## Runtime Registration

Custom tools are registered:

- Immediately after create.
- Immediately after update.
- During chat execution, before resolving tools for the user.
- During direct tool execution.

Registration creates a dynamic `BaseTool` subclass and stores it in the global `tool_registry`.

## Import Allowlist

The runtime limits imports through a custom import function.

Always allowed standard modules:

- `math`
- `random`
- `re`
- `json`
- `time`
- `datetime`
- `uuid`
- `base64`
- `hashlib`
- `typing`
- `asyncio`

Allowed internal module:

- `backend.tools.base`

Additional modules by permission:

- `network` or `web_access`: `urllib`, `urllib.parse`, `httpx`, `requests`, `wikipedia`.
- `database_read` or `database_write`: `sqlite3`.

## Safety Notes

- Custom tools are not a full security sandbox.
- Builtins are restricted, but user code still runs inside the backend process.
- Only trusted users should be allowed to create powerful network, database, or system-like custom tools.
- Prefer environment variables for secrets. Do not hardcode API keys in tool code.

## Custom Tool API

- `GET /api/custom-tools/` lists tools for the current user.
- `POST /api/custom-tools/` creates a tool.
- `GET /api/custom-tools/{tool_id}` fetches one tool.
- `PUT /api/custom-tools/{tool_id}` updates a tool.
- `DELETE /api/custom-tools/{tool_id}` deletes and unregisters a tool.
- `POST /api/custom-tools/{tool_id}/toggle` activates or deactivates a tool.
- `POST /api/custom-tools/generate` generates code/schema with AI.
