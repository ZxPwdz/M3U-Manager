import os
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import Playlist, Channel
from schemas import PlaylistResponse, PlaylistDetail, UploadResponse
from m3u_parser import parse_m3u, generate_m3u

router = APIRouter(prefix="/api/playlists", tags=["playlists"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_playlist(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and parse an M3U/M3U8 playlist file."""
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.m3u', '.m3u8']:
        raise HTTPException(status_code=400, detail="Only .m3u and .m3u8 files are allowed")

    # Read file content
    content = await file.read()
    try:
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            content_str = content.decode('latin-1')
        except:
            raise HTTPException(status_code=400, detail="Unable to decode file content")

    # Parse M3U content
    channels_data = parse_m3u(content_str)
    if not channels_data:
        raise HTTPException(status_code=400, detail="No valid channels found in the file")

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save original file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_str)

    # Create playlist record
    playlist = Playlist(
        filename=unique_filename,
        original_filename=file.filename,
        channels_count=len(channels_data),
        file_size=len(content)
    )
    db.add(playlist)
    db.flush()  # Get the playlist ID

    # Create channel records
    for position, channel_data in enumerate(channels_data):
        channel = Channel(
            playlist_id=playlist.id,
            position=position,
            name=channel_data.name,
            tvg_id=channel_data.tvg_id,
            tvg_name=channel_data.tvg_name,
            tvg_logo=channel_data.tvg_logo,
            group_title=channel_data.group_title,
            stream_url=channel_data.stream_url
        )
        db.add(channel)

    db.commit()
    db.refresh(playlist)

    return UploadResponse(
        id=playlist.id,
        filename=playlist.original_filename,
        channels_count=playlist.channels_count,
        uploaded_at=playlist.created_at
    )


@router.get("", response_model=List[PlaylistResponse])
def list_playlists(db: Session = Depends(get_db)):
    """List all uploaded playlists."""
    playlists = db.query(Playlist).order_by(Playlist.created_at.desc()).all()
    return playlists


@router.get("/{playlist_id}", response_model=PlaylistDetail)
def get_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Get playlist details including channels and groups."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Get unique groups
    groups = db.query(Channel.group_title).filter(
        Channel.playlist_id == playlist_id,
        Channel.group_title.isnot(None)
    ).distinct().all()
    group_list = sorted([g[0] for g in groups if g[0]])

    return PlaylistDetail(
        id=playlist.id,
        filename=playlist.filename,
        original_filename=playlist.original_filename,
        channels_count=playlist.channels_count,
        file_size=playlist.file_size,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        channels=sorted(playlist.channels, key=lambda c: c.position),
        groups=group_list
    )


@router.get("/{playlist_id}/download")
def download_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Download the playlist as an M3U file."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Get channels sorted by position
    channels = db.query(Channel).filter(
        Channel.playlist_id == playlist_id
    ).order_by(Channel.position).all()

    # Generate M3U content
    m3u_content = generate_m3u(channels)

    # Return as downloadable file
    return Response(
        content=m3u_content,
        media_type="audio/x-mpegurl",
        headers={
            "Content-Disposition": f'attachment; filename="{playlist.original_filename}"'
        }
    )


@router.get("/stream/{filename}")
def stream_playlist(filename: str, db: Session = Depends(get_db)):
    """Get the playlist as a direct M3U stream for IPTV programs."""
    # Strip .m3u or .m3u8 extension to get the playlist ID
    playlist_id = filename
    for ext in ['.m3u8', '.m3u']:
        if playlist_id.endswith(ext):
            playlist_id = playlist_id[:-len(ext)]
            break

    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Get channels sorted by position
    channels = db.query(Channel).filter(
        Channel.playlist_id == playlist_id
    ).order_by(Channel.position).all()

    # Generate M3U content
    m3u_content = generate_m3u(channels)

    # Return as inline content (no download prompt)
    return Response(
        content=m3u_content,
        media_type="audio/x-mpegurl"
    )


@router.delete("/{playlist_id}")
def delete_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Delete a playlist and all its channels."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Delete the stored file
    file_path = os.path.join(UPLOAD_DIR, playlist.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete playlist (channels cascade)
    db.delete(playlist)
    db.commit()

    return {"message": "Playlist deleted successfully"}
