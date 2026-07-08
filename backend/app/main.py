from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import Config
from app.database import engine, Base, SessionLocal
from app.routes import auth_router, video_router
from app.utils.logger import setup_logger
from app.middleware.logger_middleware import logger_middleware
from app.models.user import User

# Configure startup/shutdown lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("app")
    logger.info("Running application startup checks...")
    
    # Auto-create tables in PostgreSQL database
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize database tables: {e}", exc_info=True)
        
    # Auto-create default administrator
    create_default_admin()
    
    yield
    logger.info("Shutting down FastAPI application...")

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Video Summarizer API",
        description="A backend for transcribing and summarizing online videos and direct uploads.",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Initialize logger utility
    setup_logger()
    
    # Logger Middleware
    app.middleware("http")(logger_middleware)
    
    # Setup CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://silfratech.in"
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Type", "Authorization"]
    )
    
    # Register blueprints (APIRouters)
    app.include_router(auth_router)
    app.include_router(video_router)
    
    return app

def create_default_admin():
    db = SessionLocal()
    logger = logging.getLogger("app")
    try:
        # Check if default admin exists
        admin = db.query(User).filter(User.email == 'admin@videosummarizer.com').first()
        
        if not admin:
            admin = User(
                email='admin@videosummarizer.com',
                full_name='Admin User',
                role='Admin'
            )
            admin.set_password('admin123')
            db.add(admin)
            db.commit()
            logger.info("Default admin user created: admin@videosummarizer.com / admin123")
        else:
            logger.info("Admin user already exists")

    except Exception as e:
        logger.error(f"Error creating default admin user: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()