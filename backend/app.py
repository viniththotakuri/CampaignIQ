"""
CampaignIQ — Flask Application & API Server
PS-8 Banking Call Center Intelligence System

Central Flask application providing REST APIs for:
- System Health & Diagnostics
- Authentication & Roles
- Campaign Lifecycle & Batch ML Prioritization
- Workload Assignment & Call Queues
- Call Outcome Disposition & Follow-ups
- Real Database Operational Analytics
"""

import os
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS

from database import engine, SessionLocal, init_db
from models import User, Customer, Campaign, Prediction, Assignment, CallLog, FollowUp, utc_now
from ml_engine import (
    original_model,
    original_preprocessor,
    v2_model,
    v2_preprocessor
)
from assignment_service import (
    preview_workload_distribution,
    execute_workload_distribution,
    get_agent_calling_queue,
    get_smart_next_recommended_call
)
from analytics_service import (
    get_team_leader_analytics,
    get_agent_personal_analytics
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path=""
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "campaigniq-ps8-secret-key-2026")
app.config["JSON_SORT_KEYS"] = False

# Enable CORS for cross-origin frontend communication
CORS(app, resources={r"/api/*": {"origins": "*"}})


# --------------------------------------------------
# DATABASE SESSION MANAGEMENT
# --------------------------------------------------

@app.teardown_appcontext
def remove_db_session(exception=None):
    """Closes the scoped database session after each request context."""
    SessionLocal.remove()


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "code": 400,
        "message": getattr(error, "description", "Bad Request")
    }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "code": 404,
        "message": getattr(error, "description", "Resource Not Found")
    }), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "status": "error",
        "code": 500,
        "message": "Internal Server Error"
    }), 500


# --------------------------------------------------
# CORE SYSTEM & HEALTH ENDPOINTS
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serves the CampaignIQ interactive single-page application."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "system": "CampaignIQ — Banking Call Center Intelligence System",
        "version": "1.0.0",
        "stakeholder": "Banking Call Center Team (Team Leader & Calling Agents)",
        "framework": "Flask with SQLAlchemy & XGBoost Intelligence Engine",
        "status": "running"
    })


@app.route("/api", methods=["GET"])
def api_info():
    """Returns system metadata and operational status."""
    return jsonify({
        "system": "CampaignIQ — Banking Call Center Intelligence System",
        "version": "1.0.0",
        "stakeholder": "Banking Call Center Team (Team Leader & Calling Agents)",
        "framework": "Flask with SQLAlchemy & XGBoost Intelligence Engine",
        "status": "running"
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Diagnostic endpoint verifying:
    1. Relational database connectivity and table readiness
    2. ML model artifact loading (Original & V2 XGBoost models + preprocessors)
    """
    db_ok = False
    counts = {}
    db = SessionLocal()
    try:
        counts = {
            "users": db.query(User).count(),
            "customers": db.query(Customer).count(),
            "campaigns": db.query(Campaign).count(),
            "predictions": db.query(Prediction).count(),
            "assignments": db.query(Assignment).count(),
            "call_logs": db.query(CallLog).count(),
            "followups": db.query(FollowUp).count()
        }
        db_ok = True
    except Exception as e:
        counts = {"error": str(e)}
    finally:
        db.close()

    ml_ready = (
        original_model is not None and
        original_preprocessor is not None and
        v2_model is not None and
        v2_preprocessor is not None
    )

    status_code = 200 if (db_ok and ml_ready) else 503

    return jsonify({
        "status": "healthy" if status_code == 200 else "degraded",
        "database": {
            "connected": db_ok,
            "engine": str(engine.url),
            "table_counts": counts
        },
        "ml_intelligence": {
            "ready": ml_ready,
            "original_xgboost_loaded": original_model is not None,
            "original_preprocessor_loaded": original_preprocessor is not None,
            "v2_xgboost_loaded": v2_model is not None,
            "v2_preprocessor_loaded": v2_preprocessor is not None
        }
    }), status_code


# --------------------------------------------------
# CAMPAIGN & BATCH PRIORITIZATION ENDPOINTS
# --------------------------------------------------

from campaign_service import (
    create_campaign,
    launch_campaign_with_batch_prioritization,
    get_campaign_prioritized_customers
)
from ml_engine import predict_single


@app.route("/api/campaigns", methods=["GET"])
def list_campaigns():
    """Returns all campaigns with live database progress, goal completion, and priority counts."""
    db = SessionLocal()
    try:
        campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
        results = []
        for c in campaigns:
            c_dict = c.to_dict()
            c_dict["total_prioritized"] = db.query(Prediction).filter_by(campaign_id=c.id).count()
            c_dict["high_priority_count"] = db.query(Prediction).filter_by(campaign_id=c.id, priority="High").count()
            c_dict["medium_priority_count"] = db.query(Prediction).filter_by(campaign_id=c.id, priority="Medium").count()
            c_dict["low_priority_count"] = db.query(Prediction).filter_by(campaign_id=c.id, priority="Low").count()

            completed_calls = db.query(CallLog).filter_by(campaign_id=c.id).count()
            c_dict["calls_completed"] = completed_calls
            c_dict["target_progress"] = round((completed_calls / c.target_calls) * 100, 1) if c.target_calls > 0 else 0.0

            results.append(c_dict)
        return jsonify({"status": "success", "campaigns": results})
    finally:
        db.close()


@app.route("/api/campaigns", methods=["POST"])
def api_create_campaign():
    """Creates a new campaign in draft status."""
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description", "")
    target_calls = data.get("target_calls", 50)
    created_by = data.get("created_by")

    db = SessionLocal()
    try:
        if not created_by:
            # Default to the first team leader found in the database
            leader = db.query(User).filter_by(role="leader").first()
            if not leader:
                return jsonify({"status": "error", "message": "No team leader found in system."}), 400
            created_by = leader.id

        campaign = create_campaign(
            name=name,
            description=description,
            target_calls=target_calls,
            created_by=created_by,
            db=db
        )
        return jsonify({
            "status": "success",
            "message": "Campaign created successfully in draft mode.",
            "campaign": campaign.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to create campaign: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/campaigns/<int:campaign_id>", methods=["GET"])
def get_campaign_detail(campaign_id):
    """Returns single campaign details along with ML priority distribution."""
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({"status": "error", "message": "Campaign not found"}), 404

        c_dict = campaign.to_dict()
        c_dict["total_prioritized"] = db.query(Prediction).filter_by(campaign_id=campaign_id).count()
        c_dict["high_priority_count"] = db.query(Prediction).filter_by(campaign_id=campaign_id, priority="High").count()
        c_dict["medium_priority_count"] = db.query(Prediction).filter_by(campaign_id=campaign_id, priority="Medium").count()
        c_dict["low_priority_count"] = db.query(Prediction).filter_by(campaign_id=campaign_id, priority="Low").count()

        return jsonify({"status": "success", "campaign": c_dict})
    finally:
        db.close()


@app.route("/api/campaigns/<int:campaign_id>/launch", methods=["POST"])
def api_launch_campaign(campaign_id):
    """
    Launches a campaign:
    1. Fetches eligible customers from DB.
    2. Runs friend's XGBoost model pipeline in batch mode.
    3. Ranks and scores customers with High/Medium/Low priority.
    4. Saves predictions to DB and transitions campaign to 'active'.
    """
    data = request.get_json() or {}
    customer_limit = data.get("customer_limit")

    db = SessionLocal()
    try:
        result = launch_campaign_with_batch_prioritization(
            campaign_id=campaign_id,
            db=db,
            customer_limit=customer_limit
        )
        return jsonify({
            "status": "success",
            "message": "Campaign launched and customers prioritized successfully.",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Launch failed: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/campaigns/<int:campaign_id>/prioritized-customers", methods=["GET"])
def api_campaign_prioritized_customers(campaign_id):
    """
    Returns prioritized calling list for a campaign, ranked by probability descending.
    Query params: ?priority=High, ?limit=20, ?page=1, ?page_size=25
    """
    priority_filter = request.args.get("priority")
    limit = request.args.get("limit", type=int)
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", type=int)

    db = SessionLocal()
    try:
        want_metadata = (page is not None) or (page_size is not None)
        res = get_campaign_prioritized_customers(
            campaign_id=campaign_id,
            db=db,
            priority_filter=priority_filter,
            limit=limit,
            page=page,
            page_size=page_size,
            return_metadata=want_metadata
        )

        if want_metadata:
            return jsonify({
                "status": "success",
                "campaign_id": campaign_id,
                "priority_filter": priority_filter,
                "total_count": res["total_count"],
                "page": res["page"],
                "page_size": res["page_size"],
                "total_pages": res["total_pages"],
                "count": len(res["customers"]),
                "customers": res["customers"]
            })
        else:
            return jsonify({
                "status": "success",
                "campaign_id": campaign_id,
                "count": len(res),
                "priority_filter": priority_filter,
                "customers": res
            })
    finally:
        db.close()


@app.route("/api/customers", methods=["GET"])
def api_list_customers():
    """
    Returns paginated list of bank customer records from the Customer table.
    Supports search (name, phone, job), job filter, and education filter.
    """
    import math
    page = max(1, request.args.get("page", 1, type=int))
    page_size = max(1, min(100, request.args.get("page_size", 25, type=int)))
    search = request.args.get("search", "").strip()
    job_filter = request.args.get("job", "").strip()
    education_filter = request.args.get("education", "").strip()

    db = SessionLocal()
    try:
        query = db.query(Customer)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Customer.name.ilike(search_pattern)) |
                (Customer.phone.ilike(search_pattern)) |
                (Customer.job.ilike(search_pattern))
            )

        if job_filter:
            query = query.filter(Customer.job == job_filter)

        if education_filter:
            query = query.filter(Customer.education == education_filter)

        total_count = query.count()
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

        customers = (
            query.order_by(Customer.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return jsonify({
            "status": "success",
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "count": len(customers),
            "customers": [c.to_dict() for c in customers]
        })
    finally:
        db.close()


@app.route("/api/predict/single", methods=["POST"])
def api_predict_single():
    """Scores a single customer JSON without creating a campaign."""
    data = request.get_json() or {}
    try:
        result = predict_single(data)
        return jsonify({"status": "success", "prediction": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# --------------------------------------------------
# AUTHENTICATION & AGENT MANAGEMENT ENDPOINTS
# --------------------------------------------------

@app.route("/api/auth/login", methods=["POST"])
def login():
    """Validates user credentials and initiates session."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required."}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"status": "error", "message": "Invalid username or password."}), 401

        if not user.is_active:
            return jsonify({"status": "error", "message": "User account is deactivated."}), 403

        session["user_id"] = user.id
        session["role"] = user.role

        return jsonify({
            "status": "success",
            "message": f"Welcome back, {user.full_name}!",
            "user": user.to_dict()
        })
    finally:
        db.close()


@app.route("/api/auth/me", methods=["GET"])
def current_user():
    """Returns authenticated user profile."""
    user_id = session.get("user_id")
    # Also support ?user_id= query param for API clients/testing
    if not user_id:
        user_id = request.args.get("user_id", type=int)

    if not user_id:
        return jsonify({"status": "error", "message": "Not authenticated."}), 401

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found."}), 404
        return jsonify({"status": "success", "user": user.to_dict()})
    finally:
        db.close()


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Clears user session."""
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})


@app.route("/api/agents", methods=["GET"])
def list_agents():
    """Lists calling agents with live workload metrics."""
    db = SessionLocal()
    try:
        agents = db.query(User).filter_by(role="agent").all()
        results = []
        for agent in agents:
            a_dict = agent.to_dict()
            a_dict["pending_load"] = db.query(Assignment).filter_by(agent_id=agent.id, status="pending").count()
            a_dict["calls_completed"] = db.query(CallLog).filter_by(agent_id=agent.id).count()
            a_dict["subscriptions"] = db.query(CallLog).filter_by(agent_id=agent.id, call_outcome="Subscribed").count()
            results.append(a_dict)
        return jsonify({"status": "success", "agents": results})
    finally:
        db.close()


# --------------------------------------------------
# WORKLOAD DISTRIBUTION ENDPOINTS (Team Leader)
# --------------------------------------------------

@app.route("/api/assignments/preview", methods=["POST"])
def preview_assignments():
    """Previews smart workload distribution across agents without saving."""
    data = request.get_json() or {}
    campaign_id = data.get("campaign_id")
    agent_ids = data.get("agent_ids")
    max_per_agent = data.get("max_per_agent")

    if not campaign_id:
        return jsonify({"status": "error", "message": "campaign_id is required."}), 400

    db = SessionLocal()
    try:
        preview = preview_workload_distribution(
            campaign_id=campaign_id,
            db=db,
            agent_ids=agent_ids,
            max_per_agent=max_per_agent
        )
        return jsonify({"status": "success", "preview": preview})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/assignments/distribute", methods=["POST"])
def distribute_assignments():
    """Commits workload distribution to database."""
    data = request.get_json() or {}
    campaign_id = data.get("campaign_id")
    agent_ids = data.get("agent_ids")
    max_per_agent = data.get("max_per_agent")

    if not campaign_id:
        return jsonify({"status": "error", "message": "campaign_id is required."}), 400

    db = SessionLocal()
    try:
        result = execute_workload_distribution(
            campaign_id=campaign_id,
            db=db,
            agent_ids=agent_ids,
            max_per_agent=max_per_agent
        )
        return jsonify({
            "status": "success",
            "message": "Workload distributed successfully.",
            "data": result
        })
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()


@app.route("/api/assignments", methods=["GET"])
def list_assignments():
    """Lists assignments with optional campaign_id and agent_id filters."""
    campaign_id = request.args.get("campaign_id", type=int)
    agent_id = request.args.get("agent_id", type=int)
    status_filter = request.args.get("status")

    db = SessionLocal()
    try:
        query = db.query(Assignment, Customer).join(Customer, Assignment.customer_id == Customer.id)
        if campaign_id:
            query = query.filter(Assignment.campaign_id == campaign_id)
        if agent_id:
            query = query.filter(Assignment.agent_id == agent_id)
        if status_filter:
            query = query.filter(Assignment.status == status_filter)

        records = query.all()
        results = []
        for assign, cust in records:
            item = assign.to_dict()
            item["customer_name"] = cust.name
            item["customer_phone"] = cust.phone
            results.append(item)
        return jsonify({"status": "success", "count": len(results), "assignments": results})
    finally:
        db.close()


# --------------------------------------------------
# CALLING AGENT WORKSPACE ENDPOINTS
# --------------------------------------------------

@app.route("/api/agent/queue", methods=["GET"])
def agent_calling_queue():
    """Returns the logged-in agent's calling queue sorted by priority."""
    agent_id = request.args.get("agent_id", type=int) or session.get("user_id")
    status_filter = request.args.get("status", "pending")

    if not agent_id:
        return jsonify({"status": "error", "message": "agent_id is required."}), 400

    db = SessionLocal()
    try:
        queue = get_agent_calling_queue(agent_id=agent_id, db=db, status_filter=status_filter)
        return jsonify({"status": "success", "agent_id": agent_id, "count": len(queue), "queue": queue})
    finally:
        db.close()


@app.route("/api/agent/next-call", methods=["GET"])
def smart_next_call():
    """Smart Next Call recommendation based on due follow-ups and ML priority."""
    agent_id = request.args.get("agent_id", type=int) or session.get("user_id")

    if not agent_id:
        return jsonify({"status": "error", "message": "agent_id is required."}), 400

    db = SessionLocal()
    try:
        next_call = get_smart_next_recommended_call(agent_id=agent_id, db=db)
        if not next_call:
            return jsonify({
                "status": "success",
                "message": "No pending calls remaining in queue. Great job!",
                "next_customer": None
            })
        return jsonify({
            "status": "success",
            "next_customer": next_call
        })
    finally:
        db.close()


# --------------------------------------------------
# CALL LOGGING & OUTCOME DISPOSITION ENDPOINTS
# --------------------------------------------------

@app.route("/api/calls/log", methods=["POST"])
def log_call_outcome():
    """
    Records customer contact result:
    1. Validates call outcome ('Interested', 'Not Interested', 'Unreachable', 'Follow-up Required', 'Subscribed').
    2. Inserts record into call_logs table.
    3. Updates assignment status to 'completed' or 'in_progress'.
    4. Automatically creates FollowUp record if outcome is 'Follow-up Required'.
    """
    data = request.get_json() or {}
    assignment_id = data.get("assignment_id")
    customer_id = data.get("customer_id")
    agent_id = data.get("agent_id") or session.get("user_id")
    campaign_id = data.get("campaign_id")
    call_outcome = data.get("call_outcome")
    duration_seconds = int(data.get("duration_seconds", 0))
    remarks = data.get("remarks", "")
    followup_date_str = data.get("followup_date")

    valid_outcomes = ["Interested", "Not Interested", "Unreachable", "Follow-up Required", "Subscribed"]
    if not call_outcome or call_outcome not in valid_outcomes:
        return jsonify({
            "status": "error",
            "message": f"Invalid call outcome. Must be one of: {', '.join(valid_outcomes)}"
        }), 400

    if not customer_id or not agent_id:
        return jsonify({"status": "error", "message": "customer_id and agent_id are required."}), 400

    db = SessionLocal()
    try:
        # Create CallLog entry
        log_entry = CallLog(
            assignment_id=assignment_id,
            customer_id=customer_id,
            agent_id=agent_id,
            campaign_id=campaign_id,
            call_outcome=call_outcome,
            duration_seconds=duration_seconds,
            remarks=remarks,
            called_at=utc_now()
        )
        db.add(log_entry)
        db.flush()

        # Resolve any prior pending follow-ups for this customer
        prior_followups = (
            db.query(FollowUp)
            .filter_by(customer_id=customer_id, status="pending")
            .all()
        )
        for pfu in prior_followups:
            pfu.status = "completed"
            pfu.resolved_at = utc_now()

        # Update assignment status for this customer across campaigns
        customer_assignments = (
            db.query(Assignment)
            .filter_by(customer_id=customer_id)
            .filter(Assignment.status != "completed")
            .all()
        )
        for ca in customer_assignments:
            if call_outcome == "Follow-up Required":
                if ca.agent_id == agent_id:
                    ca.status = "in_progress"
                else:
                    ca.status = "completed"
                    ca.completed_at = utc_now()
            else:
                ca.status = "completed"
                ca.completed_at = utc_now()

        # If assignment_id was explicitly provided and not in customer_assignments, update it too
        if assignment_id:
            specific_assign = db.query(Assignment).filter_by(id=assignment_id).first()
            if specific_assign and specific_assign not in customer_assignments:
                if call_outcome == "Follow-up Required":
                    specific_assign.status = "in_progress"
                else:
                    specific_assign.status = "completed"
                    specific_assign.completed_at = utc_now()

        # Create Follow-up if needed
        followup_created = None
        if call_outcome == "Follow-up Required" or followup_date_str:
            try:
                if followup_date_str:
                    sched_dt = datetime.fromisoformat(followup_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                else:
                    # Default callback: tomorrow same time
                    from datetime import timedelta
                    sched_dt = utc_now() + timedelta(days=1)

                followup = FollowUp(
                    customer_id=customer_id,
                    agent_id=agent_id,
                    campaign_id=campaign_id,
                    call_log_id=log_entry.id,
                    scheduled_date=sched_dt,
                    notes=remarks or "Scheduled callback requested by customer.",
                    status="pending"
                )
                db.add(followup)
                db.flush()
                followup_created = followup.to_dict()
            except Exception as fe:
                print(f"Warning: could not parse followup date: {fe}")

        db.commit()
        db.refresh(log_entry)

        return jsonify({
            "status": "success",
            "message": "Call outcome logged successfully.",
            "call_log": log_entry.to_dict(),
            "followup": followup_created
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": f"Failed to log call: {str(e)}"}), 500
    finally:
        db.close()


@app.route("/api/calls", methods=["GET"])
def list_calls():
    """Lists call history with customer details."""
    agent_id = request.args.get("agent_id", type=int)
    campaign_id = request.args.get("campaign_id", type=int)

    db = SessionLocal()
    try:
        query = db.query(CallLog, Customer).join(Customer, CallLog.customer_id == Customer.id)
        if agent_id:
            query = query.filter(CallLog.agent_id == agent_id)
        if campaign_id:
            query = query.filter(CallLog.campaign_id == campaign_id)

        records = query.order_by(CallLog.called_at.desc()).limit(100).all()
        results = []
        for log, cust in records:
            item = log.to_dict()
            item["customer_name"] = cust.name
            item["customer_phone"] = cust.phone
            results.append(item)
        return jsonify({"status": "success", "count": len(results), "calls": results})
    finally:
        db.close()


# --------------------------------------------------
# FOLLOW-UP MANAGEMENT ENDPOINTS
# --------------------------------------------------

@app.route("/api/followups", methods=["GET"])
def list_followups():
    """Lists pending and overdue follow-ups."""
    agent_id = request.args.get("agent_id", type=int)
    status_filter = request.args.get("status")

    db = SessionLocal()
    try:
        query = db.query(FollowUp, Customer, User).join(
            Customer, FollowUp.customer_id == Customer.id
        ).join(
            User, FollowUp.agent_id == User.id
        )

        if agent_id:
            query = query.filter(FollowUp.agent_id == agent_id)
        if status_filter:
            query = query.filter(FollowUp.status == status_filter)

        records = query.order_by(FollowUp.scheduled_date.asc()).all()
        now = utc_now()
        results = []
        for fu, cust, agent in records:
            item = fu.to_dict()
            item["customer_name"] = cust.name
            item["customer_phone"] = cust.phone
            item["agent_name"] = agent.full_name
            item["is_overdue"] = (fu.status == "pending" and fu.scheduled_date < now)
            results.append(item)
        return jsonify({"status": "success", "count": len(results), "followups": results})
    finally:
        db.close()


@app.route("/api/followups/<int:followup_id>/complete", methods=["POST"])
def resolve_followup(followup_id):
    """Marks a follow-up as completed."""
    db = SessionLocal()
    try:
        fu = db.query(FollowUp).filter_by(id=followup_id).first()
        if not fu:
            return jsonify({"status": "error", "message": "Follow-up not found."}), 404

        fu.status = "completed"
        fu.resolved_at = utc_now()
        db.commit()
        return jsonify({"status": "success", "message": "Follow-up completed.", "followup": fu.to_dict()})
    finally:
        db.close()


# --------------------------------------------------
# OPERATIONAL ANALYTICS & DASHBOARD KPI ENDPOINTS
# --------------------------------------------------

@app.route("/api/analytics/leader-dashboard", methods=["GET"])
def leader_dashboard_analytics():
    """Returns dynamic, database-driven KPIs for the Team Leader Dashboard."""
    campaign_id = request.args.get("campaign_id", type=int)
    db = SessionLocal()
    try:
        data = get_team_leader_analytics(db=db, campaign_id=campaign_id)
        return jsonify({"status": "success", "analytics": data})
    finally:
        db.close()


@app.route("/api/analytics/agent-dashboard", methods=["GET"])
def agent_dashboard_analytics():
    """Returns personal metrics and calling history for a Calling Agent."""
    agent_id = request.args.get("agent_id", type=int) or session.get("user_id")

    if not agent_id:
        return jsonify({"status": "error", "message": "agent_id is required."}), 400

    db = SessionLocal()
    try:
        data = get_agent_personal_analytics(agent_id=agent_id, db=db)
        return jsonify({"status": "success", "agent_id": agent_id, "analytics": data})
    finally:
        db.close()


# Initialize database schema upon module load
with app.app_context():
    init_db()


if __name__ == "__main__":
    print("\nStarting CampaignIQ Flask Server on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)


