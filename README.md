# Forense Móvil GT v2.0.0

## Requisitos previos
- adb instalado en el host
- Docker y docker compose instalados

## Ejecución con Docker
```bash
docker compose build
docker compose up
```

## Ejecución local
```bash
# Terminal 1 — Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PWD
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

## Acceso
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Conectar dispositivo USB
1. Activa depuración USB en el celular
2. Conecta el cable USB
3. Acepta el diálogo de autorización en el celular
4. Haz clic en "Actualizar" en la interfaz

## Conectar por WiFi ADB
1. Conecta el celular por USB primero
2. Ejecuta: adb tcpip 5555
3. Desconecta el USB
4. Ingresa la IP del celular en la interfaz y haz clic en "Conectar"
