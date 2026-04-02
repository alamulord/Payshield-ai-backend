# app/db/models.py — SQLAlchemy ORM models for PayShield
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Text, Boolean,
    ForeignKey, Index, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    """User model with RBAC roles. Indexed on email for O(log n) lookup."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="analyst")  # analyst | admin
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    firebase_uid = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    investigations = relationship("Investigation", back_populates="assigned_analyst")


class Transaction(Base):
    """Transaction model. Indexed on id, timestamp, status for O(log n) lookups."""
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=generate_uuid)
    tx_id = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    merchant_name = Column(String(255), nullable=False)
    merchant_category = Column(String(100), nullable=True)
    merchant_icon = Column(String(50), default="store")
    payment_method = Column(String(50), nullable=False)  # visa, mastercard, paypal, amex
    card_last4 = Column(String(4), nullable=True)
    country = Column(String(5), nullable=False)
    country_name = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    device = Column(String(255), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Risk assessment
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default="low")  # low | medium | high
    risk_factors = Column(Text, nullable=True)  # JSON string of risk factors

    # Status
    status = Column(String(50), default="pending")  # pending | completed | blocked | review | flagged | fraud
    status_color = Column(String(20), default="green")

    # Timestamps
    timestamp = Column(DateTime, default=utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    alerts = relationship("Alert", back_populates="transaction")

    __table_args__ = (
        Index("idx_tx_status_time", "status", "timestamp"),
        Index("idx_tx_risk", "risk_level", "risk_score"),
    )


class Alert(Base):
    """Alert model. Indexed on status, timestamp for queue ordering."""
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String(50), unique=True, nullable=False, index=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)

    # Alert details
    amount = Column(Float, nullable=False)
    merchant = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    username = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    country_code = Column(String(5), nullable=True)

    # Risk
    risk_score = Column(Float, nullable=False)
    triggers = Column(Text, nullable=True)  # JSON array of trigger strings

    # Status & SLA
    status = Column(String(50), default="New")  # New | In Review | Resolved | Dismissed
    sla = Column(String(20), nullable=True)
    sla_color = Column(String(30), default="text-green-500")
    sla_deadline = Column(DateTime, nullable=True)

    # Device / location info
    payment_method = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    device = Column(String(255), nullable=True)
    user_agent = Column(String(512), nullable=True)

    # Resolution
    verdict = Column(String(50), nullable=True)  # fraud | legitimate | inconclusive
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Timestamps
    timestamp = Column(DateTime, default=utcnow, index=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")
    investigation = relationship("Investigation", back_populates="alert", uselist=False)

    __table_args__ = (
        Index("idx_alert_status_time", "status", "timestamp"),
    )


class Investigation(Base):
    """Investigation model for analyst workflows."""
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String(50), unique=True, nullable=False, index=True)
    alert_id = Column(String, ForeignKey("alerts.id"), nullable=True)
    analyst_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Investigation details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), default="medium")  # high | medium | low
    status = Column(String(50), default="open")  # open | in_progress | pending_review | closed
    verdict = Column(String(50), nullable=True)  # fraud_confirmed | false_positive | inconclusive
    notes = Column(Text, nullable=True)
    timeline = Column(Text, nullable=True)  # JSON array of timeline events

    # Timestamps
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="investigation")
    assigned_analyst = relationship("User", back_populates="investigations")


class ModelRegistry(Base):
    """ML Model registry for tracking model versions and performance."""
    __tablename__ = "model_registry"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(100), nullable=False)  # lightgbm | pytorch_anomaly | river_online | ensemble
    description = Column(Text, nullable=True)

    # Performance metrics
    accuracy = Column(Float, nullable=True)
    precision_score = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)

    # Status
    status = Column(String(50), default="training")  # training | deployed | retired | shadow
    is_active = Column(Boolean, default=False)

    # Training info
    training_samples = Column(Integer, nullable=True)
    feature_count = Column(Integer, nullable=True)
    training_duration_sec = Column(Float, nullable=True)
    last_trained_at = Column(DateTime, nullable=True)

    # Drift monitoring
    drift_score = Column(Float, nullable=True)
    last_drift_check = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    deployed_at = Column(DateTime, nullable=True)


class Rule(Base):
    """Decision rules for the rules engine. O(r) rule evaluation."""
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    condition = Column(Text, nullable=False)  # JSON condition object
    action = Column(String(100), nullable=False)  # flag | block | review | allow
    threshold = Column(Float, nullable=True)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    category = Column(String(100), nullable=True)  # velocity | amount | geo | device

    # Stats
    times_triggered = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    """Audit trail for tracking all actions."""
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
