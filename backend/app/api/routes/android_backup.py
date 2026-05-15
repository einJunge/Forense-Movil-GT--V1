import os, subprocess, zipfile, json, threading, time
from fastapi import APIRouter, HTTPException

router = APIRouter()
BACKUP_PROGRESS = {}
BACKUP_PROCS = {}


def adb(serial, *args, timeout=120):
    r = subprocess.run(['adb', '-s', serial] + list(args), capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def backup_root():
    root = os.path.join(os.getcwd(), 'output', 'android_backups')
    os.makedirs(root, exist_ok=True)
    return root


def safe_name(x: str):
    return ''.join(c if c.isalnum() or c in '._-' else '_' for c in (x or 'item'))


def device_dir(serial: str):
    p = os.path.join(backup_root(), safe_name(serial))
    os.makedirs(p, exist_ok=True)
    return p


def zip_dir(path: str):
    zip_path = path + '.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(path):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, path))
    return zip_path


def shell_ok(serial: str, cmd: str):
    out, err, code = adb(serial, 'shell', cmd, timeout=60)
    return out, err, code


def set_progress(serial, mode, percent, stage, status='running', extra=None):
    BACKUP_PROGRESS[serial] = {'serial': serial, 'mode': mode, 'percent': int(percent), 'stage': stage, 'status': status, 'updated_at': time.time(), **(extra or {})}


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


def adb_pull(serial: str, remote: str, local: str):
    os.makedirs(os.path.dirname(local), exist_ok=True)
    proc = subprocess.Popen(['adb', '-s', serial, 'pull', remote, local], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    BACKUP_PROCS[serial] = proc
    stdout, stderr = proc.communicate(timeout=1800)
    code = proc.returncode
    return {'stdout': stdout.strip(), 'stderr': stderr.strip(), 'code': code, 'ok': code == 0}


def run_basic(serial: str):
    try:
        set_progress(serial, 'basic', 1, 'Iniciando backup básico')
        target = os.path.join(device_dir(serial), 'basic')
        os.makedirs(target, exist_ok=True)
        sources = ['/sdcard/DCIM', '/sdcard/Pictures', '/sdcard/Movies', '/sdcard/Download', '/sdcard/Documents', '/sdcard/WhatsApp', '/sdcard/Android/media']
        results = []
        total = len(sources) + 2
        step = 0
        for src in sources:
            step += 1
            set_progress(serial, 'basic', int((step / total) * 100), f'Extrayendo {src}')
            name = src.strip('/').replace('/', '__')
            results.append({'source': src, **adb_pull(serial, src, os.path.join(target, name))})
            if BACKUP_PROGRESS.get(serial, {}).get('status') == 'cancelled':
                return
        step += 1
        set_progress(serial, 'basic', int((step / total) * 100), 'Guardando lista de paquetes')
        pkg_out, _, _ = adb(serial, 'shell', 'pm', 'list', 'packages', '-3', timeout=120)
        with open(os.path.join(target, 'packages.txt'), 'w', encoding='utf-8') as f:
            f.write(pkg_out or '')
        with open(os.path.join(target, '_meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'mode': 'basic', 'serial': serial, 'results': results}, f, indent=2, ensure_ascii=False)
        set_progress(serial, 'basic', 95, 'Comprimiendo respaldo')
        zip_path = zip_dir(target)
        set_progress(serial, 'basic', 100, 'Backup básico completado', 'done', {'zip_path': zip_path, 'target_dir': target})
    except Exception as e:
        if BACKUP_PROGRESS.get(serial, {}).get('status') != 'cancelled':
            set_progress(serial, 'basic', 100, f'Error: {e}', 'error')
    finally:
        BACKUP_PROCS.pop(serial, None)


def run_advanced(serial: str):
    try:
        su_out, su_err, su_code = shell_ok(serial, 'su -c id')
        if not (su_code == 0 and 'uid=0' in (su_out or '')):
            set_progress(serial, 'advanced', 100, 'Root no disponible', 'error', {'error': 'Root no disponible. Usa backup básico.'})
            return
        set_progress(serial, 'advanced', 1, 'Iniciando backup avanzado root')
        target = os.path.join(device_dir(serial), 'advanced')
        os.makedirs(target, exist_ok=True)
        commands = [('packages_full.txt', 'su -c pm list packages -f -3'),('accounts.txt', 'su -c dumpsys account'),('wifi.txt', 'su -c cat /data/misc/wifi/WifiConfigStore.xml'),('settings_secure.txt', 'su -c settings list secure'),('settings_global.txt', 'su -c settings list global'),('settings_system.txt', 'su -c settings list system')]
        pulls = ['/data/data', '/data/system/users/0', '/sdcard']
        total = len(commands) + len(pulls) + 1
        step = 0
        collected = []
        for fn, cmd in commands:
            step += 1
            set_progress(serial, 'advanced', int((step / total) * 100), f'Recolectando {fn}')
            out, err, code = shell_ok(serial, cmd)
            with open(os.path.join(target, fn), 'w', encoding='utf-8') as f:
                f.write(out or err or '')
            collected.append({'file': fn, 'command': cmd, 'code': code})
            if BACKUP_PROGRESS.get(serial, {}).get('status') == 'cancelled':
                return
        pull_results = []
        for src in pulls:
            step += 1
            set_progress(serial, 'advanced', int((step / total) * 100), f'Extrayendo {src}')
            name = src.strip('/').replace('/', '__')
            pull_results.append({'source': src, **adb_pull(serial, src, os.path.join(target, name))})
            if BACKUP_PROGRESS.get(serial, {}).get('status') == 'cancelled':
                return
        with open(os.path.join(target, '_meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'mode': 'advanced', 'serial': serial, 'collected': collected, 'pulls': pull_results}, f, indent=2, ensure_ascii=False)
        set_progress(serial, 'advanced', 95, 'Comprimiendo respaldo avanzado')
        zip_path = zip_dir(target)
        set_progress(serial, 'advanced', 100, 'Backup avanzado completado', 'done', {'zip_path': zip_path, 'target_dir': target})
    except Exception as e:
        if BACKUP_PROGRESS.get(serial, {}).get('status') != 'cancelled':
            set_progress(serial, 'advanced', 100, f'Error: {e}', 'error')
    finally:
        BACKUP_PROCS.pop(serial, None)


@router.post('/cancel/{serial}')
def android_backup_cancel(serial: str):
    proc = BACKUP_PROCS.get(serial)
    if not proc or proc.poll() is not None:
        return {'ok': False, 'message': 'No hay backup Android en ejecución'}
    terminate_proc(proc)
    set_progress(serial, BACKUP_PROGRESS.get(serial, {}).get('mode', 'basic'), BACKUP_PROGRESS.get(serial, {}).get('percent', 0), 'Backup Android cancelado por el usuario', 'cancelled')
    BACKUP_PROCS.pop(serial, None)
    return {'ok': True, 'message': 'Backup Android cancelado'}


@router.get('/status/{serial}')
def android_backup_status(serial: str):
    out, err, code = adb(serial, 'get-state', timeout=20)
    if code != 0:
        raise HTTPException(500, err or out or 'adb failed')
    su_out, su_err, su_code = shell_ok(serial, 'su -c id')
    root_enabled = su_code == 0 and 'uid=0' in (su_out or '')
    return {'serial': serial, 'adb_state': out or 'unknown', 'root_available': root_enabled, 'su_stdout': su_out, 'su_stderr': su_err, 'safe_mode': not root_enabled, 'backup_root': device_dir(serial), 'progress': BACKUP_PROGRESS.get(serial)}


@router.get('/progress/{serial}')
def android_backup_progress(serial: str):
    return BACKUP_PROGRESS.get(serial, {'serial': serial, 'status': 'idle', 'percent': 0, 'stage': 'Sin ejecución'})


@router.post('/basic/{serial}')
def android_backup_basic(serial: str):
    threading.Thread(target=run_basic, args=(serial,), daemon=True).start()
    return {'ok': True, 'started': True, 'mode': 'basic', 'serial': serial}


@router.post('/advanced/{serial}')
def android_backup_advanced(serial: str):
    threading.Thread(target=run_advanced, args=(serial,), daemon=True).start()
    return {'ok': True, 'started': True, 'mode': 'advanced', 'serial': serial}


@router.get('/list')
def android_backup_list():
    root = backup_root()
    items = []
    for serial in os.listdir(root):
        p = os.path.join(root, serial)
        if os.path.isdir(p):
            items.append({'serial': serial, 'path': p, 'has_basic': os.path.isdir(os.path.join(p, 'basic')), 'has_advanced': os.path.isdir(os.path.join(p, 'advanced'))})
    return {'items': items}
