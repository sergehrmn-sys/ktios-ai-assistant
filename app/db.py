from dotenv import load_dotenv
load_dotenv()

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:Oceane.15216556%24@localhost:5432/ai_frontdesk?client_encoding=utf8"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, connect_args={"options": "-c client_encoding=utf8"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()