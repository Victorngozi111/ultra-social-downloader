# apeXion Web Downloader

Static-first landing + API proxies you can drop on Vercel.

## What’s inside
- `index.html`, `style.css`, `app.js`: Landing with URL input, quality selector, progress, and log.
- `api/info.js`, `api/download.js`: Proxy POST requests to `REMOTE_WORKER_URL` (set in Vercel env vars) so you can use your own yt-dlp/ytdl-core worker.
- Root is `web/`.

## Run locally
```bash
# from repo root
npx serve web
```

## Deploy to Vercel
1) Project root: `web/`
2) Framework preset: Other (no build step)
3) Env var: `REMOTE_WORKER_URL=https://your-worker.example.com`

## Hooking up your worker
- POST `/info` and `/download` to your worker; it should return JSON with fields like `title`, `duration`, `file`, `message`.
- Keep yt-dlp/ffmpeg on the worker side; Vercel functions just proxy.

## Worker hosting ideas
- Render (Web Service) with Python + yt-dlp + ffmpeg
- Fly.io, Railway, or a small VPS—anything that lets you install yt-dlp/ffmpeg
