import shutil, subprocess
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.adb_service import discover_devices, connect_wifi, disconnect_wifi
from pydantic import BaseModel

router = APIRouter()

class WifiConnect(BaseModel):
    host: str
    port: int = 5555

@router.get("/status")
def adb_status():
    adb_path = shutil.which('adb')
    if not adb_path:
        return {'adb_installed': False, 'message': 'adb no encontrado. Instala con: sudo apt install adb'}
    try:
        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        lines = [l for l in r.stdout.strip().split('\n')[1:] if l.strip()]
        return {'adb_installed': True, 'adb_path': adb_path, 'raw_devices': lines}
    except Exception as e:
        return {'adb_installed': True, 'adb_path': adb_path, 'error': str(e)}

@router.get("/discover")
def discover(db: Session = Depends(get_db)):
    return {"discovered_devices": discover_devices(db)}

@router.post("/connect-wifi")
def wifi_connect(body: WifiConnect):
    return connect_wifi(body.host, body.port)

@router.post("/disconnect-wifi")
def wifi_disconnect(body: WifiConnect):
    return disconnect_wifi(body.host, body.port)
