# Browser Automation

Browser automation is powered by the `browser-use` package and exposed through the Browser Automation page.

## What It Does

The backend accepts a natural language browser task, starts a local browser, creates a `browser_use.Agent`, and streams status/result events back to the UI.

Important design choices in this codebase:

- Uses the user's configured LLM provider.
- Uses local browsers only.
- Explicitly unsets `BROWSER_USE_API_KEY` during execution to avoid cloud browser mode.
- Sets `use_cloud=false` and related cloud fields to disabled values.
- Keeps the browser visible with `headless=false`.

## Step-By-Step Use

1. Install backend dependencies.
2. Ensure `browser-use` is installed from `requirements.txt`.
3. Install or configure a local browser/Chromium for browser-use.
4. Sign in to the app.
5. Open Settings and configure the LLM provider.
6. Open Browser Automation.
7. Enter a browser task.
8. Run the task.
9. Watch streamed status messages and final history/details.

Example tasks:

```text
Open example.com and summarize the page.
Search for the product page for X and report the price.
Go to the local frontend and check whether the login page loads.
```

## API

Execute:

```text
POST /api/browser-use/execute
```

Body:

```json
{
  "task": "Open example.com and summarize it",
  "stream": true
}
```

Status:

```text
GET /api/browser-use/status
```

Status returns:

- whether `browser-use` imports successfully.
- current LLM provider.
- `uses_local_browser=true`.
- `uses_user_llm=true`.

## Provider Support

The endpoint attempts to use browser-use native classes:

- `ChatOpenAI` for OpenAI.
- `ChatOllama` for Ollama.
- `ChatMistral` for Mistral.
- `ChatGoogle` for Gemini.

DeepSeek is supported by the normal chat model factory through OpenAI-compatible APIs, but the browser automation endpoint currently branches only for OpenAI, Ollama, Mistral, and Gemini.

## Streaming Events

The browser endpoint streams SSE records such as:

- `status`: task startup, browser initialization, running, processing results, closing browser.
- `browser_action`: step-level errors from browser-use history.
- `complete`: final history and detail payload.
- `error`: failure with message and optional traceback.

## Troubleshooting

- Import error: install requirements and confirm `browser-use` is present.
- Cloud browser/auth error: ensure no environment or runtime state forces cloud mode; the endpoint tries to unset `BROWSER_USE_API_KEY`.
- Browser fails to launch: install Chromium/browser support required by browser-use.
- Page parsing errors: retry with a simpler page or task; the endpoint uses longer wait times but complex pages can still fail.
- Unsupported provider: switch Settings to Ollama, OpenAI, Mistral, or Gemini for this feature.
