import subprocess, shutil, logging
from sqlalchemy.orm import Session
from app.db.models import Device

logger = logging.getLogger(__name__)

def adb_available():
    return shutil.which('adb') is not None

def run_adb(serial: str, *args, timeout=30) -> str:
    try:
        r = subprocess.run(['adb', '-s', serial] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f'ERROR: {e}'

def connect_wifi(host: str, port: int = 5555) -> dict:
    if not adb_available():
        return {'result': 'ERROR: adb no está instalado en el sistema'}
    try:
        out = subprocess.run(
            ['adb', 'connect', f'{host}:{port}'],
            capture_output=True, text=True, timeout=15
        ).stdout.strip()
        return {'result': out, 'success': 'connected' in out.lower() or 'already' in out.lower()}
    except Exception as e:
        return {'result': f'ERROR: {e}', 'success': False}

def disconnect_wifi(host: str, port: int = 5555) -> dict:
    try:
        out = subprocess.run(['adb', 'disconnect', f'{host}:{port}'],
                             capture_output=True, text=True, timeout=10).stdout
        return {'result': out.strip()}
    except Exception as e:
        return {'result': f'ERROR: {e}'}

def get_adb_devices_raw() -> list[str]:
    """Retorna lista de seriales activos según adb devices"""
    try:
        r = subprocess.run(['adb', 'devices', '-l'],
                           capture_output=True, text=True, timeout=15)
        lines = r.stdout.strip().split('\n')[1:]
        serials = []
        for line in lines:
            line = line.strip()
            if not line: continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] not in ('offline', 'unauthorized'):
                serials.append(parts[0])
        return serials
    except Exception as e:
        logger.error(f'adb devices error: {e}')
        return []

def discover_devices(db: Session):
    if not adb_available():
        return []

    serials = get_adb_devices_raw()
    if not serials:
        return []

    found = []
    for serial in serials:
        model         = run_adb(serial, 'shell', 'getprop', 'ro.product.model')
        manufacturer  = run_adb(serial, 'shell', 'getprop', 'ro.product.manufacturer')
        android_ver   = run_adb(serial, 'shell', 'getprop', 'ro.build.version.release')
        sdk_ver       = run_adb(serial, 'shell', 'getprop', 'ro.build.version.sdk')
        root_out      = run_adb(serial, 'shell', 'su', '-c', 'id')
        root_status   = 'uid=0' in root_out
        connect_type  = 'wifi' if ':' in serial else 'usb'

        existing = db.query(Device).filter(Device.adb_serial == serial).first()
        if existing:
            existing.model          = model or existing.model
            existing.manufacturer   = manufacturer or existing.manufacturer
            existing.android_version= android_ver or existing.android_version
            existing.sdk_version    = sdk_ver or existing.sdk_version
            existing.root_status    = root_status
            existing.connect_type   = connect_type
            db.commit(); db.refresh(existing)
            found.append(existing)
        else:
            d = Device(adb_serial=serial, model=model, manufacturer=manufacturer,
                       android_version=android_ver, sdk_version=sdk_ver,
                       root_status=root_status, connect_type=connect_type)
            db.add(d); db.commit(); db.refresh(d)
            found.append(d)
    return found
