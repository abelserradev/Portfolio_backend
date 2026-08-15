import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.base import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_state = Column(String(32), nullable=False, default="greeting")
    messages_json = Column(Text, nullable=False, default="[]")
    project_type = Column(String(64), nullable=True)
    scope_summary = Column(Text, nullable=True)
    estimated_range_usd = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class QuoteLead(Base):
    __tablename__ = "quote_leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    project_type = Column(String(64), nullable=False, default="consulta_personalizada")
    scope_summary = Column(Text, nullable=False, default="")
    estimated_range_usd = Column(String(64), nullable=False, default="A consultar")
    client_name = Column(String(200), nullable=True)
    client_email = Column(String(320), nullable=False)
    client_phone = Column(String(32), nullable=True)
    preferred_channel = Column(String(16), nullable=False, default="email")
    status = Column(String(16), nullable=False, default="submitted")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
