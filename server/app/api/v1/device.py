from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.device import Device

router = APIRouter()


class DeviceCreate(BaseModel):
    device_code: str
    name: Optional[str] = None
    location: Optional[str] = None
    firmware_version: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    device_code: str
    name: Optional[str]
    location: Optional[str]
    firmware_version: Optional[str]
    status: str
    last_heartbeat: Optional[datetime]
    last_upload: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class HeartbeatRequest(BaseModel):
    device_code: str
    status: str = "online"
    firmware_version: Optional[str] = None


@router.post("/register", response_model=DeviceResponse)
async def register_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    existing = db.query(Device).filter(Device.device_code == device.device_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device already registered")

    db_device = Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


@router.post("/heartbeat")
async def device_heartbeat(request: HeartbeatRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_code == request.device_code).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = request.status
    device.last_heartbeat = datetime.utcnow()
    if request.firmware_version:
        device.firmware_version = request.firmware_version
    db.commit()
    return {"status": "ok"}


@router.get("/list", response_model=List[DeviceResponse])
async def list_devices(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(Device)
    if status:
        query = query.filter(Device.status == status)
    return query.offset(skip).limit(limit).all()


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/{device_id}")
async def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"status": "deleted"}
