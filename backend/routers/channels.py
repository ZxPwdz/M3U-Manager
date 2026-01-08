from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import Playlist, Channel
from schemas import (
    ChannelResponse, ChannelCreate, ChannelUpdate,
    BulkDeleteRequest, BulkMoveRequest, ReorderRequest
)

router = APIRouter(prefix="/api/playlists/{playlist_id}/channels", tags=["channels"])


def get_playlist_or_404(playlist_id: str, db: Session) -> Playlist:
    """Get playlist or raise 404."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.get("", response_model=List[ChannelResponse])
def list_channels(
    playlist_id: str,
    search: Optional[str] = Query(None, description="Search in name, group, URL"),
    group: Optional[str] = Query(None, description="Filter by group"),
    db: Session = Depends(get_db)
):
    """List all channels in a playlist with optional filtering."""
    get_playlist_or_404(playlist_id, db)

    query = db.query(Channel).filter(Channel.playlist_id == playlist_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Channel.name.ilike(search_term),
                Channel.group_title.ilike(search_term),
                Channel.stream_url.ilike(search_term)
            )
        )

    if group:
        query = query.filter(Channel.group_title == group)

    channels = query.order_by(Channel.position).all()
    return channels


@router.post("", response_model=ChannelResponse)
def create_channel(
    playlist_id: str,
    channel_data: ChannelCreate,
    db: Session = Depends(get_db)
):
    """Add a new channel to the playlist."""
    playlist = get_playlist_or_404(playlist_id, db)

    # Get the next position
    max_position = db.query(Channel.position).filter(
        Channel.playlist_id == playlist_id
    ).order_by(Channel.position.desc()).first()
    next_position = (max_position[0] + 1) if max_position else 0

    channel = Channel(
        playlist_id=playlist_id,
        position=next_position,
        name=channel_data.name,
        stream_url=channel_data.stream_url,
        tvg_id=channel_data.tvg_id,
        tvg_name=channel_data.tvg_name,
        tvg_logo=channel_data.tvg_logo,
        group_title=channel_data.group_title
    )
    db.add(channel)

    # Update playlist channel count
    playlist.channels_count += 1

    db.commit()
    db.refresh(channel)
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(
    playlist_id: str,
    channel_id: str,
    channel_data: ChannelUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing channel."""
    get_playlist_or_404(playlist_id, db)

    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.playlist_id == playlist_id
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update only provided fields
    update_data = channel_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}")
def delete_channel(
    playlist_id: str,
    channel_id: str,
    db: Session = Depends(get_db)
):
    """Delete a channel from the playlist."""
    playlist = get_playlist_or_404(playlist_id, db)

    channel = db.query(Channel).filter(
        Channel.id == channel_id,
        Channel.playlist_id == playlist_id
    ).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    deleted_position = channel.position
    db.delete(channel)

    # Update positions of channels after the deleted one
    db.query(Channel).filter(
        Channel.playlist_id == playlist_id,
        Channel.position > deleted_position
    ).update({Channel.position: Channel.position - 1})

    # Update playlist channel count
    playlist.channels_count -= 1

    db.commit()
    return {"message": "Channel deleted successfully"}


@router.put("/reorder")
def reorder_channels(
    playlist_id: str,
    reorder_data: ReorderRequest,
    db: Session = Depends(get_db)
):
    """Reorder channels based on the provided order of IDs."""
    get_playlist_or_404(playlist_id, db)

    for position, channel_id in enumerate(reorder_data.channel_ids):
        db.query(Channel).filter(
            Channel.id == channel_id,
            Channel.playlist_id == playlist_id
        ).update({Channel.position: position})

    db.commit()
    return {"message": "Channels reordered successfully"}


@router.delete("/bulk")
def bulk_delete_channels(
    playlist_id: str,
    bulk_data: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """Delete multiple channels at once."""
    playlist = get_playlist_or_404(playlist_id, db)

    deleted_count = db.query(Channel).filter(
        Channel.id.in_(bulk_data.channel_ids),
        Channel.playlist_id == playlist_id
    ).delete(synchronize_session=False)

    # Update playlist channel count
    playlist.channels_count -= deleted_count

    # Recalculate positions
    remaining_channels = db.query(Channel).filter(
        Channel.playlist_id == playlist_id
    ).order_by(Channel.position).all()

    for i, channel in enumerate(remaining_channels):
        channel.position = i

    db.commit()
    return {"message": f"Deleted {deleted_count} channels"}


@router.put("/bulk-move")
def bulk_move_channels(
    playlist_id: str,
    bulk_data: BulkMoveRequest,
    db: Session = Depends(get_db)
):
    """Move multiple channels to a different group."""
    get_playlist_or_404(playlist_id, db)

    updated_count = db.query(Channel).filter(
        Channel.id.in_(bulk_data.channel_ids),
        Channel.playlist_id == playlist_id
    ).update({Channel.group_title: bulk_data.group_title}, synchronize_session=False)

    db.commit()
    return {"message": f"Moved {updated_count} channels to group '{bulk_data.group_title}'"}
