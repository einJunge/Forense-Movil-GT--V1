from pydantic import BaseModel, ConfigDict
class DeviceCreate(BaseModel):
    adb_serial: str
    model: str = 'Unknown'
    manufacturer: str = 'Unknown'
    android_version: str = 'Unknown'
    sdk_version: str = 'Unknown'
    root_status: bool = False
    connect_type: str = 'usb'
class DeviceOut(DeviceCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
