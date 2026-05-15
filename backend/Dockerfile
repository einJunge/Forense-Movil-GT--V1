FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

# ── Sistema base + herramientas forenses ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # compilación
    gcc g++ make \
    # postgres
    libpq-dev \
    # Android ADB
    android-tools-adb \
    # iOS libimobiledevice
    libimobiledevice-utils \
    ideviceinstaller \
    ifuse \
    usbmuxd \
    libplist-utils \
    # ClamAV (cliente únicamente; el servicio corre en su propio contenedor)
    clamav-daemon \
    # YARA (binario para yara-python)
    libyara-dev \
    yara \
    # utilidades generales
    curl wget git unzip \
    udev \
    && rm -rf /var/lib/apt/lists/*

# ── Python deps ────────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App ────────────────────────────────────────────────────────────────────────
COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
