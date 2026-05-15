import subprocess, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

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
    'android.permission.READ_EXTERNAL_STORAGE',
    'android.permission.WRITE_EXTERNAL_STORAGE',
    'android.permission.GET_ACCOUNTS',
    'android.permission.USE_BIOMETRIC',
    'android.permission.MANAGE_EXTERNAL_STORAGE',
]

SUSPICIOUS_PORTS = ['4444','5554','5555','9999','31337','1337','6666','8888','2222']

def adb(serial, *args, timeout=60):
    try:
        r = subprocess.run(['adb','-s',serial]+list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f'ERROR: {e}'

def hex_to_port(hex_str):
    try: return str(int(hex_str, 16))
    except: return ''

def get_uid_to_packages(serial):
    """Mapea UID numérico -> lista de paquetes"""
    raw = adb(serial, 'shell', 'pm', 'list', 'packages', '-U', '-3')
    uid_map = {}
    for line in raw.splitlines():
        # formato: package:com.app  uid:10123
        pkg_match = re.search(r'package:([\S]+)', line)
        uid_match = re.search(r'uid:(\d+)', line)
        if pkg_match and uid_match:
            uid = uid_match.group(1)
            pkg = pkg_match.group(1)
            uid_map.setdefault(uid, []).append(pkg)
    return uid_map

def get_pid_to_info(serial):
    """Mapea PID -> {name, uid} usando ps"""
    ps_out = adb(serial, 'shell', 'ps', '-A', '-o', 'PID,UID,NAME')
    pid_map = {}
    for line in ps_out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3:
            pid_map[parts[0]] = {'uid': parts[1], 'name': parts[2]}
    return pid_map

def find_process_for_port(serial, port_str):
    """
    Busca en /proc/net/tcp y /proc/net/tcp6 el inode del puerto,
    luego lo cruza con /proc/[pid]/fd y ps para identificar app/proceso.
    """
    port_hex = format(int(port_str), '04X')
    results = []

    for proto_file in ['/proc/net/tcp', '/proc/net/tcp6']:
        content = adb(serial, 'shell', f'cat {proto_file} 2>/dev/null')
        if not content or 'ERROR' in content:
            continue
        for line in content.splitlines()[1:]:
            cols = line.split()
            if len(cols) < 10:
                continue
            local_addr = cols[1]
            local_port_hex = local_addr.split(':')[-1]
            local_port = hex_to_port(local_port_hex)
            if local_port == port_str:
                inode = cols[9]
                uid = str(int(cols[7]))
                results.append({'proto': proto_file.split('/')[-1], 'uid': uid, 'inode': inode,
                                 'state': cols[3], 'remote': cols[2]})

    if not results:
        return [{'process': 'No encontrado en /proc/net/tcp', 'package': '', 'uid': ''}]

    uid_to_pkgs = get_uid_to_packages(serial)
    pid_to_info = get_pid_to_info(serial)

    enriched = []
    for entry in results:
        uid = entry['uid']
        inode = entry['inode']

        # buscar PID por inode en /proc/[pid]/fd
        pid_found = ''
        proc_name = ''
        cmd_line = ''
        grep_out = adb(serial, 'shell', f'grep -rl {inode} /proc/*/fd 2>/dev/null | head -3', timeout=15)
        for match in re.findall(r'/proc/(\d+)/fd', grep_out):
            pid_found = match
            info = pid_to_info.get(match, {})
            proc_name = info.get('name','')
            cmd_raw = adb(serial, 'shell', f'cat /proc/{match}/cmdline 2>/dev/null')
            cmd_line = cmd_raw.replace('\x00',' ').strip()
            break

        packages = uid_to_pkgs.get(uid, [])

        enriched.append({
            'proto': entry['proto'],
            'uid': uid,
            'pid': pid_found,
            'process_name': proc_name,
            'cmdline': cmd_line[:200] if cmd_line else '',
            'packages': packages,
            'inode': inode,
        })
    return enriched

# ── 1. PUERTOS ───────────────────────────────────────────────
@router.get("/{serial}/ports")
def get_ports(serial: str):
    ss_out = adb(serial, 'shell', 'ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null')

    suspicious = []
    for sp in SUSPICIOUS_PORTS:
        port_hex = format(int(sp), '04X')
        for proto_file in ['/proc/net/tcp', '/proc/net/tcp6']:
            content = adb(serial, 'shell', f'cat {proto_file} 2>/dev/null')
            if not content or 'ERROR' in content:
                continue
            for line in content.splitlines()[1:]:
                cols = line.split()
                if len(cols) < 10:
                    continue
                local_port = hex_to_port(cols[1].split(':')[-1])
                remote_port = hex_to_port(cols[2].split(':')[-1])
                if local_port == sp or remote_port == sp:
                    proc_info = find_process_for_port(serial, sp)
                    suspicious.append({
                        'port': sp,
                        'protocol': proto_file.split('/')[-1],
                        'reason': f'Puerto {sp} asociado a exploits/backdoors/RAT',
                        'raw_line': line.strip(),
                        'processes': proc_info
                    })
                    break

    # conexiones activas completas
    all_conns_raw = adb(serial, 'shell', 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null')
    connections = []
    for line in (all_conns_raw or '').splitlines()[1:]:
        cols = line.split()
        if len(cols) < 10: continue
        try:
            lport = hex_to_port(cols[1].split(':')[-1])
            rport = hex_to_port(cols[2].split(':')[-1])
            state_map = {'01':'ESTABLISHED','02':'SYN_SENT','06':'TIME_WAIT','0A':'LISTEN','0B':'CLOSING','07':'CLOSE','08':'CLOSE_WAIT','09':'LAST_ACK','04':'FIN_WAIT1','05':'FIN_WAIT2'}
            state = state_map.get(cols[3], cols[3])
            connections.append({'local_port': lport, 'remote_port': rport, 'state': state, 'uid': str(int(cols[7]))})
        except: pass

    return {
        'serial': serial,
        'suspicious_ports': suspicious,
        'all_connections': connections[:100],
        'raw_ss': ss_out[:3000]
    }

# ── 2. PERMISOS ──────────────────────────────────────────────
@router.get("/{serial}/permissions")
def get_permissions(serial: str):
    packages_raw = adb(serial, 'shell', 'pm list packages -3')
    packages = [l.replace('package:','').strip() for l in packages_raw.splitlines() if l.startswith('package:')]
    result = []
    for pkg in packages:
        dumpsys = adb(serial, 'shell', f'dumpsys package {pkg}')
        dangerous = []
        for perm in DANGEROUS_PERMISSIONS:
            if perm in dumpsys:
                idx = dumpsys.find(perm)
                ctx = dumpsys[idx:idx+120]
                granted = 'granted=true' in ctx
                dangerous.append({'permission': perm.split('.')[-1], 'full': perm, 'granted': granted})
        if dangerous:
            result.append({'package': pkg, 'dangerous_permissions': dangerous, 'total': len(dangerous)})
    result.sort(key=lambda x: x['total'], reverse=True)
    return {'serial': serial, 'apps_with_dangerous_permissions': result, 'total_apps': len(result)}

# ── 3. APPS ──────────────────────────────────────────────────
@router.get("/{serial}/apps")
def get_apps(serial: str):
    all_raw   = adb(serial, 'shell', 'pm list packages -f')
    sys_raw   = adb(serial, 'shell', 'pm list packages -s')
    third_raw = adb(serial, 'shell', 'pm list packages -3')
    def parse(raw):
        apps = []
        for l in raw.splitlines():
            if l.startswith('package:'):
                parts = l.replace('package:','').split('=')
                apps.append({'apk_path': parts[0] if len(parts)>1 else '', 'package': parts[-1]})
        return apps
    third = parse(third_raw)
    system_pkgs = set(l.replace('package:','').strip() for l in sys_raw.splitlines())
    enriched = []
    for app in third[:60]:
        ver = ''
        for line in adb(serial, 'shell', f'dumpsys package {app["package"]}', timeout=10).splitlines():
            if 'versionName=' in line:
                ver = line.strip().split('versionName=')[-1].split(' ')[0]; break
        enriched.append({**app, 'version': ver, 'is_system': app['package'] in system_pkgs})
    return {'serial': serial, 'third_party_apps': enriched, 'total_third_party': len(third), 'total_system': len(system_pkgs)}

# ── 4. SHELL ─────────────────────────────────────────────────
class ShellCommand(BaseModel):
    serial: str
    command: str

@router.post("/shell")
def run_shell(body: ShellCommand):
    if not body.command.strip():
        raise HTTPException(400, 'Comando vacío')
    blocked = ['rm -rf /', 'mkfs', 'dd if=', '> /dev/', 'reboot', 'shutdown', 'format c']
    for b in blocked:
        if b in body.command.lower():
            raise HTTPException(403, f'Comando bloqueado: {b}')
    output = adb(body.serial, 'shell', body.command, timeout=30)
    return {'serial': body.serial, 'command': body.command, 'output': output}
