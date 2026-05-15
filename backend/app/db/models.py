from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from app.db.base import Base

class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    adb_serial = Column(String, unique=True, index=True, nullable=False)
    model = Column(String, default='Unknown')
    manufacturer = Column(String, default='Unknown')
    android_version = Column(String, default='Unknown')
    sdk_version = Column(String, default='Unknown')
    root_status = Column(Boolean, default=False)
    connect_type = Column(String, default='usb')
    created_at = Column(DateTime, default=datetime.utcnow)

class Scan(Base):
    __tablename__ = 'scans'
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=True)
    status = Column(String, default='pending')
    risk_level = Column(String, default='unknown')
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

class Finding(Base):
    __tablename__ = 'findings'
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey('scans.id'), nullable=False)
    category = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    tool = Column(String, nullable=False)
    evidence = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey('scans.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, nullable=False)
    message = Column(Text, default='')

class Artifact(Base):
    __tablename__ = 'artifacts'
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey('scans.id'), nullable=False)
    category = Column(String, nullable=False)
    subcategory = Column(String, default='')
    source_path = Column(String, default='')
    size = Column(Integer, default=0)
    sha256_hash = Column(String, default='')
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)
    investigator = Column(String, nullable=False)
    details = Column(Text, default='')
    hash = Column(String, nullable=False) # Hash de la entrada para integridad

class Case(Base):
    __tablename__ = 'cases'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    investigator = Column(String, default='')
    description = Column(Text, default='')
    status = Column(String, default='open')
    folder_path = Column(String, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
