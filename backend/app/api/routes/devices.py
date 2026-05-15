from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Device
from app.schemas.device import DeviceCreate
router = APIRouter()
@router.get("")
def list_devices(db: Session = Depends(get_db)): return db.query(Device).all()
@router.post("")
def create_device(dev: DeviceCreate, db: Session = Depends(get_db)):
    obj = Device(**dev.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj
