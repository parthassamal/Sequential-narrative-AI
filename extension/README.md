# Vibe AI Browser Extension

🎬 AI-powered content recommendations right in your browser!

## Features

- **Popup Search**: Click the extension icon to search across TMDb, YouTube, and Paramount+
- **Quick Prompts**: One-click access to Action, Comedy, Thriller, and Trending content
- **Floating Button**: Appears on streaming sites (Netflix, YouTube, Hulu, etc.) for quick recommendations
- **Context Menu**: Right-click any selected text to search for similar content

## Installation

### Step 1: Generate Icons (Required)

1. Open `generate-icons.html` in Chrome
2. Right-click each canvas and "Save image as..."
3. Save as `icon16.png`, `icon48.png`, `icon128.png` in the `icons/` folder

### Step 2: Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select this `extension` folder
5. The Vibe AI icon should appear in your toolbar!

### Step 3: Start the Backend

Make sure the Vibe AI backend is running:

```bash
cd ../backend
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

## Usage

### Popup Search
1. Click the Vibe AI extension icon
2. Type your query (e.g., "action movies", "funny videos")
3. Click a result to open it

### On Streaming Sites
When you visit Netflix, YouTube, Paramount+, Hulu, Disney+, or HBO Max:
1. A floating "🎬 What else?" button appears
2. Click it for recommendations based on what you're watching

### Context Menu
1. Select any text on a webpage
2. Right-click and choose "Find similar with Vibe AI"
3. The popup opens with search results

## Supported Platforms

| Platform | Popup Search | Floating Button |
|----------|-------------|-----------------|
| TMDb | ✅ | - |
| YouTube | ✅ | ✅ |
| Paramount+ | ✅ | ✅ |
| Netflix | - | ✅ |
| Hulu | - | ✅ |
| Disney+ | - | ✅ |
| HBO Max | - | ✅ |

## Troubleshooting

**"Offline" status in popup?**
- Make sure backend is running at `http://localhost:8888`

**No results?**
- Check if API keys are configured in the backend

**Floating button not appearing?**
- Refresh the streaming site page
- Check if content scripts are enabled in `chrome://extensions/`

## File Structure

```
extension/
├── manifest.json      # Extension configuration
├── popup.html         # Popup UI
├── popup.css          # Popup styles
├── popup.js           # Popup logic
├── background.js      # Background service worker
├── content.js         # Injected into streaming sites
├── content.css        # Styles for injected UI
├── icons/             # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── generate-icons.html # Tool to generate icons
```

## API Endpoints Used

- `GET /api/streaming/search?q={query}` - Search content
- `GET /api/streaming/trending` - Get trending content
- `GET /health` - Check backend status

---

Made with ❤️ for the Vibe AI Content Discovery System
