<div align="center">

```
███████╗ ██████╗ ██████╗ ███████╗███╗   ██╗███████╗███████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝██╔════╝
█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║███████╗█████╗  
██╔══╝  ██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║╚════██║██╔══╝  
██║     ╚██████╔╝██║  ██║███████╗██║ ╚████║███████║███████╗
╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝

███╗   ███╗ ██████╗ ██╗   ██╗██╗██╗      ██████╗ ████████╗
████╗ ████║██╔═══██╗██║   ██║██║██║     ██╔════╝ ╚══██╔══╝
██╔████╔██║██║   ██║██║   ██║██║██║     ██║  ███╗   ██║   
██║╚██╔╝██║██║   ██║╚██╗ ██╔╝██║██║     ██║   ██║   ██║   
██║ ╚═╝ ██║╚██████╔╝ ╚████╔╝ ██║███████╗╚██████╔╝   ██║   
╚═╝     ╚═╝ ╚═════╝   ╚═══╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝   
```

# Forense Móvil GT

**Herramienta profesional de análisis forense para dispositivos Android e iOS**

[![Version](https://img.shields.io/badge/versión-V1-blue?style=for-the-badge)](https://github.com/hackingsegurgt/forense-movil-gt)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React-61DAFB?style=for-the-badge&logo=react)](https://react.dev/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?style=for-the-badge&logo=docker)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/licencia-privada-red?style=for-the-badge)](LICENSE)

*Desarrollado por **Marcos Hernández** · "Der Designer" — Hacking Seguro GT*

</div>

---

## 📋 Descripción

**Forense Móvil GT** es una herramienta de análisis forense orientada a investigadores de seguridad, peritos digitales y analistas que necesitan documentar, analizar y exportar evidencia de dispositivos móviles Android e iOS de forma estructurada y reproducible.

Toda la investigación se organiza en torno a un **expediente (caso)**, asegurando que cada análisis, hallazgo, backup y reporte quede aislado y asociado a su expediente correspondiente.

---

## ✨ Funcionalidades V1

### 🗂️ Gestión de Casos
- Creación de expedientes con nombre, investigador, descripción y estado
- Carpeta física del caso generada automáticamente en `/var/cases/{CASO}/`
- Subcarpetas organizadas: `evidencia/`, `reportes/`, `notas/`
- Acceso obligatorio al caso antes de iniciar cualquier análisis
- Datos aislados por caso: cada expediente muestra únicamente su propia información

### 🤖 Análisis Android
- Detección de dispositivos por USB y WiFi (ADB)
- Escaneo forense completo del dispositivo
- Análisis de permisos de aplicaciones
- Listado y análisis de aplicaciones instaladas
- Análisis de puertos abiertos y conexiones activas
- Shell interactivo ADB
- Backup completo y selectivo del dispositivo
- Historial de escaneos filtrado por caso activo

### 🍎 Análisis iOS
- Detección de dispositivos iOS conectados
- Pairing y backup completo del dispositivo
- Backup selectivo por categoría
- Extracción de fotos
- Extracción de mensajes
- Inspección de bases de datos SQLite
- Lectura de archivos `.plist`
- Estado y diagnóstico del módulo iOS

### 📑 Reportes Periciales
- Generación de reporte con un solo clic al finalizar el análisis
- El reporte consolida automáticamente:
  - Datos del caso (nombre, investigador, descripción)
  - Datos del analista y marca
  - Dispositivos analizados
  - Hallazgos y artefactos recolectados
  - Línea de tiempo de eventos
  - Hash SHA-256 para trazabilidad del informe
- Exportación en **PDF** y **JSON**
- Guardado automático dentro de la carpeta `reportes/` del caso activo
- Acceso directo al último PDF generado

---

## 🏗️ Arquitectura

```
forense-movil-gt/
├── backend/                    # API FastAPI (Python)
│   └── app/
│       ├── api/routes/         # Rutas: adb, casos, scans, reportes, iOS, Android
│       ├── db/                 # Modelos SQLAlchemy (Device, Scan, Finding, Event, Case)
│       ├── services/           # Lógica de negocio y generación de reportes
│       └── main.py             # Punto de entrada FastAPI
├── frontend/                   # Interfaz React (Vite)
│   └── src/
│       ├── App.jsx             # Flujo principal: gestión de casos + navegación
│       ├── AndroidApp.jsx      # Panel Android completo
│       ├── iOSPanel.jsx        # Panel iOS completo
│       ├── ShellTab.jsx        # Terminal ADB interactiva
│       └── PortsTab.jsx        # Análisis de puertos
├── docker-compose.yml          # Orquestación de servicios
└── README.md
```

### Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 + FastAPI + Uvicorn |
| Base de datos | PostgreSQL 15 |
| Frontend | React 18 + Vite |
| Contenedores | Docker + Docker Compose |
| Generación PDF | ReportLab |
| Análisis Android | ADB (Android Debug Bridge) |
| Análisis iOS | libimobiledevice + idevicebackup2 |

---

## 🚀 Instalación y uso

### Requisitos previos

#### Opción 1: Con Docker
- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/) v2+
- ADB instalado en el sistema host (para análisis Android)
- libimobiledevice instalado (para análisis iOS)

## Levantar sin Docker

Si prefieres ejecutar el proyecto directamente en tu máquina, también puedes hacerlo sin Docker.

### Requisitos
- Python 3.11 o superior.
- Node.js 18 o superior.
- PostgreSQL 15 instalado y corriendo localmente.
- ADB instalado en el sistema host para análisis Android.
- libimobiledevice instalado para análisis iOS.

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Ajusta las variables de conexión a PostgreSQL local

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Acceso
- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

### Levantar la herramienta con Docker

```bash
# 1. Clonar el repositorio
git clone https://github.com/hackingsegurgt/forense-movil-gt.git
cd forense-movil-gt

# 2. Levantar todos los servicios
docker compose up -d --build

# 3. Acceder a la interfaz
# Abrir navegador en: http://localhost:3000
```

### Levantar la herramienta sin Docker

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Ajusta las variables de conexión a PostgreSQL local

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

#### Acceso

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Detener la herramienta

```bash
docker compose down
```

### Ver logs en tiempo real

```bash
docker compose logs -f
```

---

## 🤝 Apoyo y redes

<div align="center">

<a href="https://www.paypal.com/donate/?business=sorayav1616%40gmail.com&no_recurring=0&currency_code=USD" target="_blank" rel="noreferrer">
  <img src="https://img.shields.io/badge/PayPal-Donar-003087?style=for-the-badge&logo=paypal" alt="Donar con PayPal">
</a>

<a href="https://www.facebook.com/hackingseguro502" target="_blank" rel="noreferrer">
  <img src="https://img.shields.io/badge/Facebook-Seguir-1877F2?style=for-the-badge&logo=facebook" alt="Facebook">
</a>

<a href="https://www.linkedin.com/in/marcosh1488" target="_blank" rel="noreferrer">
  <img src="https://img.shields.io/badge/LinkedIn-Conectar-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn">
</a>

</div>

---

## 📁 Volúmenes persistentes

Los siguientes volúmenes Docker garantizan que los datos sobrevivan reinicios:

| Volumen | Ruta en contenedor | Contenido |
|---------|-------------------|-----------|
| `postgres_data` | `/var/lib/postgresql/data` | Base de datos de casos, scans y hallazgos |
| `reports` | `/var/reports` | Reportes individuales por scan |
| `cases` | `/var/cases` | Expedientes completos con subcarpetas |
| `backups` | `/var/backups` | Backups de dispositivos Android e iOS |

---

## 🔄 Flujo de trabajo

```
1. Abrir la herramienta
       ↓
2. Crear o seleccionar un caso
       ↓
3. Elegir plataforma: Android o iOS
       ↓
4. Conectar dispositivo
       ↓
5. Ejecutar análisis (escaneo, permisos, apps, puertos, backup...)
       ↓
6. Al finalizar: presionar "Exportar PDF"
       ↓
7. El reporte se genera con toda la información del caso y el análisis
```

---

## 🌐 API REST

La API está disponible en `http://localhost:8000`. Documentación interactiva en:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/cases` | Listar todos los casos |
| `POST` | `/api/cases` | Crear un caso nuevo |
| `POST` | `/api/cases/assign-scan/{scan_id}` | Asignar scan a un caso |
| `GET` | `/api/adb/discover` | Detectar dispositivos Android |
| `POST` | `/api/scans` | Iniciar escaneo forense |
| `GET` | `/api/scans` | Listar scans |
| `GET` | `/api/findings` | Listar hallazgos |
| `POST` | `/api/reports/cases/{id}/pericial` | Generar reporte pericial |
| `GET` | `/api/reports/cases/{id}/pericial/latest-pdf` | Descargar último PDF del caso |
| `GET` | `/api/ios/devices` | Detectar dispositivos iOS |
| `POST` | `/api/ios/backup/{udid}` | Iniciar backup iOS |

---

## 🖼️ Branding

Coloca los archivos de imagen de la herramienta en:

```
frontend/public/assets/branding/
├── brand-logo.png    ← Logo principal del encabezado (52×52px mínimo)
└── favicon.png       ← Ícono de la pestaña del navegador (32×32px)
```

Si `brand-logo.png` no existe, se mostrará automáticamente el fallback con las siglas **HS**.

---

## 🔒 Consideraciones de seguridad

- Esta herramienta está diseñada para **uso forense y educativo** en entornos controlados.
- No exponer los puertos de la herramienta a redes públicas sin autenticación adicional.
- Los reportes generados pueden contener información sensible del dispositivo analizado.
- Se recomienda operar en un entorno aislado o red local dedicada.

---

## 📌 Versión

| Campo | Valor |
|-------|-------|
| Versión del producto | `V1` |
| Versión del backend | `2.1.0` |
| Estado | Estable |
| Plataformas soportadas | Android, iOS |

---

## 👤 Créditos

**Desarrollado por:** Marcos Hernández  
**Sobrenombre:** *"Der Designer"*  
**Organización:** Hacking Seguro GT  
**Lema:** *Aprende · Practica · Protege*

---

<div align="center">

**Forense Móvil GT V1** — Hacking Seguro GT  
*Aprende · Practica · Protege*

</div>
