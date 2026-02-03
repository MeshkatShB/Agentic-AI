# Quick Start Guide

## Prerequisites

1. Your backend server running on `http://localhost:8000`
2. Chrome browser
3. Basic icon files (see `icons/README.md`)

## Installation Steps

### 1. Create Icons (Required)

Before loading the extension, you need to create icon files:

- Go to `icons/` folder
- Create three PNG files:
  - `icon16.png` (16x16 pixels)
  - `icon48.png` (48x48 pixels)
  - `icon128.png` (128x128 pixels)

**Quick test icons**: You can create simple colored squares for testing.

### 2. Load Extension in Chrome

1. Open Chrome
2. Navigate to `chrome://extensions/`
3. Enable **Developer mode** (toggle in top-right)
4. Click **Load unpacked**
5. Select the `chrome-extension` folder
6. The extension should appear in your extensions list

### 3. Configure Settings

1. Click the extension icon in Chrome toolbar (or go to `chrome://extensions/` → Options)
2. Enter your backend URL (default: `http://localhost:8000`)
3. Click **Test Connection** to verify
4. Enter your username and password
5. Click **Login**
6. Click **Save Settings**

### 4. Use the Extension

1. Navigate to any website
2. Click the extension icon
3. Wait for "Content loaded" status
4. Type a question about the page
5. Click **Ask** or press Enter
6. Get AI-powered answers!

## Troubleshooting

### Extension won't load

- Check that all files are in the correct folders
- Verify `manifest.json` is valid JSON
- Check Chrome's error console (`chrome://extensions/` → Errors)

### Connection failed

- Ensure backend is running: `uvicorn backend.main:app --reload`
- Check backend URL in settings
- Verify backend health: `curl http://localhost:8000/health`

### Authentication failed

- Check username/password
- Verify backend login endpoint works
- Check browser console for errors

### Page content not loading

- Some pages block content scripts (chrome://, extensions, etc.)
- Try refreshing the page
- Check if page has CSP restrictions

## Next Steps

- Customize the UI in `popup/popup.css`
- Add more features in `background/service-worker.js`
- Modify content extraction in `content/content-script.js`

## Backend Changes Made

The backend now accepts `page_context` in message requests:

```python
# backend/api/chat.py
class MessageRequest(BaseModel):
    # ... existing fields ...
    page_context: Optional[dict] = None  # NEW
```

The page context is automatically included in the message sent to the LLM.
