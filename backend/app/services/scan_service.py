import subprocess, os, hashlib, tempfile
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Scan, Finding, Event, Device, Artifact
from app.tools.clamav_wrapper import scan_file_clamav

DANGEROUS_PERMISSIONS = [
    'android.permission.READ_SMS',
    'android.permission.SEND_SMS',
    'android.permission.READ_CALL_LOG',
    'android.permission.RECORD_AUDIO',
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.READ_CONTACTS',
    'android.permission.CAMERA',
    'android.permission.PROCESS_OUTGOING_CALLS',
    'android.permission.READ_PHONE_STATE',
    'android.permission.RECEIVE_BOOT_COMPLETED',
    'android.permission.INSTALL_PACKAGES',
    'android.permission.WRITE_SETTINGS',
    'android.permission.SYSTEM_ALERT_WINDOW',
    'android.permission.BIND_ACCESSIBILITY_SERVICE',
    'android.permission.BIND_DEVICE_ADMIN',
]

def adb(serial, *args, timeout=60):
    try:
        r = subprocess.run(['adb', '-s', serial] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f'ERROR: {e}'

def log(db, scan_id, source, message):
    db.add(Event(scan_id=scan_id, source=source, message=message, timestamp=datetime.utcnow()))
    db.commit()

def finding(db, scan_id, category, severity, tool, evidence):
    db.add(Finding(scan_id=scan_id, category=category, severity=severity, tool=tool, evidence=evidence))
    db.commit()

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''): h.update(chunk)
    return h.hexdigest()

def start_scan(db: Session, device_id: int):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return {'error': 'Device not found'}

    serial = device.adb_serial
    scan = Scan(device_id=device_id, status='running', risk_level='low', started_at=datetime.utcnow())
    db.add(scan); db.commit(); db.refresh(scan)
    sid = scan.id
    severities = []

    log(db, sid, 'scan', f'Iniciando escaneo en {serial} ({device.model})')

    # ── 1. PAQUETES INSTALADOS ──────────────────────────────────
    log(db, sid, 'adb', 'Enumerando paquetes instalados...')
    packages_raw = adb(serial, 'shell', 'pm', 'list', 'packages', '-f', '-3')
    packages = [l.split('=')[-1] for l in packages_raw.splitlines() if l.startswith('package:')]
    log(db, sid, 'adb', f'{len(packages)} paquetes de terceros encontrados')

    # ── 2. PERMISOS PELIGROSOS ──────────────────────────────────
    log(db, sid, 'adb', 'Analizando permisos...')
    for pkg in packages:
        dumpsys = adb(serial, 'shell', 'dumpsys', 'package', pkg)
        for perm in DANGEROUS_PERMISSIONS:
            if perm in dumpsys and 'granted=true' in dumpsys:
                finding(db, sid, 'dangerous_permission', 'high', 'adb',
                        f'{pkg} tiene permiso peligroso: {perm}')
                severities.append('high')

    # ── 3. APPS EN MODO ADMIN / ACCESIBILIDAD ──────────────────
    log(db, sid, 'adb', 'Revisando administradores de dispositivo...')
    admin_raw = adb(serial, 'shell', 'dumpsys', 'device_policy')
    if 'admin' in admin_raw.lower():
        finding(db, sid, 'device_admin', 'critical', 'adb',
                f'App con privilegios de administrador detectada')
        severities.append('critical')

    # ── 4. SERVICIOS DE ACCESIBILIDAD ──────────────────────────
    acc_raw = adb(serial, 'shell', 'settings', 'get', 'secure', 'enabled_accessibility_services')
    if acc_raw and acc_raw != 'null':
        finding(db, sid, 'accessibility_service', 'high', 'adb',
                f'Servicios de accesibilidad activos: {acc_raw}')
        severities.append('high')

    # ── 5. PUERTOS DE RED ABIERTOS ─────────────────────────────
    log(db, sid, 'adb', 'Escaneando puertos de red...')
    netstat = adb(serial, 'shell', 'ss', '-tlnp')
    if not netstat or 'ERROR' in netstat:
        netstat = adb(serial, 'shell', 'netstat', '-tlnp')
    suspicious_ports = ['4444', '5554', '5555', '9999', '31337']
    for port in suspicious_ports:
        if port in netstat:
            finding(db, sid, 'open_port', 'critical', 'network',
                    f'Puerto sospechoso abierto: {port}')
            severities.append('critical')

    # ── 6. PROCESOS EN EJECUCIÓN ───────────────────────────────
    log(db, sid, 'adb', 'Analizando procesos...')
    ps_out = adb(serial, 'shell', 'ps', '-A')
    suspicious_procs = ['nc ', 'ncat', 'netcat', 'metasploit', 'tcpdump', 'frida', 'magisk']
    for proc in suspicious_procs:
        if proc in ps_out.lower():
            finding(db, sid, 'suspicious_process', 'critical', 'adb',
                    f'Proceso sospechoso en ejecución: {proc.strip()}')
            severities.append('critical')

    # ── 7. ARCHIVOS APK EN SDCARD ──────────────────────────────
    log(db, sid, 'adb', 'Buscando APKs en almacenamiento...')
    apk_list = adb(serial, 'shell', 'find', '/sdcard', '-name', '*.apk', '-type', 'f', timeout=60)
    for apk_path in apk_list.splitlines():
        if apk_path.strip():
            finding(db, sid, 'apk_sideload', 'medium', 'filesystem',
                    f'APK fuera de Play Store encontrado: {apk_path.strip()}')
            severities.append('medium')

    # ── 8. ARCHIVOS SOSPECHOSOS EN /DATA (root) ────────────────
    if device.root_status:
        log(db, sid, 'adb', 'Revisando /data/local/tmp (root)...')
        tmp_files = adb(serial, 'shell', 'su', '-c', 'ls -la /data/local/tmp/')
        if tmp_files and 'ERROR' not in tmp_files and tmp_files.strip():
            finding(db, sid, 'suspicious_files', 'high', 'filesystem',
                    f'Archivos en /data/local/tmp: {tmp_files[:500]}')
            severities.append('high')

    # ── 9. LOGCAT — PALABRAS CLAVE ─────────────────────────────
    log(db, sid, 'adb', 'Analizando logcat...')
    logcat = adb(serial, 'shell', 'logcat', '-d', '-t', '500')
    keywords = ['password', 'token', 'secret', 'credit_card', 'malware', 'exploit', 'inject']
    for kw in keywords:
        if kw in logcat.lower():
            finding(db, sid, 'logcat_leak', 'high', 'logcat',
                    f'Palabra clave sensible en logcat: {kw}')
            severities.append('high')

    # ── 10. CLAMAV EN SDCARD ───────────────────────────────────
    log(db, sid, 'clamav', 'Descargando archivos de /sdcard para escaneo ClamAV...')
    tmpdir = tempfile.mkdtemp()
    adb(serial, 'pull', '/sdcard/Download', tmpdir, timeout=120)
    for root_dir, _, fnames in os.walk(tmpdir):
        for fname in fnames:
            fpath = os.path.join(root_dir, fname)
            try:
                result = scan_file_clamav(fpath)
                if result.get('result') == 'malicious':
                    finding(db, sid, 'malware', 'critical', 'clamav',
                            f'Malware detectado: {fname} — {result["reason"]}')
                    severities.append('critical')
                    fhash = sha256_file(fpath)
                    db.add(Artifact(scan_id=sid, category='malware', subcategory='file',
                                    source_path=fname, size=os.path.getsize(fpath), sha256_hash=fhash))
                    db.commit()
            except Exception:
                pass

    # ── 11. NIVEL DE RIESGO FINAL ──────────────────────────────
    if 'critical' in severities:
        risk = 'critical'
    elif 'high' in severities:
        risk = 'high'
    elif 'medium' in severities:
        risk = 'medium'
    elif severities:
        risk = 'low'
    else:
        risk = 'clean'

    scan.status = 'completed'
    scan.risk_level = risk
    scan.finished_at = datetime.utcnow()
    db.commit(); db.refresh(scan)
    log(db, sid, 'scan', f'Escaneo finalizado. Riesgo: {risk}. Hallazgos: {len(severities)}')
    return scan
