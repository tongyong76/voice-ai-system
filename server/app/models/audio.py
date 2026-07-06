from sqlalchemy import Column, BigInteger, String, Integer, Enum, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class AudioRecord(Base):
    __tablename__ = "audio_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(BigInteger, ForeignKey("devices.id"), nullable=False, index=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id"), index=True)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger)
    duration_ms = Column(Integer)
    sample_rate = Column(Integer, default=16000)
    format = Column(String(16), default="opus")
    upload_time = Column(DateTime, server_default=func.now())
    inference_status = Column(
        Enum("pending", "processing", "completed", "failed", name="inference_status"),
        default="pending",
        index=True,
    )
