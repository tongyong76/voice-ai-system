from sqlalchemy import Column, BigInteger, String, Enum, DateTime, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128))
    location = Column(String(256))
    firmware_version = Column(String(32))
    status = Column(Enum("online", "offline", "busy", "error", name="device_status"), default="offline")
    last_heartbeat = Column(DateTime)
    last_upload = Column(DateTime)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
