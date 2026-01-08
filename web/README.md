# apeXion Web Downloader (Vercel-ready)

Minimal static-first web UI with mock API routes you can deploy directly to Vercel. Swap the mock handlers for your real downloader (yt-dlp via Python serverless, or ytdl-core in Node) when ready.

## Structure
- `index.html`, `style.css`, `app.js`: Bold landing UI with URL input, quality selector, progress bar, and demo run.
- `api/info.js`, `api/download.js`: Mock Vercel serverless routes returning JSON. Replace logic with real fetch/download code.
- Root is `web/` so your existing desktop/Kivy code stays untouched.

## Local preview (no build step)
```bash
# from repo root
npx serve web
# or use any static server you like
```

## Deploy to Vercel
1. Create a new Vercel project and set **Project Root** to `web/`.
2. Framework preset: **Other** (no build needed).
3. Deploy. Vercel will expose `api/info` and `api/download` as serverless endpoints.

## Going live
- Replace `web/api/info.js` with real metadata fetching (yt-dlp, ytdl-core, etc.).
- Replace `web/api/download.js` to stream/generate a download URL.
- Ensure any binaries (ffmpeg/yt-dlp) are available in your chosen runtime or use a remote worker.

## Notes
- The UI currently talks to mock endpoints; progress is simulated in `app.js`.
- Fonts: Space Grotesk + Inter pulled from Google Fonts.
- Color direction: Deep navy base with lilac/cyan gradient accents; responsive and mobile-friendly.
