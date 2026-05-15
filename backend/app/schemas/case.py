from pydantic import BaseModel

class CaseCreate(BaseModel):
    name: str
    investigator: str = ''
    description: str = ''
    status: str = 'open'

class CaseAssign(BaseModel):
    case_id: int


class PericialReportCreate(BaseModel):
    case_id: int
    title: str = 'Reporte pericial'
    expert_name: str = ''
    expert_alias: str = ''
    requested_by: str = ''
    objective: str = ''
    methodology: str = 'Análisis técnico-forense sobre los artefactos recolectados por la herramienta.'
    conclusions: str = ''
    device_type: str = 'android'
    scan_ids: list[int] = []
