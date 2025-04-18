from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chat_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) ## hmm instead of directly connecting/request like I am
# they are using something called sqlalchemy.
Base = declarative_base()

# Dependency to get DB session
# why is this a generator function ?
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 