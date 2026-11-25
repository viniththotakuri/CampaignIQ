"""
Workload Distribution & Calling Queue Service for CampaignIQ
PS-8 Banking Call Center Intelligence System

Implements:
1. Smart Workload Distribution: Fairly distributes prioritized customers
   across active calling agents based on capacity and priority (High first).
2. Assignment Preview: Allows Team Leader to preview allocation before committing.
3. Agent Queue & "Smart Next Call" recommendation algorithm.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, select

from models import User, Customer, Campaign, Prediction, Assignment, CallLog, FollowUp, utc_now


def preview_workload_distribution(
    campaign_id: int,
    db: Session,
    agent_ids: Optional[List[int]] = None,
    max_per_agent: Optional[int] = None
) -> Dict[str, Any]:
    """
    Simulates assignment distribution without committing changes to the database.
    Shows the Team Leader how many High, Medium, and Low priority customers each agent will get.
    """
    campaign = db.query(Campaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found.")

    # Get target agents
    if agent_ids:
        agents = db.query(User).filter(User.id.in_(agent_ids), User.is_active == True).all()
    else:
        agents = db.query(User).filter_by(role="agent", is_active=True).all()

    if not agents:
        raise ValueError("No active calling agents available for assignment.")

    # Find unassigned prioritized customers for this campaign
    assigned_select = (
        select(Assignment.customer_id)
        .filter_by(campaign_id=campaign_id)
    )

    unassigned_predictions = (
        db.query(Prediction, Customer)
        .join(Customer, Prediction.customer_id == Customer.id)
        .filter(
            Prediction.campaign_id == campaign_id,
            ~Prediction.customer_id.in_(assigned_select)
        )
        .order_by(desc(Prediction.subscription_probability))
        .all()
    )

    total_available = len(unassigned_predictions)
    num_agents = len(agents)

    # Determine capacity per agent
    if max_per_agent and max_per_agent > 0:
        target_per_agent = max_per_agent
    else:
        target_per_agent = (total_available // num_agents) + (1 if total_available % num_agents > 0 else 0)

    # Simulate distribution: round-robin prioritized customers across agents
    preview_agents: Dict[int, Dict[str, Any]] = {
        agent.id: {
            "agent_id": agent.id,
            "agent_name": agent.full_name,
            "username": agent.username,
            "current_pending_load": db.query(Assignment).filter_by(agent_id=agent.id, status="pending").count(),
            "simulated_total": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0
        }
        for agent in agents
    }

    agent_list = list(preview_agents.keys())
    agent_idx = 0
    assigned_count = 0

    for pred, cust in unassigned_predictions:
        # Check if all agents reached max limit
        if all(preview_agents[aid]["simulated_total"] >= target_per_agent for aid in agent_list):
            break

        # Find next agent who has capacity
        start_idx = agent_idx
        while preview_agents[agent_list[agent_idx]]["simulated_total"] >= target_per_agent:
            agent_idx = (agent_idx + 1) % num_agents
            if agent_idx == start_idx:
                break

        curr_agent_id = agent_list[agent_idx]
        if preview_agents[curr_agent_id]["simulated_total"] < target_per_agent:
            preview_agents[curr_agent_id]["simulated_total"] += 1
            if pred.priority == "High":
                preview_agents[curr_agent_id]["high_priority"] += 1
            elif pred.priority == "Medium":
                preview_agents[curr_agent_id]["medium_priority"] += 1
            else:
                preview_agents[curr_agent_id]["low_priority"] += 1

            assigned_count += 1
            agent_idx = (agent_idx + 1) % num_agents

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_unassigned_available": total_available,
        "total_to_assign": assigned_count,
        "remaining_unassigned": total_available - assigned_count,
        "agent_distributions": list(preview_agents.values())
    }


def execute_workload_distribution(
    campaign_id: int,
    db: Session,
    agent_ids: Optional[List[int]] = None,
    max_per_agent: Optional[int] = None
) -> Dict[str, Any]:
    """
    Commits the workload distribution to the database:
    1. Selects unassigned prioritized customers ordered by probability descending.
    2. Assigns them to agents in balanced round-robin batches.
    3. Creates records in the assignments table.
    """
    campaign = db.query(Campaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found.")

    if agent_ids:
        agents = db.query(User).filter(User.id.in_(agent_ids), User.is_active == True).all()
    else:
        agents = db.query(User).filter_by(role="agent", is_active=True).all()

    if not agents:
        raise ValueError("No active calling agents available for assignment.")

    # Find unassigned predictions
    assigned_select = (
        select(Assignment.customer_id)
        .filter_by(campaign_id=campaign_id)
    )

    unassigned = (
        db.query(Prediction)
        .filter(
            Prediction.campaign_id == campaign_id,
            ~Prediction.customer_id.in_(assigned_select)
        )
        .order_by(desc(Prediction.subscription_probability))
        .all()
    )

    if not unassigned:
        raise ValueError("All prioritized customers for this campaign are already assigned.")

    num_agents = len(agents)
    target_per_agent = max_per_agent if (max_per_agent and max_per_agent > 0) else len(unassigned)

    agent_counts: Dict[int, int] = {agent.id: 0 for agent in agents}
    agent_ids_list = [agent.id for agent in agents]
    agent_idx = 0
    created_assignments = 0

    for pred in unassigned:
        if all(agent_counts[aid] >= target_per_agent for aid in agent_ids_list):
            break

        start_idx = agent_idx
        while agent_counts[agent_ids_list[agent_idx]] >= target_per_agent:
            agent_idx = (agent_idx + 1) % num_agents
            if agent_idx == start_idx:
                break

        chosen_agent_id = agent_ids_list[agent_idx]
        if agent_counts[chosen_agent_id] < target_per_agent:
            assignment = Assignment(
                campaign_id=campaign_id,
                customer_id=pred.customer_id,
                agent_id=chosen_agent_id,
                status="pending",
                priority=pred.priority,
                assigned_at=utc_now()
            )
            db.add(assignment)
            agent_counts[chosen_agent_id] += 1
            created_assignments += 1
            agent_idx = (agent_idx + 1) % num_agents

    db.commit()

    agent_summary = []
    for agent in agents:
        agent_summary.append({
            "agent_id": agent.id,
            "agent_name": agent.full_name,
            "assigned_in_this_run": agent_counts[agent.id],
            "total_pending_queue": db.query(Assignment).filter_by(agent_id=agent.id, status="pending").count()
        })

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "total_assignments_created": created_assignments,
        "agent_summary": agent_summary
    }


def get_agent_calling_queue(
    agent_id: int,
    db: Session,
    status_filter: Optional[str] = "pending"
) -> List[Dict[str, Any]]:
    """
    Returns the agent's personalized calling queue.
    Orders by High Priority first, then by subscription probability descending.
    """
    query = (
        db.query(Assignment, Customer, Prediction)
        .join(Customer, Assignment.customer_id == Customer.id)
        .outerjoin(
            Prediction,
            (Prediction.customer_id == Customer.id) & (Prediction.campaign_id == Assignment.campaign_id)
        )
        .filter(Assignment.agent_id == agent_id)
    )

    if status_filter and status_filter != "all":
        query = query.filter(Assignment.status == status_filter)

    records = query.all()

    # Sort queue: High priority first, then descending probability
    priority_rank = {"High": 1, "Medium": 2, "Low": 3}
    records.sort(
        key=lambda r: (
            priority_rank.get(r[0].priority, 99),
            -(r[2].subscription_probability if r[2] else 0.0)
        )
    )

    output = []
    seen_customers = set()
    for assign, cust, pred in records:
        if cust.id in seen_customers:
            continue
        seen_customers.add(cust.id)

        output.append({
            "queue_position": len(output) + 1,
            "assignment_id": assign.id,
            "campaign_id": assign.campaign_id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "customer_phone": cust.phone,
            "age": cust.age,
            "job": cust.job,
            "marital": cust.marital,
            "education": cust.education,
            "housing_loan": cust.housing,
            "personal_loan": cust.loan,
            "previous_contacts": cust.previous,
            "poutcome": cust.poutcome,
            "priority": assign.priority,
            "status": assign.status,
            "subscription_probability": pred.subscription_probability if pred else None,
            "subscription_percentage": round(pred.subscription_probability * 100, 2) if pred else None,
            "assigned_at": assign.assigned_at.isoformat() if assign.assigned_at else None
        })

    return output


def get_smart_next_recommended_call(agent_id: int, db: Session) -> Optional[Dict[str, Any]]:
    """
    Smart Next Call Recommendation Engine:
    1. Checks if the agent has any pending callbacks scheduled for today or overdue.
    2. If none, selects the highest probability uncontacted customer from their assigned queue.
    """
    now = utc_now()

    # 1. Check for due / overdue follow-up callbacks
    due_followup = (
        db.query(FollowUp, Customer)
        .join(Customer, FollowUp.customer_id == Customer.id)
        .filter(
            FollowUp.agent_id == agent_id,
            FollowUp.status == "pending",
            FollowUp.scheduled_date <= now
        )
        .order_by(FollowUp.scheduled_date.asc())
        .first()
    )

    if due_followup:
        fu, cust = due_followup
        # Locate corresponding assignment
        assignment = (
            db.query(Assignment)
            .filter_by(agent_id=agent_id, customer_id=cust.id)
            .first()
        )
        return {
            "recommendation_reason": "Scheduled Follow-up Due",
            "is_followup": True,
            "followup_id": fu.id,
            "scheduled_time": fu.scheduled_date.isoformat(),
            "followup_notes": fu.notes,
            "assignment_id": assignment.id if assignment else None,
            "campaign_id": fu.campaign_id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "customer_phone": cust.phone,
            "age": cust.age,
            "job": cust.job,
            "education": cust.education,
            "priority": "High",  # Follow-ups are urgent
            "poutcome": cust.poutcome
        }

    # 2. Select top pending assigned customer
    pending_queue = get_agent_calling_queue(agent_id, db, status_filter="pending")
    if pending_queue:
        top_cust = pending_queue[0]
        top_cust["recommendation_reason"] = "Highest ML Propensity in Queue"
        top_cust["is_followup"] = False
        return top_cust

    return None
