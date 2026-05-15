from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Finding
router = APIRouter()
@router.get("")
def list_findings(db: Session = Depends(get_db)): return db.query(Finding).all()
@router.get("/scan/{scan_id}")
def findings_by_scan(scan_id: int, db: Session = Depends(get_db)):
    return db.query(Finding).filter(Finding.scan_id == scan_id).all()
