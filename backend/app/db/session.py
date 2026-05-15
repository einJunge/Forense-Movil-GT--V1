from sqlalchemy.orm import sessionmaker
from app.db.base import engine
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
