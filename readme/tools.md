# Tools

Tools let the agent inspect local data, call external services, schedule reminders, and perform utility actions. A tool must be registered in the backend and normally must also be allowed for the user.

## Permission Levels

Tool permission levels are defined in `backend/tools/base.py`:

- `safe`: no special permission required.
- `read_files`: can read local files or document content.
- `write_files`: can write local files.
- `network`: can access the network.
- `web_access`: can access web pages.
- `database_read`: can read from databases.
- `database_write`: can write to databases.
- `system`: can execute system commands.
- `system_read`: can read system information.

The Tools page uses `/api/tools/available` to show built-in tools and `/api/tools/grant-permission` to add or remove tools from the user's `allowed_tools`.

## Step-By-Step Tool Enablement

1. Sign in.
2. Open Tools.
3. Review each tool's description and permission.
4. Enable only the tools the user should be able to call.
5. In Chat, select tools for a message if you want to narrow the agent's available actions.
6. Ask for a task that needs the tool.
7. Inspect the steps panel to see tool calls and results.

## Built-In File And Document Tools

### `search_local_files`

Semantic retrieval over indexed documents.

- Permission: `read_files`.
- Input: `query`, optional `user_id`.
- Searches `user_documents_{user_id}` when user context exists.
- Returns serialized `Source: ... Content: ...` snippets.
- If no uploaded documents match, it tells the user to upload documents in Documents.

### `read_file`

Reads a text file from an allowed path.

- Permission: `read_files`.
- Input: `file_path`, optional `start_line`, optional `end_line`.
- Enforces `ALLOWED_FILE_PATHS` and `BLOCKED_FILE_PATHS`.

### `parse_document`

Extracts text from supported document files.

- Permission: `read_files`.
- Input: `file_path`, optional `extract_metadata`.
- Supports PDF, DOCX, Markdown, TXT, LOG, and CSV.

## Built-In Web And Network Tools

### `web_search`

Searches the web and fetches page content for top results.

- Permission: `network`.
- Requires `ENABLE_WEB_SEARCH=true`.
- Uses SearXNG when `SEARXNG_URL` is configured, with DuckDuckGo fallback.
- Inputs: `query`, `max_results`, `time_range`.

### `scrape_webpage`

Extracts content from a URL.

- Permission: `web_access`.
- Inputs: `url`, `extract_type` (`text`, `links`, `images`, `all`), `max_length`.

### `http_request`

Generic HTTP client.

- Permission: `network`.
- Inputs: method, URL, headers, query params, JSON body, form data, timeout, and `allow_insecure`.
- Returns status, headers, JSON or text, and success state.

### `network_tools`

Network utility toolkit.

- Permission: `network`.
- Actions: `ping`, `port_scan`, `dns_lookup`, `ip_geolocation`.
- Inputs: `action`, `target`, optional `port` or `port_range`.

## Built-In API Tool

### `get_weather`

Fetches weather through OpenWeatherMap-style API usage.

- Permission: `network`.
- Inputs: `city`, `units`.
- Uses `WEATHER_API_KEY` if configured; otherwise uses `demo`, which may not work for real requests.

### `custom_api`

A template/example generic API tool.

- Permission: `network`.
- The implementation points to placeholder values and is mainly a starting point for creating real API tools.

## Built-In Analysis And Utility Tools

### `get_system_info`

Returns OS, CPU, memory, disk, boot time, optional network interfaces, and optional top processes.

- Permission: `system_read`.
- Inputs: `detailed`, `include_processes`.

### `analyze_code`

Reads a code file and reports basic stats, complexity stats, and simple security-pattern checks.

- Permission: `read_files`.
- Inputs: `file_path`, `analysis_type` (`basic`, `complexity`, `security`, `all`).

### `analyze_image`

Inspects image file properties and optional EXIF metadata.

- Permission: `read_files`.
- Inputs: `image_path`, `include_metadata`.
- Requires Pillow at runtime.

### `calculate_hash`

Hashes text or a file.

- Permission: `read_files`.
- Inputs: `input_type` (`file` or `text`), `input_value`, `hash_type` (`md5`, `sha1`, `sha256`, `sha512`, `all`).

## Built-In Database Tool

### `query_database`

Reads from a database.

- Permission: `database_read`.
- The code includes a separate `DatabaseWriteTool`, but the registry currently registers only `DatabaseQueryTool` by default.

## Scheduling Tool

### `schedule_job`

Creates reminders and scheduled jobs.

- Permission: `safe`.
- Inputs: `job_type`, `title`, `run_at`, optional `cron_expression`, optional `schedule_timezone`, optional `payload`.
- The agent system prompt explicitly tells the model to use this tool for reminders.
- Jobs are run by the backend cron runner.

## Exchange/EWS Tools

Exchange tools are registered if `exchangelib` is available. They are added to the agent when a user's Exchange settings are enabled and complete.

Tools:

- `exchange_list_emails`
- `exchange_get_email`
- `exchange_send_email`
- `exchange_list_calendar`
- `exchange_create_event`
- `exchange_list_tasks`
- `exchange_create_task`

Required user settings:

- Exchange enabled.
- Server.
- Email.
- Username.
- Password.

Configure and test these under Settings.

## Direct Tool Execution

Endpoint:

```text
POST /api/tools/execute
```

Use it for testing a tool outside normal chat.

If `require_approval` is true and the tool is not `safe`, the endpoint returns an approval-required response instead of executing.

## Custom Tools And MCP Tools

Built-in tools are not the only possible tools.

- User custom tools are stored in `custom_tools` and loaded at runtime.
- MCP server tools are discovered through configured MCP servers and appended to the agent's tool list during chat execution.

Read [Custom Tools](custom-tools.md) and [MCP Servers](mcp-servers.md) for those flows.
