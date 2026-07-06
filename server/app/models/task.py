from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    target_device_ids = Column(JSON)  # [1, 2, 3] or ["all"]
    config = Column(JSON)  # {"duration": 3600, "sample_rate": 16000}
    status = Column(
        Enum("pending", "dispatched", "running", "completed", "failed", name="task_status"),
        default="pending",
    )
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())
