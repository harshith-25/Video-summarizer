from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # youtube, vimeo, drive, dropbox, onedrive, upload
    source_url = Column(String(1000))
    local_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)  # in bytes
    duration = Column(Float)  # in seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='videos')
    transcript = relationship('Transcript', back_populates='video', uselist=False, cascade='all, delete-orphan')
    summary = relationship('Summary', back_populates='video', uselist=False, cascade='all, delete-orphan')
    jobs = relationship('Job', back_populates='video', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'duration': self.duration,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
