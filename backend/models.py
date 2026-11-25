"""
Relational Database Models for CampaignIQ
PS-8 Banking Call Center Intelligence System

Entities:
1. User (Team Leader & Calling Agent)
2. Customer (UCI Bank Marketing features & contact metadata)
3. Campaign (Campaign metadata & operational status)
4. Prediction (Model outputs, probabilities, priority scoring)
5. Assignment (Workload distribution linking Customer to Agent)
6. CallLog (Operational call outcomes, durations, notes)
7. FollowUp (Scheduled follow-ups and resolution status)
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from database import Base


def utc_now():
    """Return current UTC datetime as a naive datetime object for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="agent")  # 'leader' or 'agent'
    email = Column(String(120), unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    campaigns_created = relationship("Campaign", back_populates="creator")
    assignments = relationship("Assignment", back_populates="agent", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="agent")
    followups = relationship("FollowUp", back_populates="agent")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)

    # Demographic features (UCI Bank Marketing)
    age = Column(Integer, nullable=False)
    job = Column(String(50), nullable=False)
    marital = Column(String(30), nullable=False)
    education = Column(String(50), nullable=False)
    default = Column(String(10), nullable=False, default="no")
    housing = Column(String(10), nullable=False, default="no")
    loan = Column(String(10), nullable=False, default="no")

    # Campaign contact features
    contact = Column(String(20), nullable=True)
    month = Column(String(10), nullable=True)
    day_of_week = Column(String(10), nullable=True)
    campaign = Column(Integer, nullable=True, default=1)
    pdays = Column(Integer, nullable=True, default=999)
    previous = Column(Integer, nullable=True, default=0)
    poutcome = Column(String(30), nullable=True, default="nonexistent")

    # Macroeconomic indicators
    emp_var_rate = Column(Float, nullable=True)
    cons_price_idx = Column(Float, nullable=True)
    cons_conf_idx = Column(Float, nullable=True)
    euribor3m = Column(Float, nullable=True)
    nr_employed = Column(Float, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    predictions = relationship("Prediction", back_populates="customer", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="customer", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="customer")
    followups = relationship("FollowUp", back_populates="customer")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "age": self.age,
            "job": self.job,
            "marital": self.marital,
            "education": self.education,
            "default": self.default,
            "housing": self.housing,
            "loan": self.loan,
            "contact": self.contact,
            "month": self.month,
            "day_of_week": self.day_of_week,
            "campaign": self.campaign,
            "pdays": self.pdays,
            "previous": self.previous,
            "poutcome": self.poutcome,
            "emp_var_rate": self.emp_var_rate,
            "cons_price_idx": self.cons_price_idx,
            "cons_conf_idx": self.cons_conf_idx,
            "euribor3m": self.euribor3m,
            "nr_employed": self.nr_employed,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    target_calls = Column(Integer, nullable=False, default=100)
    status = Column(String(20), nullable=False, default="draft")  # 'draft', 'active', 'paused', 'completed'
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="campaigns_created")
    predictions = relationship("Prediction", back_populates="campaign", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="campaign", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="campaign")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_calls": self.target_calls,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    model_used = Column(String(50), nullable=False)  # 'Original XGBoost' or 'Missingness-Aware V2'
    scenario = Column(String(50), nullable=False)    # 'Complete', '10% missing', etc.
    subscription_probability = Column(Float, nullable=False)
    priority = Column(String(20), nullable=False)    # 'High', 'Medium', 'Low'
    predicted_outcome = Column(Integer, nullable=False)  # 1 or 0
    missing_features_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="predictions")
    campaign = relationship("Campaign", back_populates="predictions")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "campaign_id": self.campaign_id,
            "model_used": self.model_used,
            "scenario": self.scenario,
            "subscription_probability": round(self.subscription_probability, 4),
            "subscription_percentage": round(self.subscription_probability * 100, 2),
            "priority": self.priority,
            "predicted_outcome": self.predicted_outcome,
            "missing_features_count": self.missing_features_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'in_progress', 'completed'
    priority = Column(String(20), nullable=False, default="Medium")  # 'High', 'Medium', 'Low'
    assigned_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "customer_id", name="uq_campaign_customer"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="assignments")
    customer = relationship("Customer", back_populates="assignments")
    agent = relationship("User", back_populates="assignments")
    call_logs = relationship("CallLog", back_populates="assignment")

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "priority": self.priority,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    call_outcome = Column(String(50), nullable=False)  # 'Interested', 'Not Interested', 'Unreachable', 'Follow-up Required', 'Subscribed'
    duration_seconds = Column(Integer, default=0, nullable=False)
    remarks = Column(Text, nullable=True)
    called_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    assignment = relationship("Assignment", back_populates="call_logs")
    customer = relationship("Customer", back_populates="call_logs")
    agent = relationship("User", back_populates="call_logs")
    campaign = relationship("Campaign", back_populates="call_logs")
    followup = relationship("FollowUp", back_populates="call_log", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "assignment_id": self.assignment_id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "campaign_id": self.campaign_id,
            "call_outcome": self.call_outcome,
            "duration_seconds": self.duration_seconds,
            "remarks": self.remarks,
            "called_at": self.called_at.isoformat() if self.called_at else None
        }


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    call_log_id = Column(Integer, ForeignKey("call_logs.id"), nullable=True, index=True)
    scheduled_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # 'pending', 'completed', 'overdue', 'cancelled'
    created_at = Column(DateTime, default=utc_now, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="followups")
    agent = relationship("User", back_populates="followups")
    call_log = relationship("CallLog", back_populates="followup")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "agent_id": self.agent_id,
            "campaign_id": self.campaign_id,
            "call_log_id": self.call_log_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }
