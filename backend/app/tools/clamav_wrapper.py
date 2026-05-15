import os
from io import BytesIO
try:
    from clamdpy import ClamdNetworkSocket
except Exception:
    ClamdNetworkSocket = None

CLAMAV_HOST = os.getenv('CLAMAV_HOST', 'localhost')
CLAMAV_PORT = int(os.getenv('CLAMAV_PORT', 3310))

def scan_file_clamav(file_path: str):
    if ClamdNetworkSocket is None:
        return {'result': 'skipped', 'reason': 'clamdpy not installed'}
    try:
        cd = ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT, timeout=15)
        cd.ping()
        with open(file_path, 'rb') as f:
            res = cd.instream(BytesIO(f.read()))
        status = getattr(res, 'status', None) or res.get('stream', 'UNKNOWN')
        if str(status).upper() == 'OK':
            return {'result': 'clean', 'reason': 'No malware detected'}
        return {'result': 'malicious', 'reason': str(status)}
    except Exception as e:
        return {'result': 'error', 'reason': str(e)}
