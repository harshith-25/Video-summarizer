from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import Config
from urllib.parse import urlparse

engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def check_and_create_database():
    uri = Config.SQLALCHEMY_DATABASE_URI
    if not uri or not uri.startswith("postgresql"):
        # SQLite or other databases handle auto-creation natively, or we only handle PostgreSQL here
        return

    # Parse URI to get database name and host details
    result = urlparse(uri)
    db_name = result.path.lstrip('/')
    
    # Rebuild connection string to connect to the default 'postgres' database
    netloc = result.netloc
    default_uri = f"{result.scheme}://{netloc}/postgres"
    
    # Create engine with AUTOCOMMIT to run database-level commands outside a transaction block
    temp_engine = create_engine(default_uri, isolation_level="AUTOCOMMIT")
    with temp_engine.connect() as conn:
        # Check if target database exists
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": db_name}
        ).scalar()
        
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            
    temp_engine.dispose()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()