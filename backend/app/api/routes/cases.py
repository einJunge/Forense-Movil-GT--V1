import os, re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Case, Scan
from app.schemas.case import CaseCreate, CaseAssign

router = APIRouter()
BASE_CASES_DIR = '/var/cases'

def slugify(value: str) -> str:
    value = (value or '').strip().upper()
    value = re.sub(r'[^A-Z0-9]+', '-', value)
    value = re.sub(r'-+', '-', value).strip('-')
    return value or 'CASO-SIN-NOMBRE'

def ensure_case_dirs(slug: str):
    case_dir = os.path.join(BASE_CASES_DIR, slug)
    os.makedirs(os.path.join(case_dir, 'evidencia'), exist_ok=True)
    os.makedirs(os.path.join(case_dir, 'reportes'), exist_ok=True)
    os.makedirs(os.path.join(case_dir, 'notas'), exist_ok=True)
    return case_dir

@router.get('')
def list_cases(db: Session = Depends(get_db)):
    return db.query(Case).order_by(Case.created_at.desc()).all()

@router.get('/{case_id}')
def get_case(case_id: int, db: Session = Depends(get_db)):
    c = db.query(Case).filter(Case.id == case_id).first()
    if not c:
        raise HTTPException(404, 'Case not found')
    scans = db.query(Scan).filter(Scan.case_id == case_id).all()
    return {'case': c, 'scans': scans, 'folders': {'root': c.folder_path, 'evidencia': os.path.join(c.folder_path, 'evidencia'), 'reportes': os.path.join(c.folder_path, 'reportes'), 'notas': os.path.join(c.folder_path, 'notas')}}

@router.post('')
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    name = (payload.name or '').strip()
    if not name:
        raise HTTPException(400, 'Case name is required')
    existing = db.query(Case).filter(Case.name == name).first()
    if existing:
        raise HTTPException(409, 'A case with that name already exists')
    slug = slugify(name)
    if db.query(Case).filter(Case.slug == slug).first():
        raise HTTPException(409, 'A case with that slug already exists')
    os.makedirs(BASE_CASES_DIR, exist_ok=True)
    folder = ensure_case_dirs(slug)
    obj = Case(name=name, slug=slug, investigator=payload.investigator or '', description=payload.description or '', status=payload.status or 'open', folder_path=folder)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post('/assign-scan/{scan_id}')
def assign_scan(scan_id: int, payload: CaseAssign, db: Session = Depends(get_db)):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(404, 'Scan not found')
    case = db.query(Case).filter(Case.id == payload.case_id).first()
    if not case:
        raise HTTPException(404, 'Case not found')
    scan.case_id = case.id
    db.commit()
    return {'ok': True, 'scan_id': scan.id, 'case_id': case.id, 'case_name': case.name}
