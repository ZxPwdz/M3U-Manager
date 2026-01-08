import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)  # stored filename
    original_filename = Column(String(255), nullable=False)  # original upload name
    channels_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    channels = relationship("Channel", back_populates="playlist", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    playlist_id = Column(String(36), ForeignKey("playlists.id"), nullable=False)
    position = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    tvg_id = Column(String(255), nullable=True)
    tvg_name = Column(String(255), nullable=True)
    tvg_logo = Column(Text, nullable=True)
    group_title = Column(String(255), nullable=True)
    stream_url = Column(Text, nullable=False)

    playlist = relationship("Playlist", back_populates="channels")
