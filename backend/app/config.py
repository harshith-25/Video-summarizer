import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    
    # Base directory of the app
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # PostgreSQL database URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        # Fallback to postgres default for safety, but log/raise warning
        DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/video_summarizer"
    
    # Standard SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JWT_ACCESS_TOKEN_EXPIRES = 43200  # 12 hours
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/app.log'
    
    # Paths for files
    USER_DOCUMENTS_PATH = os.getenv("USER_DOCUMENTS_PATH", "data/user_documents")
    if not os.path.isabs(USER_DOCUMENTS_PATH):
        USER_DOCUMENTS_PATH = os.path.abspath(os.path.join(BASE_DIR, USER_DOCUMENTS_PATH))
        
    DEFAULT_CHUNK_SIZE = int(os.getenv('DEFAULT_CHUNK_SIZE', '600'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '250'))
    
    # Path to multilingual font for PDF generation (ReportLab)
    NIRMALA_FONT_PATH = os.getenv("NIRMALA_FONT_PATH", "C:\\Windows\\Fonts\\Nirmala.ttc")
    
    # Frontend URL (for OAuth redirect callbacks)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')