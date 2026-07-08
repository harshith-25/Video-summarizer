from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, JSON, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Transcript(Base):
    __tablename__ = 'transcripts'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text)
    segments_json = Column(JSON)  # List of segments with timestamps
    model_name = Column(String(50))  # whisper model or subtitle source
    language = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship('Video', back_populates='transcript')
    
    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'raw_text': self.raw_text,
            'cleaned_text': self.cleaned_text,
            'segments_json': self.segments_json,
            'model_name': self.model_name,
            'language': self.language,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
