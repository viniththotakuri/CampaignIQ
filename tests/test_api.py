"""
Test Suite: Flask REST API & Call Center Workflows
Tests end-to-end integration across Auth, Campaigns, Queues, Calls, and Analytics
"""

import pytest


def test_api_health_endpoint(client):
    """Verifies that the /api/health endpoint confirms DB and ML readiness."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"]["connected"] is True
    assert data["ml_intelligence"]["ready"] is True
    assert data["ml_intelligence"]["original_xgboost_loaded"] is True
    assert data["ml_intelligence"]["v2_xgboost_loaded"] is True


def test_auth_login_endpoints(client):
    """Verifies authentication for Team Leader and Calling Agents."""
    # Leader login
    res_leader = client.post("/api/auth/login", json={"username": "leader", "password": "leader123"})
    assert res_leader.status_code == 200
    assert res_leader.get_json()["user"]["role"] == "leader"

    # Agent login
    res_agent = client.post("/api/auth/login", json={"username": "agent1", "password": "agent123"})
    assert res_agent.status_code == 200
    assert res_agent.get_json()["user"]["role"] == "agent"

    # Bad credentials
    res_bad = client.post("/api/auth/login", json={"username": "leader", "password": "wrong_password"})
    assert res_bad.status_code == 401


def test_campaign_lifecycle_and_batch_prioritization(client):
    """Verifies creating a campaign, launching it, and querying prioritized customers."""
    # 1. Create campaign
    res_create = client.post("/api/campaigns", json={
        "name": "Integration Test Term Deposit Drive",
        "description": "Automated test campaign",
        "target_calls": 25
    })
    assert res_create.status_code == 201
    camp_id = res_create.get_json()["campaign"]["id"]

    # 2. Launch campaign (triggers batch prediction via XGBoost pipeline)
    res_launch = client.post(f"/api/campaigns/{camp_id}/launch", json={})
    assert res_launch.status_code == 200
    launch_data = res_launch.get_json()["data"]
    assert launch_data["total_customers_scored"] > 0
    assert "priority_breakdown" in launch_data
    assert "High" in launch_data["priority_breakdown"]

    # 3. Retrieve prioritized list
    res_queue = client.get(f"/api/campaigns/{camp_id}/prioritized-customers?limit=10")
    assert res_queue.status_code == 200
    customers = res_queue.get_json()["customers"]
    assert len(customers) > 0
    assert customers[0]["subscription_probability"] >= customers[-1]["subscription_probability"]


def test_workload_distribution_and_agent_queue(client):
    """Verifies workload preview, distribution, and agent calling queue."""
    # Create and launch a test campaign
    c_res = client.post("/api/campaigns", json={"name": "Workload Test Campaign", "target_calls": 20})
    camp_id = c_res.get_json()["campaign"]["id"]
    client.post(f"/api/campaigns/{camp_id}/launch", json={})

    # Preview distribution
    res_prev = client.post("/api/assignments/preview", json={"campaign_id": camp_id})
    assert res_prev.status_code == 200
    assert "agent_distributions" in res_prev.get_json()["preview"]

    # Commit distribution
    res_dist = client.post("/api/assignments/distribute", json={"campaign_id": camp_id})
    assert res_dist.status_code == 200
    assert res_dist.get_json()["data"]["total_assignments_created"] > 0

    # Check agent queue
    res_queue = client.get("/api/agent/queue?agent_id=2")
    assert res_queue.status_code == 200
    queue = res_queue.get_json()["queue"]
    assert len(queue) > 0

    # Smart Next Call check
    res_next = client.get("/api/agent/next-call?agent_id=2")
    assert res_next.status_code == 200
    assert res_next.get_json()["next_customer"] is not None


def test_call_outcome_logging_and_followup(client):
    """Verifies recording call dispositions and scheduling follow-up callbacks."""
    # Log a Subscribed call
    res_call = client.post("/api/calls/log", json={
        "customer_id": 1,
        "agent_id": 2,
        "campaign_id": 1,
        "call_outcome": "Subscribed",
        "duration_seconds": 180,
        "remarks": "Signed up for 1-year deposit."
    })
    assert res_call.status_code == 201

    # Log a Follow-up Required call
    res_fu = client.post("/api/calls/log", json={
        "customer_id": 2,
        "agent_id": 2,
        "campaign_id": 1,
        "call_outcome": "Follow-up Required",
        "duration_seconds": 90,
        "remarks": "Requested callback tomorrow.",
        "followup_date": "2026-11-26T14:00:00"
    })
    assert res_fu.status_code == 201
    assert res_fu.get_json()["followup"] is not None

    # Check followups endpoint
    res_list = client.get("/api/followups?agent_id=2")
    assert res_list.status_code == 200
    assert res_list.get_json()["count"] > 0


def test_leader_and_agent_analytics(client):
    """Verifies operational analytics calculated from real database records."""
    # Leader dashboard
    res_leader = client.get("/api/analytics/leader-dashboard?campaign_id=1")
    assert res_leader.status_code == 200
    kpis = res_leader.get_json()["analytics"]["kpis"]
    assert kpis["total_customers"] > 0
    assert "conversion_rate" in kpis
    assert "agent_performance" in res_leader.get_json()["analytics"]

    # Agent dashboard
    res_agent = client.get("/api/analytics/agent-dashboard?agent_id=2")
    assert res_agent.status_code == 200
    assert "personal_kpis" in res_agent.get_json()["analytics"]


def test_customers_pagination_and_search(client):
    """Verifies server-side pagination and demographic search on /api/customers."""
    # 1. Page 1 with page_size=10
    res_p1 = client.get("/api/customers?page=1&page_size=10")
    assert res_p1.status_code == 200
    d1 = res_p1.get_json()
    assert d1["status"] == "success"
    assert d1["page"] == 1
    assert d1["page_size"] == 10
    assert d1["total_count"] == 25
    assert d1["total_pages"] == 3
    assert len(d1["customers"]) == 10

    # 2. Page 2
    res_p2 = client.get("/api/customers?page=2&page_size=10")
    assert res_p2.status_code == 200
    d2 = res_p2.get_json()
    assert d2["page"] == 2
    assert len(d2["customers"]) == 10
    assert d1["customers"][0]["id"] != d2["customers"][0]["id"]

    # 3. Search by keyword
    first_cust_name = d1["customers"][0]["name"].split()[0]
    res_search = client.get(f"/api/customers?search={first_cust_name}")
    assert res_search.status_code == 200
    ds = res_search.get_json()
    assert ds["total_count"] >= 1
    assert any(first_cust_name.lower() in c["name"].lower() for c in ds["customers"])


def test_prioritized_customers_pagination(client):
    """Verifies server-side pagination on /api/campaigns/<id>/prioritized-customers."""
    c_res = client.post("/api/campaigns", json={"name": "Pagination Test Campaign", "target_calls": 30})
    camp_id = c_res.get_json()["campaign"]["id"]
    client.post(f"/api/campaigns/{camp_id}/launch", json={})

    # Page 1 (first 5 leads)
    res_p1 = client.get(f"/api/campaigns/{camp_id}/prioritized-customers?page=1&page_size=5")
    assert res_p1.status_code == 200
    d1 = res_p1.get_json()
    assert d1["page"] == 1
    assert d1["page_size"] == 5
    assert d1["total_count"] == 25
    assert d1["total_pages"] == 5
    assert len(d1["customers"]) == 5
    assert d1["customers"][0]["rank"] == 1

    # Page 2 (next 5 leads)
    res_p2 = client.get(f"/api/campaigns/{camp_id}/prioritized-customers?page=2&page_size=5")
    assert res_p2.status_code == 200
    d2 = res_p2.get_json()
    assert d2["page"] == 2
    assert len(d2["customers"]) == 5
    assert d2["customers"][0]["rank"] == 6


def test_campaign_specific_analytics_isolation(client):
    """Verifies that selecting a campaign strictly isolates KPIs and agent performance."""
    # Create Campaign A
    res_a = client.post("/api/campaigns", json={"name": "Campaign A Isolated", "target_calls": 10})
    camp_a = res_a.get_json()["campaign"]["id"]
    client.post(f"/api/campaigns/{camp_a}/launch", json={})

    # Create Campaign B
    res_b = client.post("/api/campaigns", json={"name": "Campaign B Isolated", "target_calls": 10})
    camp_b = res_b.get_json()["campaign"]["id"]
    client.post(f"/api/campaigns/{camp_b}/launch", json={})

    # Log a completed call ONLY in Campaign A
    client.post("/api/calls/log", json={
        "customer_id": 1,
        "agent_id": 2,
        "campaign_id": camp_a,
        "call_outcome": "Subscribed",
        "duration_seconds": 150
    })

    # Query analytics for Campaign A
    res_ana_a = client.get(f"/api/analytics/leader-dashboard?campaign_id={camp_a}")
    kpi_a = res_ana_a.get_json()["analytics"]["kpis"]
    assert kpi_a["calls_completed"] == 1
    assert kpi_a["successful_subscriptions"] == 1

    # Query analytics for Campaign B -> MUST be 0 calls completed
    res_ana_b = client.get(f"/api/analytics/leader-dashboard?campaign_id={camp_b}")
    kpi_b = res_ana_b.get_json()["analytics"]["kpis"]
    assert kpi_b["calls_completed"] == 0
    assert kpi_b["successful_subscriptions"] == 0
    assert kpi_b["conversion_rate"] == 0.0

    # Verify Agent 2's performance in Campaign B shows 0 calls
    agents_b = res_ana_b.get_json()["analytics"]["agent_performance"]
    agent_2_b = next((a for a in agents_b if a["agent_id"] == 2), None)
    assert agent_2_b is not None
    assert agent_2_b["calls_completed"] == 0


def test_campaign_target_calls_progress(client):
    """Verifies that target_calls tracks progress without restricting customer scoring."""
    res_c = client.post("/api/campaigns", json={"name": "Target Tracking Campaign", "target_calls": 10})
    camp_id = res_c.get_json()["campaign"]["id"]

    # Launching campaign scores all 25 customers despite target_calls being 10
    res_launch = client.post(f"/api/campaigns/{camp_id}/launch", json={})
    assert res_launch.get_json()["data"]["total_customers_scored"] == 25
    assert res_launch.get_json()["data"]["saved_predictions_count"] == 25

    # Check progress via list campaigns
    res_list = client.get("/api/campaigns")
    c_info = next(c for c in res_list.get_json()["campaigns"] if c["id"] == camp_id)
    assert c_info["target_calls"] == 10
    assert c_info["calls_completed"] == 0
    assert c_info["target_progress"] == 0.0

