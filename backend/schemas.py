from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# Channel schemas
class ChannelBase(BaseModel):
    name: str
    stream_url: str
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    tvg_logo: Optional[str] = None
    group_title: Optional[str] = None


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    stream_url: Optional[str] = None
    tvg_id: Optional[str] = None
    tvg_name: Optional[str] = None
    tvg_logo: Optional[str] = None
    group_title: Optional[str] = None


class ChannelResponse(ChannelBase):
    id: str
    playlist_id: str
    position: int

    class Config:
        from_attributes = True


# Playlist schemas
class PlaylistBase(BaseModel):
    original_filename: str


class PlaylistResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    channels_count: int
    file_size: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlaylistDetail(PlaylistResponse):
    channels: List[ChannelResponse] = []
    groups: List[str] = []


# Bulk operation schemas
class BulkDeleteRequest(BaseModel):
    channel_ids: List[str]


class BulkMoveRequest(BaseModel):
    channel_ids: List[str]
    group_title: str


class ReorderRequest(BaseModel):
    channel_ids: List[str]  # Ordered list of channel IDs


class UploadResponse(BaseModel):
    id: str
    filename: str
    channels_count: int
    uploaded_at: datetime
