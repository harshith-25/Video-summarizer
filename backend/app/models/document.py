from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    summary_id = Column(Integer, ForeignKey('summaries.id', ondelete='CASCADE'), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, md
    file_size = Column(Integer)  # in bytes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    summary = relationship('Summary', back_populates='documents')
    
    def to_dict(self):
        return {
            'id': self.id,
            'summary_id': self.summary_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
