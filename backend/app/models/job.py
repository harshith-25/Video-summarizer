from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='SET NULL'), nullable=True, index=True)
    status = Column(String(20), default='queued', nullable=False)  # queued, processing, completed, failed
    progress = Column(Integer, default=0, nullable=False)  # 0 to 100
    message = Column(String(255), default='Job created')
    error_message = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='jobs')
    video = relationship('Video', back_populates='jobs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_id': self.video_id,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
