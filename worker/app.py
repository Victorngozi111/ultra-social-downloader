from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import yt_dlp

TMP_DIR = Path(tempfile.gettempdir()) / "apexion_dl"
TMP_DIR.mkdir(parents=True, exist_ok=True)

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
    if quality and quality.lower() != "best":
        # Non-strict quality hint; falls back to best if unavailable.
        q = quality.replace("p", "")
        fmt = f"bv*[height<={q}]+ba/b[height<={q}]/{fmt}"
    return {
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
    }


@app.post("/info")
async def info(payload: InfoRequest):
    opts = _ydl_opts(payload.quality)
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

    # Save to temp; in production, upload to object storage and return a signed URL.
    opts.update({
        "outtmpl": str(TMP_DIR / "%(title)s.%(ext)s"),
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
    return FileResponse(safe_path)


@app.get("/")
async def root():
    return {"ok": True, "message": "apeXion worker online"}
