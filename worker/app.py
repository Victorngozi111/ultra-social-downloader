from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp

TMP_DIR = Path(tempfile.gettempdir()) / "apexion_dl"
TMP_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.instagram.com/",
}

app = FastAPI(title="apeXion Downloader Worker")


class InfoRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = None


class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: Optional[str] = None


def _ydl_opts(quality: Optional[str]) -> dict:
    # Adjust formats to your needs; ffmpeg must be available on the worker host.
    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"

    # Normalize the quality hint; ignore "best" and any non-numeric noise.
    if quality:
        normalized = str(quality).strip().lower()
        if normalized and normalized != "best":
            # Extract digits only (e.g., "1080p" -> "1080"); fall back to best if nothing usable.
            q = "".join(ch for ch in normalized if ch.isdigit())
            if q:
                fmt = f"bv*[height<={q}]+ba/b[height<={q}]/{fmt}"
    return {
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "http_headers": DEFAULT_HEADERS,
    }


def _safe_filename(raw: str) -> str:
    """Generate a safe, deterministic filename component."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw or "file")
    cleaned = cleaned.strip("._-") or "file"
    return cleaned[:120]


@app.post("/info")
async def info(payload: InfoRequest):
    # Use safest defaults for metadata to reduce extractor-specific issues.
    opts = _ydl_opts(None)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(str(payload.url), download=False)
    except Exception as exc:  # broad to surface upstream errors
        raise HTTPException(status_code=400, detail=f"Failed to fetch info: {exc}")

    return {
        "title": data.get("title"),
        "duration": data.get("duration"),
        "thumbnail": data.get("thumbnail"),
        "uploader": data.get("uploader"),
        "description": data.get("description"),
        "message": "Metadata fetched",
    }


@app.post("/download")
async def download(payload: DownloadRequest, request: Request):
    opts = _ydl_opts(payload.quality)

    # Force a predictable, safe filename: use video id when available; fallback to slugged title.
    out_id = "%(id)s"
    out_title = "%(title)s"
    opts.update({
        "outtmpl": str(TMP_DIR / f"{out_id}.%(ext)s"),
    })

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([str(payload.url)])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Download failed: {exc}")

    # Pick the newest file in the temp dir as the result.
    candidates = sorted(TMP_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise HTTPException(status_code=500, detail="No file produced")

    file_path = candidates[0]

    # Build a user-friendly filename for download (prefer title if present).
    friendly_name = file_path.name
    try:
        # If yt_dlp stored the id-based filename, try to swap to a safe, title-based name for the download URL.
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(str(payload.url), download=False)
            title = info.get("title") if isinstance(info, dict) else None
            if title:
                safe_title = _safe_filename(title)
                friendly_name = f"{safe_title}{file_path.suffix}"
                safe_target = TMP_DIR / friendly_name
                if safe_target != file_path:
                    try:
                        if safe_target.exists():
                            safe_target.unlink()
                        file_path.rename(safe_target)
                        file_path = safe_target
                    except Exception:
                        pass
    except Exception:
        pass
    # Build a download URL that serves from this worker.
    base_url = str(request.base_url).rstrip("/")
    download_url = f"{base_url}/files/{file_path.name}"

    return {
        "file": file_path.name,
        "path": str(file_path),
        "download_url": download_url,
        "message": "Download ready.",
    }


@app.get("/files/{filename}")
async def serve_file(filename: str):
    # Prevent path traversal
    safe_path = (TMP_DIR / filename).resolve()
    if not str(safe_path).startswith(str(TMP_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not safe_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(safe_path, filename=safe_path.name)


@app.get("/")
async def root():
    return {"ok": True, "message": "apeXion worker online"}
