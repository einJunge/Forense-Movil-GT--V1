from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Event
router = APIRouter()
@router.get("")
def list_events(db: Session = Depends(get_db)): return db.query(Event).all()
@router.get("/scan/{scan_id}")
def events_by_scan(scan_id: int, db: Session = Depends(get_db)):
    return db.query(Event).filter(Event.scan_id == scan_id).all()
