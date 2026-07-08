from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Summary(Base):
    __tablename__ = 'summaries'
    
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    executive_summary = Column(Text, nullable=False)
    detailed_summary = Column(Text, nullable=False)
    key_topics = Column(JSON)  # List of topics with description
    action_items = Column(JSON)  # List of action items
    timeline = Column(JSON)  # Key timestamps and descriptions
    conclusion = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    video = relationship('Video', back_populates='summary')
    documents = relationship('Document', back_populates='summary', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'executive_summary': self.executive_summary,
            'detailed_summary': self.detailed_summary,
            'key_topics': self.key_topics,
            'action_items': self.action_items,
            'timeline': self.timeline,
            'conclusion': self.conclusion,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
