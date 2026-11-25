"""
Operational Analytics & KPI Service for CampaignIQ
PS-8 Banking Call Center Intelligence System

Calculates live, database-driven metrics for:
1. Team Leader Control Center (KPI cards, agent performance, conversion rates, Needs Attention queue)
2. Calling Agent Workspace (personal metrics, daily progress, recent history)
No fake or hardcoded values; all computed from real relational tables.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models import User, Customer, Campaign, Prediction, Assignment, CallLog, FollowUp, utc_now


def get_team_leader_analytics(db: Session, campaign_id: int = None) -> Dict[str, Any]:
    """
    Computes real-time operational KPIs for the Team Leader Dashboard.
    Supports global view or filtering by campaign.
    """
    now = utc_now()

    # 1. Base query filters
    assign_query = db.query(Assignment)
    call_query = db.query(CallLog)
    pred_query = db.query(Prediction)
    fu_query = db.query(FollowUp)

    if campaign_id:
        assign_query = assign_query.filter(Assignment.campaign_id == campaign_id)
        call_query = call_query.filter(CallLog.campaign_id == campaign_id)
        pred_query = pred_query.filter(Prediction.campaign_id == campaign_id)
        fu_query = fu_query.filter(FollowUp.campaign_id == campaign_id)

    # 2. KPI Metrics
    total_pool = db.query(Customer).count()
    customers_scored = pred_query.count()
    campaign_obj = db.query(Campaign).filter_by(id=campaign_id).first() if campaign_id else None
    target_calls = campaign_obj.target_calls if campaign_obj else 0

    total_customers = customers_scored if campaign_id else total_pool
    total_assigned = assign_query.count()
    calls_completed = call_query.count()
    pending_calls = assign_query.filter(Assignment.status == "pending").count()
    in_progress_calls = assign_query.filter(Assignment.status == "in_progress").count()

    successful_subscriptions = (
        call_query.filter(CallLog.call_outcome == "Subscribed").count()
    )

    conversion_rate = (
        round((successful_subscriptions / calls_completed) * 100, 2)
        if calls_completed > 0 else 0.0
    )

    target_progress = (
        round((calls_completed / target_calls) * 100, 1)
        if target_calls > 0 else 0.0
    )

    # Overdue and pending follow-ups
    pending_followups = fu_query.filter(FollowUp.status == "pending").count()
    overdue_followups = (
        fu_query.filter(
            FollowUp.status == "pending",
            FollowUp.scheduled_date < now
        ).count()
    )

    # High priority remaining uncontacted (strictly scoped by campaign if specified)
    from sqlalchemy import select
    if campaign_id:
        called_cust_ids = select(CallLog.customer_id).filter(CallLog.campaign_id == campaign_id)
    else:
        called_cust_ids = select(CallLog.customer_id)

    high_priority_remaining = (
        pred_query.filter(
            Prediction.priority == "High",
            ~Prediction.customer_id.in_(called_cust_ids)
        ).count()
    )

    # 3. Call Outcome Distribution
    outcome_counts = {}
    valid_outcomes = ["Interested", "Not Interested", "Unreachable", "Follow-up Required", "Subscribed"]
    for outcome in valid_outcomes:
        count = call_query.filter(CallLog.call_outcome == outcome).count()
        outcome_counts[outcome] = count

    # 4. Agent Performance Table (strictly filtered by campaign when specified)
    agents = db.query(User).filter_by(role="agent", is_active=True).all()
    agent_performance = []
    for agent in agents:
        agent_assign_q = db.query(Assignment).filter_by(agent_id=agent.id)
        agent_call_q = db.query(CallLog).filter_by(agent_id=agent.id)
        if campaign_id:
            agent_assign_q = agent_assign_q.filter(Assignment.campaign_id == campaign_id)
            agent_call_q = agent_call_q.filter(CallLog.campaign_id == campaign_id)

        agent_assigned = agent_assign_q.count()
        agent_calls = agent_call_q.count()
        agent_pending = agent_assign_q.filter(Assignment.status == "pending").count()
        agent_subs = agent_call_q.filter(CallLog.call_outcome == "Subscribed").count()
        agent_conv = round((agent_subs / agent_calls) * 100, 2) if agent_calls > 0 else 0.0

        agent_performance.append({
            "agent_id": agent.id,
            "agent_name": agent.full_name,
            "username": agent.username,
            "total_assigned": agent_assigned,
            "calls_completed": agent_calls,
            "pending_queue": agent_pending,
            "successful_subscriptions": agent_subs,
            "conversion_rate": agent_conv
        })

    # 5. Needs Attention Items
    needs_attention = []

    # Check for overdue callbacks
    overdue_records = (
        fu_query.filter(
            FollowUp.status == "pending",
            FollowUp.scheduled_date < now
        ).limit(5).all()
    )
    for rec in overdue_records:
        cust = db.query(Customer).filter_by(id=rec.customer_id).first()
        agent = db.query(User).filter_by(id=rec.agent_id).first()
        needs_attention.append({
            "type": "overdue_followup",
            "severity": "high",
            "message": f"Overdue callback with {cust.name if cust else 'Customer'} assigned to {agent.full_name if agent else 'Agent'}.",
            "due_date": rec.scheduled_date.isoformat(),
            "customer_id": rec.customer_id,
            "agent_id": rec.agent_id
        })

    # Check for unassigned high priority customers
    if total_assigned < total_customers and high_priority_remaining > 0:
        needs_attention.append({
            "type": "unassigned_high_priority",
            "severity": "medium",
            "message": f"{high_priority_remaining} high-priority customers remain unassigned or uncontacted in the active campaign.",
            "count": high_priority_remaining
        })

    # Check for agent workload imbalance (e.g. pending load > 15)
    for a in agent_performance:
        if a["pending_queue"] > 15:
            needs_attention.append({
                "type": "workload_imbalance",
                "severity": "warning",
                "message": f"Agent {a['agent_name']} has an elevated queue of {a['pending_queue']} pending calls.",
                "agent_id": a["agent_id"]
            })

    return {
        "kpis": {
            "total_customers": total_customers,
            "customers_scored": customers_scored,
            "total_pool": total_pool,
            "total_assigned": total_assigned,
            "calls_completed": calls_completed,
            "target_calls": target_calls,
            "target_progress": target_progress,
            "pending_calls": pending_calls,
            "in_progress_calls": in_progress_calls,
            "successful_subscriptions": successful_subscriptions,
            "conversion_rate": conversion_rate,
            "pending_followups": pending_followups,
            "overdue_followups": overdue_followups,
            "high_priority_remaining": high_priority_remaining
        },
        "outcome_distribution": outcome_counts,
        "agent_performance": agent_performance,
        "needs_attention": needs_attention
    }


def get_agent_personal_analytics(agent_id: int, db: Session) -> Dict[str, Any]:
    """
    Computes personal metrics and calling history for a Calling Agent.
    """
    total_assigned = db.query(Assignment).filter_by(agent_id=agent_id).count()
    pending_queue = db.query(Assignment).filter_by(agent_id=agent_id, status="pending").count()
    in_progress = db.query(Assignment).filter_by(agent_id=agent_id, status="in_progress").count()
    calls_completed = db.query(CallLog).filter_by(agent_id=agent_id).count()

    successful_subscriptions = (
        db.query(CallLog)
        .filter_by(agent_id=agent_id, call_outcome="Subscribed")
        .count()
    )

    conversion_rate = (
        round((successful_subscriptions / calls_completed) * 100, 2)
        if calls_completed > 0 else 0.0
    )

    followups_due = (
        db.query(FollowUp)
        .filter_by(agent_id=agent_id, status="pending")
        .count()
    )

    # Recent call logs
    recent_logs = (
        db.query(CallLog, Customer)
        .join(Customer, CallLog.customer_id == Customer.id)
        .filter(CallLog.agent_id == agent_id)
        .order_by(desc(CallLog.called_at))
        .limit(10)
        .all()
    )

    history = []
    for log, cust in recent_logs:
        history.append({
            "call_id": log.id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "customer_phone": cust.phone,
            "call_outcome": log.call_outcome,
            "duration_seconds": log.duration_seconds,
            "remarks": log.remarks,
            "called_at": log.called_at.isoformat() if log.called_at else None
        })

    return {
        "personal_kpis": {
            "total_assigned": total_assigned,
            "pending_queue": pending_queue,
            "in_progress": in_progress,
            "calls_completed": calls_completed,
            "successful_subscriptions": successful_subscriptions,
            "conversion_rate": conversion_rate,
            "followups_due": followups_due
        },
        "recent_call_history": history
    }
