# AI Agent Chrome Extension

A Chrome extension that reads page content and uses your local AI agent backend to answer questions about the current webpage.

## Features

- 📄 **Page Content Extraction**: Automatically extracts text, links, images, forms, and metadata from any webpage
- 🤖 **AI-Powered Q&A**: Ask questions about the current page using your local LLM
- 🔒 **Privacy-First**: All processing happens on your local backend
- ⚙️ **Configurable**: Easy settings page for backend URL and authentication
- 💾 **Offline Support**: Caches page content for offline access

## Installation

### Development Setup

1. **Load Extension in Chrome**:

   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top right)
   - Click "Load unpacked"
   - Select the `chrome-extension` folder

2. **Configure Backend**:

   - Click the extension icon, then click "Settings"
   - Or go to `chrome://extensions/` → Find "AI Agent Assistant" → Click "Options"
   - Enter your backend URL (default: `http://localhost:8000`)
   - Click "Test Connection" to verify

3. **Login**:
   - Enter your username and password
   - Click "Login"
   - The extension will save your authentication token

## Usage

1. **Navigate to any webpage**
2. **Click the extension icon** in the Chrome toolbar
3. **Wait for page content to load** (you'll see a status message)
4. **Ask a question** about the page content in the input field
5. **Get AI-powered answers** based on the page content

## File Structure

```
chrome-extension/
├── manifest.json              # Extension configuration
├── background/
│   └── service-worker.js      # Background processing & API communication
├── content/
│   └── content-script.js      # Page content extraction
├── popup/
│   ├── popup.html             # Extension popup UI
│   ├── popup.js               # Popup logic
│   └── popup.css              # Popup styles
├── options/
│   ├── options.html           # Settings page
│   ├── options.js             # Settings logic
│   └── options.css            # Settings styles
└── icons/                      # Extension icons (you need to add these)
```

## Icons

You need to create icon files:

- `icons/icon16.png` (16x16 pixels)
- `icons/icon48.png` (48x48 pixels)
- `icons/icon128.png` (128x128 pixels)

You can use any image editor or online tool to create these. The icons should represent your AI agent.

## Backend Requirements

Your backend must:

1. Run on `http://localhost:8000` (or configure in settings)
2. Have CORS enabled for `chrome-extension://` origins
3. Provide these endpoints:
   - `POST /api/auth/login` - User authentication
   - `GET /health` - Health check
   - `POST /api/chat/conversations` - Create conversation
   - `POST /api/chat/conversations/{id}/messages` - Send message with `page_context` parameter

## Backend API Modification

Your backend's message endpoint should accept `page_context`:

```python
class MessageCreate(BaseModel):
    content: str
    stream: bool = True
    selected_tools: List[str] = []
    use_deepagent: bool = False
    file_contents: List[Dict] = []
    page_context: Optional[Dict] = None  # NEW: Page content from extension
```

## Troubleshooting

### Extension not loading

- Make sure all files are in the correct directory structure
- Check Chrome's extension error page (`chrome://extensions/`)
- Verify `manifest.json` is valid JSON

### Connection failed

- Ensure your backend is running on the configured URL
- Check CORS settings in your backend
- Verify the backend URL in settings

### Authentication failed

- Check your username and password
- Verify the backend login endpoint is working
- Check browser console for errors

### Page content not loading

- Some pages may block content scripts (chrome:// pages, extensions, etc.)
- Try refreshing the page
- Check if the page has Content Security Policy restrictions

### Network Connectivity Issues (WiFi vs LAN)

If your backend/frontend is accessible on LAN but not on WiFi:

**The Problem:**

- WiFi and LAN are often on different network segments (subnets/VLANs)
- Firewall rules may block certain ports on WiFi
- Router configuration may isolate WiFi from LAN

**Solutions:**

1. **Use Server IP Address Instead of localhost:**

   - In extension settings, use the server's IP address (e.g., `http://192.168.1.100:8000`)
   - Find your server's IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
   - Ensure both WiFi and LAN devices can reach this IP

2. **Check Network Configuration:**

   - Verify WiFi and LAN are on the same subnet (e.g., both 192.168.1.x)
   - Check router settings for "AP Isolation" or "Client Isolation" - disable if enabled
   - Ensure firewall allows the port on both networks

3. **Port Forwarding (if needed):**

   - If WiFi is on a different subnet, configure port forwarding on your router
   - Forward the backend port (8000) and frontend port (3333) to your server

4. **Use a Reverse Proxy:**

   - Set up nginx or similar to serve both backend and frontend on standard ports (80/443)
   - This avoids port-specific firewall issues

5. **VPN/Network Bridge:**
   - Use a VPN to bridge WiFi and LAN networks
   - Or configure router to bridge WiFi and LAN segments

**Note:** Changing the port number won't solve this issue - it's a network infrastructure problem, not a port problem.

## Development

1. Make changes to files
2. Go to `chrome://extensions/`
3. Click the refresh icon on the extension card
4. Test your changes

## Building for Production

1. Go to `chrome://extensions/`
2. Click "Pack extension"
3. Select the `chrome-extension` folder
4. Choose a location for the `.crx` file
5. The extension is now packaged and ready for distribution

## License

Same as the main Agentic-AI project.
