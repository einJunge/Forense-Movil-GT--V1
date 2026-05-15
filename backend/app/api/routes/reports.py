import os
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Scan, Case, AuditLog
from app.services.report_service import generate_report, generate_pericial_report

router = APIRouter()

@router.post('/scans/{scan_id}/generate')
def generate(scan_id: int, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(404, 'Scan not found')
    return generate_report(db, scan)

@router.get('/scans/{scan_id}/pdf')
def pdf(scan_id: int):
    p = f'/var/reports/scan_{scan_id}.pdf'
    if not os.path.exists(p):
        raise HTTPException(404, 'PDF not found')
    return FileResponse(p, media_type='application/pdf', filename=f'scan_{scan_id}.pdf')

@router.post('/cases/{case_id}/pericial')
def generate_case_pericial(case_id: int, payload: dict = Body(default={}), db: Session = Depends(get_db)):
    case_obj = db.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        raise HTTPException(404, 'Case not found')
    payload['case_id'] = case_id
    try:
        return generate_pericial_report(db, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get('/cases/{case_id}/pericial/latest-pdf')
def latest_case_pdf(case_id: int, db: Session = Depends(get_db)):
    case_obj = db.query(Case).filter(Case.id == case_id).first()
    if not case_obj or not case_obj.folder_path:
        raise HTTPException(404, 'Case not found')
    report_dir = os.path.join(case_obj.folder_path, 'reportes')
    if not os.path.isdir(report_dir):
        raise HTTPException(404, 'No reports found')
    files = sorted([os.path.join(report_dir, f) for f in os.listdir(report_dir) if f.startswith('reporte_pericial_') and f.endswith('.pdf')])
    if not files:
        raise HTTPException(404, 'No reports found')
    latest = files[-1]
    return FileResponse(latest, media_type='application/pdf', filename=os.path.basename(latest))

@router.get('/cases/{case_id}/audit')
def get_case_audit(case_id: int, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.case_id == case_id).order_by(AuditLog.timestamp.desc()).all()
    return logs

@router.get('/cases/latest-pdf')
def latest_case_pdf_any(db: Session = Depends(get_db)):
    files = []
    for case in db.query(Case).all():
        if case.folder_path:
            report_dir = os.path.join(case.folder_path, 'reportes')
            if os.path.isdir(report_dir):
                files.extend([os.path.join(report_dir, f) for f in os.listdir(report_dir) if f.startswith('reporte_pericial_') and f.endswith('.pdf')])
    if not files:
        raise HTTPException(404, 'No reports found')
    latest = sorted(files)[-1]
    return FileResponse(latest, media_type='application/pdf', filename=os.path.basename(latest))
