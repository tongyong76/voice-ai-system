from sqlalchemy import Column, BigInteger, String, Text, Float, Integer, DateTime, JSON, BLOB, Boolean
from sqlalchemy.sql import func
from ..core.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, nullable=False, index=True)
    full_text = Column(Text)
    language = Column(String(16), default="zh")
    segments = Column(JSON)  # [{start, end, text, confidence}]
    created_at = Column(DateTime, server_default=func.now())


class SpeakerRecord(Base):
    __tablename__ = "speaker_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, nullable=False, index=True)
    speaker_label = Column(String(64))
    speaker_id = Column(BigInteger, index=True)
    embedding = Column(BLOB)
    confidence = Column(Float)
    start_ms = Column(Integer)
    end_ms = Column(Integer)


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    tags = Column(JSON)  # ["嫌疑人A", "重点人员"]
    embedding = Column(BLOB)
    created_at = Column(DateTime, server_default=func.now())


class EmotionRecord(Base):
    __tablename__ = "emotion_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, nullable=False, index=True)
    label = Column(String(32))  # positive/negative/neutral/angry/sad
    confidence = Column(Float)
    start_ms = Column(Integer)
    end_ms = Column(Integer)


class NLUResult(Base):
    __tablename__ = "nlu_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    audio_id = Column(BigInteger, nullable=False, index=True)
    keywords = Column(JSON)  # ["关键词1", "关键词2"]
    intent = Column(String(64))
    entities = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    condition_type = Column(String(32))  # keyword/speaker/emotion/custom
    condition_expr = Column(JSON)
    action_type = Column(String(32))  # websocket/sms/email/webhook
    action_target = Column(String(256))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_id = Column(BigInteger)
    audio_id = Column(BigInteger)
    triggered_at = Column(DateTime, server_default=func.now())
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(BigInteger)
