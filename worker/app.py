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
import shutil
import uuid

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


def _ydl_opts(quality: Optional[str], source_url: Optional[str] = None, *, is_video: bool = True) -> dict:
    # Build domain-aware headers so sites like Pinterest respect the request.
    headers = DEFAULT_HEADERS.copy()
    if source_url:
        try:
            # Use the source URL as referer when available to appease origin checks.
            headers["Referer"] = str(source_url)
        except Exception:
            pass
    # Prefer widely supported H.264/AAC in an MP4 container to avoid "codec not supported" issues.
    height_clause = ""
    if quality:
        normalized = str(quality).strip().lower()
        if normalized and normalized != "best":
            q = "".join(ch for ch in normalized if ch.isdigit())
            if q:
                height_clause = f"[height<={q}]"

    if is_video:
        fmt = (
            f"bv*[ext=mp4][vcodec^=avc1]{height_clause}+ba[ext=m4a]/"
            f"bv*[ext=mp4]{height_clause}+ba[ext=m4a]/"
            f"b[ext=mp4]{height_clause}/"
            "best[ext=mp4]/best"
        )
    else:
        # For images (no video codec), just grab the best available original file.
        fmt = "best/b"

    opts = {
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "http_headers": headers,
        # Force safe filenames from yt-dlp to avoid spaces/hashtags breaking /files/ serving.
        "restrictfilenames": True,
        "windowsfilenames": True,
    }

    if is_video:
        opts["merge_output_format"] = "mp4"
        # Remux to MP4 to avoid HEVC/VP9 playback issues in common players.
        opts["postprocessors"] = [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"},
        ]

    return opts


def _safe_filename(raw: str) -> str:
    """Generate a safe, deterministic filename component."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw or "file")
    cleaned = cleaned.strip("._-") or "file"
    return cleaned[:120]


def _session_dir() -> Path:
    # Keep each download in its own folder to avoid cross-talk between parallel downloads.
    path = TMP_DIR / f"job_{uuid.uuid4().hex[:12]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@app.post("/info")
async def info(payload: InfoRequest):
    # Use safest defaults for metadata to reduce extractor-specific issues.
    opts = _ydl_opts(None, payload.url, is_video=True)
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
    # Step 1: fetch metadata to derive a safe base name.
    info_opts = _ydl_opts(None, payload.url, is_video=True)
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(str(payload.url), download=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch info before download: {exc}")

    base_name = _safe_filename(info.get("title") or info.get("id") or "download")

    # Detect whether this is a video (has vcodec) or just an image/resource.
    def _is_video(meta: dict) -> bool:
        if meta.get("vcodec") and meta.get("vcodec") != "none":
            return True
        for f in meta.get("formats") or []:
            if f.get("vcodec") and f.get("vcodec") != "none":
                return True
        return False

    is_video = _is_video(info)

    # Step 2: download with a deterministic, safe filename.
    job_dir = _session_dir()
    dl_opts = _ydl_opts(payload.quality, payload.url, is_video=is_video)
    dl_opts.update({
        "outtmpl": str(job_dir / f"{base_name}.%(ext)s"),
    })

    try:
        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.download([str(payload.url)])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Download failed: {exc}")

    # Pick the newest actual media file in the job dir as the result (avoids mixing outputs across requests).
    candidates = [p for p in job_dir.glob("*") if p.is_file()]
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise HTTPException(status_code=500, detail="No file produced")

    file_path = candidates[0]

    # Ensure the produced filename is slug-safe (double safety if extractor changed the name).
    safe_base = _safe_filename(file_path.stem)
    safe_name = f"{safe_base}{file_path.suffix}"
    if safe_name != file_path.name:
        safe_target = TMP_DIR / safe_name
        try:
            if safe_target.exists():
                safe_target.unlink()
            file_path.rename(safe_target)
            file_path = safe_target
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
