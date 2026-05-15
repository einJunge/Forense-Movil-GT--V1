from pydantic import BaseModel, ConfigDict
class ScanCreate(BaseModel):
    device_id: int
class ScanOut(ScanCreate):
    id: int
    status: str
    risk_level: str
    model_config = ConfigDict(from_attributes=True)
