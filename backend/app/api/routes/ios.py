import os, subprocess, shutil, sqlite3, plistlib, hashlib, base64, mimetypes, json, zipfile, threading, time
from fastapi import APIRouter, HTTPException

router = APIRouter()
IOS_PROGRESS = {}
IOS_PROCS = {}


def which(cmd):
    return shutil.which(cmd)


def run_cmd(*cmd, timeout=120):
    try:
        r = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return '', str(e), -1


def terminate_proc(proc):
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    except Exception:
        pass


def set_progress(udid, kind, percent, stage, status='running', extra=None):
    IOS_PROGRESS[udid] = {'udid': udid, 'kind': kind, 'percent': int(percent), 'stage': stage, 'status': status, 'updated_at': time.time(), **(extra or {})}


def backup_root():
    root = os.path.join(os.getcwd(), 'output', 'ios_backups')
    os.makedirs(root, exist_ok=True)
    return root


def export_root():
    root = os.path.join(os.getcwd(), 'output', 'ios_exports')
    os.makedirs(root, exist_ok=True)
    return root


def ensure_backup(udid: str):
    root = backup_root()
    dest = os.path.join(root, udid)
    info_path = os.path.join(dest, 'Info.plist')
    manifest_db = os.path.join(dest, 'Manifest.db')
    if os.path.isdir(dest) and (os.path.exists(info_path) or os.path.exists(manifest_db)):
        return dest, False
    if not which('idevicebackup2'):
        raise HTTPException(500, 'idevicebackup2 not installed')
    os.makedirs(dest, exist_ok=True)
    stdout, stderr, code = run_cmd('idevicebackup2', 'backup', '--full', dest, '-u', udid, timeout=7200)
    if code != 0:
        raise HTTPException(500, f'backup failed: {stderr or stdout or code}')
    return dest, True


def manifest_rows(backup_path: str, where_sql: str = '', params=()):
    db = os.path.join(backup_path, 'Manifest.db')
    if not os.path.isfile(db):
        raise HTTPException(404, 'Manifest.db not found')
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    q = 'SELECT fileID, domain, relativePath, flags FROM Files'
    if where_sql:
        q += ' WHERE ' + where_sql
    q += ' LIMIT 5000'
    rows = cur.execute(q, params).fetchall()
    conn.close()
    out = []
    for fileID, domain, relativePath, flags in rows:
        out.append({'fileID': fileID, 'domain': domain, 'relativePath': relativePath, 'flags': flags})
    return out


def backup_file_real_path(backup_path: str, fileID: str):
    p = os.path.join(backup_path, fileID[:2], fileID)
    return p if os.path.exists(p) else None


def safe_name(x: str):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in (x or 'item'))


def export_rows(backup_path: str, rows, export_name: str, udid: str = ''):
    target_dir = os.path.join(export_root(), export_name)
    os.makedirs(target_dir, exist_ok=True)
    exported = []
    total = len(rows) or 1
    for i, r in enumerate(rows, 1):
        if udid:
            set_progress(udid, 'selective', int((i / total) * 100), f"Exportando {r.get('relativePath') or r.get('fileID')}")
        rp = r.get('relativePath') or os.path.basename(r.get('fileID',''))
        real = backup_file_real_path(backup_path, r['fileID'])
        if not real:
            continue
        rel = rp.lstrip('/').replace('..','_')
        rel = safe_name(r.get('domain','domain')) + '__' + rel.replace('/', '__')
        dst = os.path.join(target_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(real, dst)
            exported.append({'fileID': r['fileID'], 'domain': r['domain'], 'relativePath': r['relativePath'], 'exported_path': dst, 'size': os.path.getsize(dst)})
        except Exception:
            pass
    meta = os.path.join(target_dir, '_export.json')
    with open(meta, 'w', encoding='utf-8') as f:
        json.dump({'count': len(exported), 'items': exported}, f, ensure_ascii=False, indent=2)
    zip_path = target_dir + '.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(target_dir):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, target_dir))
    return target_dir, zip_path, exported


def run_ios_backup(udid: str):
    proc = None
    try:
        if not which('idevicebackup2'):
            set_progress(udid, 'backup', 100, 'idevicebackup2 no instalado', 'error')
            return
        root = backup_root()
        dest = os.path.join(root, udid)
        os.makedirs(dest, exist_ok=True)
        set_progress(udid, 'backup', 5, 'Iniciando backup iOS')
        set_progress(udid, 'backup', 15, 'Esperando validación en el dispositivo')
        set_progress(udid, 'backup', 30, 'Solicitando respaldo al dispositivo')
        proc = subprocess.Popen(['idevicebackup2', 'backup', '--full', dest, '-u', udid], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        IOS_PROCS[udid] = proc
        stdout, stderr = proc.communicate(timeout=7200)
        code = proc.returncode
        if code != 0:
            if IOS_PROGRESS.get(udid, {}).get('status') == 'cancelled':
                return
            set_progress(udid, 'backup', 100, stderr or stdout or 'backup failed', 'error', {'code': code})
            return
        set_progress(udid, 'backup', 85, 'Verificando archivos principales')
        info_path = os.path.join(dest, 'Info.plist')
        manifest_db = os.path.join(dest, 'Manifest.db')
        manifest_plist = os.path.join(dest, 'Manifest.plist')
        status_plist = os.path.join(dest, 'Status.plist')
        files = []
        for x in [info_path, manifest_db, manifest_plist, status_plist]:
            if os.path.exists(x): files.append(os.path.basename(x))
        set_progress(udid, 'backup', 100, 'Backup iOS completado', 'done', {'core_files': files, 'backup_dir': dest})
    except Exception as e:
        if IOS_PROGRESS.get(udid, {}).get('status') != 'cancelled':
            set_progress(udid, 'backup', 100, str(e), 'error')
    finally:
        IOS_PROCS.pop(udid, None)


@router.post('/cancel/{udid}')
def cancel_ios_backup(udid: str):
    proc = IOS_PROCS.get(udid)
    if not proc or proc.poll() is not None:
        return {'ok': False, 'message': 'No hay backup iOS en ejecución'}
    terminate_proc(proc)
    set_progress(udid, 'backup', IOS_PROGRESS.get(udid, {}).get('percent', 0), 'Backup iOS cancelado por el usuario', 'cancelled')
    IOS_PROCS.pop(udid, None)
    return {'ok': True, 'message': 'Backup iOS cancelado'}


@router.get('/progress/{udid}')
def progress(udid: str):
    return IOS_PROGRESS.get(udid, {'udid': udid, 'status': 'idle', 'percent': 0, 'stage': 'Sin ejecución'})


@router.get('/status')
def status():
    tools = {'idevice_id': which('idevice_id'),'ideviceinfo': which('ideviceinfo'),'idevicepair': which('idevicepair'),'idevicebackup2': which('idevicebackup2'),'ifuse': which('ifuse')}
    enabled = all(tools.values())
    return {'enabled': enabled, 'tools': tools, 'message': 'iOS tools ready' if enabled else 'Missing iOS tools in container/host'}


@router.get('/devices')
def devices():
    if not which('idevice_id'):
        return {'ok': False, 'error': 'idevice_id not installed', 'devices': [], 'count': 0}
    out, err, code = run_cmd('idevice_id', '-l', timeout=20)
    if code != 0:
        return {'ok': False, 'error': err or out or 'idevice_id failed', 'devices': [], 'count': 0, 'code': code}
    devs = [l.strip() for l in out.splitlines() if l.strip()]
    if not devs:
        return {'ok': False, 'error': 'No iOS devices detected. Connect USB and trust the computer.', 'devices': [], 'count': 0}
    return {'ok': True, 'devices': devs, 'count': len(devs)}


@router.get('/info/{udid}')
def info(udid: str):
    if not which('ideviceinfo'):
        raise HTTPException(500, 'ideviceinfo not installed')
    out, err, code = run_cmd('ideviceinfo', '-u', udid, timeout=30)
    if code != 0 and not out:
        raise HTTPException(500, err or 'ideviceinfo failed')
    info = {}
    for line in out.splitlines():
        if ': ' in line:
            k, v = line.split(': ', 1)
            info[k.strip()] = v.strip()
    return {'udid': udid, 'info': info}


@router.post('/pair/{udid}')
def pair(udid: str):
    if not which('idevicepair'):
        raise HTTPException(500, 'idevicepair not installed')
    out, err, code = run_cmd('idevicepair', 'pair', '-u', udid, timeout=60)
    return {'udid': udid, 'stdout': out, 'stderr': err, 'code': code, 'ok': code == 0}


@router.post('/backup/{udid}')
def backup(udid: str):
    threading.Thread(target=run_ios_backup, args=(udid,), daemon=True).start()
    return {'ok': True, 'started': True, 'udid': udid, 'mode': 'full'}


@router.post('/backup/selective/{udid}')
def backup_selective(udid: str, category: str = 'photos', domain: str = '', extensions: str = ''):
    backup_path, created = ensure_backup(udid)
    category = (category or 'photos').lower().strip()
    rows = []
    set_progress(udid, 'selective', 5, f'Preparando exportación {category}')
    if category == 'photos':
        rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%.jpg' OR lower(relativePath) LIKE '%.jpeg' OR lower(relativePath) LIKE '%.png' OR lower(relativePath) LIKE '%.heic' OR lower(relativePath) LIKE '%.heif' OR lower(relativePath) LIKE '%.gif'")
    elif category == 'messages':
        rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%sms.db%' OR lower(relativePath) LIKE '%sms.db-wal%' OR lower(relativePath) LIKE '%sms.db-shm%' OR lower(relativePath) LIKE '%attachments/%'")
    elif category == 'sqlite':
        rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%.db' OR lower(relativePath) LIKE '%.sqlite' OR lower(relativePath) LIKE '%.sqlite3' OR lower(relativePath) LIKE '%.db-wal' OR lower(relativePath) LIKE '%.db-shm'")
    elif category == 'plist':
        rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%.plist'")
    elif category == 'domain' and domain:
        rows = manifest_rows(backup_path, 'domain = ?', (domain,))
    elif category == 'extensions' and extensions:
        exts = [e.strip().lower() for e in extensions.split(',') if e.strip()]
        clauses = []
        params = []
        for e in exts:
            if not e.startswith('.'): e = '.' + e
            clauses.append('lower(relativePath) LIKE ?')
            params.append('%' + e)
        rows = manifest_rows(backup_path, ' OR '.join(clauses), tuple(params)) if clauses else []
    else:
        raise HTTPException(400, 'Unsupported category. Use photos, messages, sqlite, plist, domain, extensions')
    export_name = f'{udid}_{safe_name(category)}_{safe_name(domain or extensions or "all")}'
    target_dir, zip_path, exported = export_rows(backup_path, rows, export_name, udid)
    set_progress(udid, 'selective', 100, f'Exportación {category} completada', 'done', {'zip_path': zip_path, 'count': len(exported)})
    return {'ok': True, 'backup_path': backup_path, 'backup_created_now': created, 'category': category, 'domain': domain, 'extensions': extensions,'export_dir': target_dir, 'zip_path': zip_path, 'count': len(exported), 'items': exported[:200]}


@router.get('/export/list')
def export_list():
    root = export_root()
    items = []
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            items.append({'name': name, 'path': p, 'zip_path': p + '.zip', 'has_zip': os.path.exists(p + '.zip')})
    return {'exports': items}


@router.get('/backup/list')
def backup_list():
    root = backup_root()
    items = []
    for name in os.listdir(root):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            items.append({'name': name, 'path': p, 'has_info_plist': os.path.exists(os.path.join(p, 'Info.plist')), 'has_manifest_db': os.path.exists(os.path.join(p, 'Manifest.db')), 'has_manifest_plist': os.path.exists(os.path.join(p, 'Manifest.plist')), 'has_status_plist': os.path.exists(os.path.join(p, 'Status.plist'))})
    return {'backups': items}


@router.get('/manifest')
def manifest(backup_path: str):
    rows = manifest_rows(backup_path)
    return {'count': len(rows), 'items': rows[:500]}


@router.get('/photos')
def photos(backup_path: str):
    rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%.jpg' OR lower(relativePath) LIKE '%.jpeg' OR lower(relativePath) LIKE '%.png' OR lower(relativePath) LIKE '%.heic' OR lower(relativePath) LIKE '%.heif' LIMIT 500")
    return {'items': rows}


@router.get('/messages')
def messages(backup_path: str):
    rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%sms.db%' OR lower(relativePath) LIKE '%attachments/%'")
    return {'items': rows}


@router.get('/sqlite')
def sqlite(backup_path: str):
    rows = manifest_rows(backup_path, "lower(relativePath) LIKE '%.db' OR lower(relativePath) LIKE '%.sqlite' OR lower(relativePath) LIKE '%.sqlite3'")
    return {'items': rows}


@router.get('/plist')
def plist(backup_path: str):
    info_path = os.path.join(backup_path, 'Info.plist')
    if not os.path.exists(info_path):
        raise HTTPException(404, 'Info.plist not found')
    with open(info_path, 'rb') as f:
        data = plistlib.load(f)
    return data
