# Chrome Extension

The Chrome extension lets a user ask the local agent questions about the current webpage. It extracts page context in the browser and sends it to the backend chat endpoint.

## What It Can Extract

The extension is designed to collect:

- Page text.
- URL.
- Title.
- Links.
- Images.
- Forms.
- Metadata.

The backend message endpoint specifically consumes `page_context` with URL, title, and page text, then asks the agent to answer using that provided context.

## Install For Development

1. Open Chrome.
2. Go to:

   ```text
   chrome://extensions/
   ```

3. Enable Developer mode.
4. Click Load unpacked.
5. Select the `chrome-extension/` directory.
6. Pin the extension if desired.

## Configure Backend

1. Open extension options or click Settings in the popup.
2. Set backend URL.

   Local development normally uses:

   ```text
   http://localhost:8000
   ```

   Docker backend normally uses:

   ```text
   http://localhost:3333
   ```

3. Test the connection.
4. Log in with your app username and password.

## Use On A Page

1. Navigate to a normal webpage.
2. Click the extension icon.
3. Wait for content extraction.
4. Ask a question.
5. The extension creates or uses a chat conversation and sends the question plus page context.
6. The backend streams or returns the agent answer.

## Backend Requirements

The backend must expose:

- `POST /api/auth/login`
- `GET /health`
- `POST /api/chat/conversations`
- `POST /api/chat/conversations/{id}/messages`

CORS must permit the extension origin. `backend/main.py` includes `allow_origin_regex` for `chrome-extension://.*` when not allowing all origins.

## Manifest

The extension uses Manifest V3 and includes:

- `activeTab`
- `storage`
- `scripting`
- `tabs`
- host permissions for backend localhost and web pages
- background service worker
- content script on all URLs
- popup UI
- options page

## Files

```text
chrome-extension/
  manifest.json
  background/service-worker.js
  content/content-script.js
  popup/popup.html
  popup/popup.js
  popup/popup.css
  options/options.html
  options/options.js
  options/options.css
  icons/
```

## Troubleshooting

- Cannot connect to backend: verify backend URL, backend port, `/health`, and CORS.
- Login fails: confirm the same credentials work in the web UI.
- Page content missing: Chrome blocks content scripts on some pages such as Chrome internal pages and extension pages.
- LAN/WiFi access fails: use the server's LAN IP instead of `localhost`, check firewall rules, and disable network isolation if needed.
- Extension changed but behavior did not: click reload on the extension card in `chrome://extensions/`.
