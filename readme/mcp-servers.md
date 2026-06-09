# MCP Servers

MCP server support lets each user connect external Model Context Protocol servers and expose their tools to the chat agent.

## Supported Transports

The app stores two user-facing transport types:

- `http`
- `stdio`

For HTTP, the model converts the server config to `streamable-http` when creating the MCP client config and ensures the `Accept` header includes `text/event-stream`.

## Step-By-Step HTTP Server Setup

1. Start your MCP server.
2. Open MCP Servers in the frontend.
3. Add a server.
4. Set transport to HTTP.
5. Enter the MCP endpoint URL, for example:

   ```text
   http://localhost:8001/mcp
   ```

6. Add headers or auth config if the server requires them.
7. Save.
8. Click Test.
9. Confirm `success=true` and review discovered tools.
10. Enable the server.
11. Use Chat and ask for a task that matches one of the MCP tools.

## Step-By-Step stdio Server Setup

1. Confirm the server command works locally.
2. Open MCP Servers.
3. Add a server.
4. Set transport to stdio.
5. Enter `command`, for example `python`.
6. Enter args, for example `["path/to/server.py"]`.
7. Save and test.
8. Enable the server.
9. Use Chat.

## Runtime Flow

1. User MCP server rows are stored in `mcp_servers`.
2. `mcp_service.get_tools_for_user()` loads active and enabled servers for a user.
3. `MultiServerMCPClient` connects to the server set.
4. MCP tools are converted to LangChain-compatible tools by `langchain-mcp-adapters`.
5. Chat agent execution appends MCP tools to the selected built-in/custom tool list.

When `mcp_server_ids` is:

- `None`: load all active enabled user MCP servers.
- `[]`: load no MCP servers.
- `[id, ...]`: load only the selected servers.

## MCP API

- `GET /api/mcp/` lists the user's MCP server configs.
- `POST /api/mcp/` creates a config.
- `GET /api/mcp/{server_id}` gets one config.
- `PUT /api/mcp/{server_id}` updates a config.
- `DELETE /api/mcp/{server_id}` deletes a config.
- `POST /api/mcp/{server_id}/test` tests a connection and updates last status.
- `GET /api/mcp/tools/list` lists tools discovered from the user's enabled servers.

## Test MCP Server

The repository includes `test_mcp_server_simple.py` and `README_MCP_TEST.md`.

Typical test command:

```powershell
uvicorn test_mcp_server_simple:app --host 0.0.0.0 --port 8001
```

Then add this server in the UI:

```text
Name: test-server
Transport: HTTP
URL: http://localhost:8001/mcp
```

The test server exposes tools such as adding numbers, multiplying numbers, greeting a user, server info, power calculation, and string reversal.

## Troubleshooting

- Test fails with connection refused: confirm the MCP server process is running and the URL is correct.
- HTTP server tools do not load: ensure the endpoint supports streamable HTTP/SSE behavior expected by the MCP client.
- Auth errors: add required headers or auth config to the server configuration.
- Tools changed but chat still sees old tools: update/test the server or restart the backend to clear cached client state if needed.
