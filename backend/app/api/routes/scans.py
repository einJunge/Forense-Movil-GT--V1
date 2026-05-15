from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Scan
from app.schemas.scan import ScanCreate
from app.services.scan_service import start_scan
import threading, time

router = APIRouter()
SCAN_PROGRESS = {}

@router.get("")
def list_scans(db: Session = Depends(get_db)): return db.query(Scan).all()

@router.get("/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    s = db.query(Scan).filter(Scan.id == scan_id).first()
    if not s: raise HTTPException(404, "Scan not found")
    return s

@router.get('/progress/{device_id}')
def get_scan_progress(device_id: int):
    return SCAN_PROGRESS.get(str(device_id), {'device_id': device_id, 'status': 'idle', 'percent': 0, 'stage': 'Sin ejecución'})


def run_scan(db_factory, device_id: int):
    try:
        key = str(device_id)
        steps = [
            (10, 'Preparando análisis'),
            (25, 'Recolectando información del dispositivo'),
            (45, 'Analizando permisos y aplicaciones'),
            (65, 'Evaluando puertos y artefactos'),
            (85, 'Calculando riesgo y guardando resultados'),
        ]
        for pct, stage in steps:
            SCAN_PROGRESS[key] = {'device_id': device_id, 'status': 'running', 'percent': pct, 'stage': stage, 'updated_at': time.time()}
            time.sleep(1)
        db = next(db_factory())
        result = start_scan(db, device_id)
        SCAN_PROGRESS[key] = {'device_id': device_id, 'status': 'done', 'percent': 100, 'stage': 'Escaneo completado', 'updated_at': time.time()}
        db.close()
        return result
    except Exception as e:
        SCAN_PROGRESS[str(device_id)] = {'device_id': device_id, 'status': 'error', 'percent': 100, 'stage': str(e), 'updated_at': time.time()}

@router.post("")
def create_scan(sc: ScanCreate, db: Session = Depends(get_db)):
    threading.Thread(target=run_scan, args=(get_db, sc.device_id), daemon=True).start()
    return {'ok': True, 'started': True, 'device_id': sc.device_id}
