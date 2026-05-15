from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base, engine
from app.api.routes import health, adb, devices, scans, findings, events, reports, cases
from app.api.routes import forensics
from app.api.routes import ios
from app.api.routes import android_backup
from app.db import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Forense Móvil GT", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"service": "Forense Móvil GT", "status": "running", "version": "2.1.0"}

app.include_router(health.router,    prefix="/health")
app.include_router(adb.router,       prefix="/api/adb")
app.include_router(devices.router,   prefix="/api/devices")
app.include_router(scans.router,     prefix="/api/scans")
app.include_router(findings.router,  prefix="/api/findings")
app.include_router(events.router,    prefix="/api/events")
app.include_router(reports.router,   prefix="/api/reports")
app.include_router(cases.router,     prefix="/api/cases")
app.include_router(forensics.router, prefix="/api/forensics")
app.include_router(android_backup.router, prefix="/api/android/backup")

app.include_router(ios.router, prefix="/api/ios")
