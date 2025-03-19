from sqlalchemy import text
from .db import engine, Base
from .models import User, Chat, Message

def recreate_tables():
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped successfully!")
    
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    recreate_tables() 