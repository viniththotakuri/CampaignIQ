"""
Campaign & Batch Prediction Service for CampaignIQ
PS-8 Banking Call Center Intelligence System

Orchestrates:
1. Campaign creation and lifecycle management (draft, active, paused, completed)
2. Batch ML scoring of database customers via friend's trained XGBoost pipeline
3. Prioritizing and ranking customers into High, Medium, Low tiers
4. Persisting prediction scores and audit metadata in the relational database
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models import Campaign, Customer, Prediction, User
from ml_engine import batch_score_customers


def create_campaign(
    name: str,
    description: Optional[str],
    target_calls: int,
    created_by: int,
    db: Session
) -> Campaign:
    """
    Creates a new campaign in 'draft' status.
    """
    if not name or not name.strip():
        raise ValueError("Campaign name is required.")

    # Verify user exists
    user = db.query(User).filter_by(id=created_by).first()
    if not user:
        raise ValueError(f"User with ID {created_by} does not exist.")

    campaign = Campaign(
        name=name.strip(),
        description=description.strip() if description else None,
        target_calls=max(1, int(target_calls or 50)),
        status="draft",
        created_by=created_by
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def launch_campaign_with_batch_prioritization(
    campaign_id: int,
    db: Session,
    customer_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main PS-8 intelligence workflow:
    1. Validates campaign.
    2. Fetches eligible customers from the database.
    3. Runs the trained XGBoost model pipeline in batch mode.
    4. Ranks customers by predicted subscription probability.
    5. Saves predictions (probability, High/Medium/Low priority, scenario) in the DB.
    6. Transitions campaign status to 'active'.
    """
    campaign = db.query(Campaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found.")

    # 1. Fetch eligible customer records from the database
    query = db.query(Customer)
    if customer_limit and customer_limit > 0:
        query = query.limit(customer_limit)
    customers: List[Customer] = query.all()

    if not customers:
        raise ValueError("No customers available in the database to prioritize.")

    # 2. Run background ML batch scoring using the XGBoost pipeline
    scored_results = batch_score_customers(customers, campaign_id=campaign_id)

    # 3. Clean any existing predictions for this campaign to allow clean re-scoring
    db.query(Prediction).filter_by(campaign_id=campaign_id).delete()

    # 4. Persist prioritized predictions
    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    total_prob = 0.0

    for item in scored_results:
        pred = Prediction(
            customer_id=item["customer_id"],
            campaign_id=campaign_id,
            model_used=item["model_used"],
            scenario=item["scenario"],
            subscription_probability=item["subscription_probability"],
            priority=item["priority"],
            predicted_outcome=item["predicted_outcome"],
            missing_features_count=item["missing_features_count"]
        )
        db.add(pred)
        priority_counts[item["priority"]] = priority_counts.get(item["priority"], 0) + 1
        total_prob += item["subscription_probability"]

    # 5. Transition campaign status to 'active'
    campaign.status = "active"
    db.commit()
    db.refresh(campaign)

    # 5b. Verify prediction count matches scored eligible customers
    saved_predictions_count = db.query(Prediction).filter_by(campaign_id=campaign_id).count()

    avg_prob = round(total_prob / len(scored_results), 4) if scored_results else 0.0

    # 6. Retrieve top 5 preview records for display
    top_preview = get_campaign_prioritized_customers(campaign_id, db, limit=5)

    return {
        "campaign": campaign.to_dict(),
        "total_eligible_customers": len(customers),
        "total_customers_scored": len(scored_results),
        "saved_predictions_count": saved_predictions_count,
        "priority_breakdown": priority_counts,
        "average_subscription_probability": avg_prob,
        "average_subscription_percentage": round(avg_prob * 100, 2),
        "top_prioritized_preview": top_preview
    }


def get_campaign_prioritized_customers(
    campaign_id: int,
    db: Session,
    priority_filter: Optional[str] = None,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    return_metadata: bool = False
) -> Any:
    """
    Retrieves ranked customers for a campaign, ordered by subscription probability descending.
    Supports both simple limit slicing and server-side pagination (page & page_size).
    """
    import math

    query = (
        db.query(Prediction, Customer)
        .join(Customer, Prediction.customer_id == Customer.id)
        .filter(Prediction.campaign_id == campaign_id)
    )

    if priority_filter and priority_filter in ["High", "Medium", "Low"]:
        query = query.filter(Prediction.priority == priority_filter)

    total_count = query.count()
    query = query.order_by(desc(Prediction.subscription_probability))

    effective_page = max(1, page) if page else 1
    if page_size and page_size > 0:
        query = query.offset((effective_page - 1) * page_size).limit(page_size)
    elif limit and limit > 0:
        query = query.limit(limit)

    records = query.all()

    start_rank = ((effective_page - 1) * (page_size or 0)) + 1 if page else 1
    output = []
    for rank_idx, (pred, cust) in enumerate(records):
        output.append({
            "rank": start_rank + rank_idx,
            "prediction_id": pred.id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "customer_phone": cust.phone,
            "customer_job": cust.job,
            "customer_age": cust.age,
            "subscription_probability": pred.subscription_probability,
            "subscription_percentage": round(pred.subscription_probability * 100, 2),
            "priority": pred.priority,
            "predicted_outcome": pred.predicted_outcome,
            "model_used": pred.model_used,
            "scenario": pred.scenario,
            "missing_features_count": pred.missing_features_count
        })

    if return_metadata:
        effective_page_size = page_size or limit or (total_count if total_count > 0 else 1)
        total_pages = math.ceil(total_count / effective_page_size) if effective_page_size > 0 else 1
        return {
            "total_count": total_count,
            "page": effective_page,
            "page_size": effective_page_size,
            "total_pages": max(1, total_pages),
            "customers": output
        }

    return output
