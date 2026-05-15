import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fmgt.db")
engine = create_engine(DATABASE_URL, future=True)
Base = declarative_base()
