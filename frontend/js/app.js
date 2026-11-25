/**
 * CampaignIQ — Full-Stack Application Controller
 * PS-8 Banking Call Center Intelligence System
 */

// Application State
const state = {
  currentUser: {
    id: 1,
    username: "leader",
    full_name: "Vikram Malhotra",
    role: "leader"
  },
  activeView: "leader-dashboard",
  activeCampaignId: 1,
  callingCustomer: null,
  callTimerInterval: null,
  callTimerSeconds: 0,
  predictionsPage: 1,
  predictionsPageSize: 10,
  customerPoolPage: 1,
  customerPoolPageSize: 10,
  customerPoolSearch: "",
  charts: {}
};

// ============================================================================
// API CLIENT UTILITIES
// ============================================================================

async function apiRequest(endpoint, options = {}) {
  try {
    const config = {
      headers: {
        "Content-Type": "application/json"
      },
      ...options
    };

    if (config.body && typeof config.body === "object") {
      config.body = JSON.stringify(config.body);
    }

    const response = await fetch(endpoint, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || `Request failed with status ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error(`API Error on [${endpoint}]:`, error);
    showToast(error.message, "error");
    throw error;
  }
}

// Toast Notifications
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================================
// ROLE SWITCHING & WORKSPACE NAVIGATION
// ============================================================================

function switchUserRole(username, role) {
  const userMap = {
    leader: { id: 1, full_name: "Vikram Malhotra", role: "leader", initials: "VM" },
    agent1: { id: 2, full_name: "Rahul Sharma", role: "agent", initials: "RS" },
    agent2: { id: 3, full_name: "Priya Patel", role: "agent", initials: "PP" },
    agent3: { id: 4, full_name: "Amit Verma", role: "agent", initials: "AV" }
  };

  const target = userMap[username] || userMap.leader;
  state.currentUser = {
    id: target.id,
    username: username,
    full_name: target.full_name,
    role: target.role
  };

  // Update UI indicators
  document.getElementById("sidebarUserName").textContent = target.full_name;
  document.getElementById("sidebarAvatar").textContent = target.initials;

  const rolePill = document.getElementById("sidebarRolePill");
  const roleLabel = document.getElementById("sidebarRoleLabel");
  const navGroupLeader = document.getElementById("navGroupLeader");
  const navGroupAgent = document.getElementById("navGroupAgent");

  if (target.role === "leader") {
    rolePill.className = "role-pill leader";
    roleLabel.textContent = "Team Leader";
    navGroupLeader.style.display = "block";
    navGroupAgent.style.display = "none";
    document.getElementById("sidebarUserRole").textContent = "Call Center Leader";
    navigateToView("leader-dashboard");
  } else {
    rolePill.className = "role-pill agent";
    roleLabel.textContent = "Calling Agent";
    navGroupLeader.style.display = "none";
    navGroupAgent.style.display = "block";
    document.getElementById("sidebarUserRole").textContent = "Calling Agent Workspace";
    navigateToView("agent-dashboard");
  }

  closeModal("modalSwitchUser");
  showToast(`Switched workspace to ${target.full_name} (${target.role.toUpperCase()})`);
}

function navigateToView(viewId) {
  state.activeView = viewId;

  // Update sidebar active states
  document.querySelectorAll(".nav-item").forEach(item => {
    item.classList.toggle("active", item.getAttribute("data-view") === viewId);
  });

  // Switch view containers
  document.querySelectorAll(".view-section").forEach(sec => {
    sec.classList.remove("active");
  });

  const targetSec = document.getElementById(`view-${viewId}`);
  if (targetSec) {
    targetSec.classList.add("active");
  }

  // Update page header title
  const titles = {
    "leader-dashboard": "Team Leader Operations Control",
    "campaigns": "Telemarketing Campaigns",
    "predictions": "ML-Powered Customer Prioritization",
    "assignments": "Customer Workload Assignment",
    "agents": "Calling Agents Performance",
    "calls": "Call Disposition Logs",
    "followups": "Follow-Up Management",
    "analytics": "Performance & Conversion Analytics",
    "customers": "Customer Benchmark Pool",
    "agent-dashboard": "Calling Agent Workspace",
    "agent-queue": "My Assigned Calling Queue",
    "agent-history": "My Call Disposition History",
    "agent-followups": "My Scheduled Follow-ups",
    "agent-performance": "My Conversion Metrics"
  };

  document.getElementById("pageTitle").textContent = titles[viewId] || "CampaignIQ";

  // Trigger relevant data loader
  loadViewData(viewId);
}

function loadViewData(viewId) {
  switch (viewId) {
    case "leader-dashboard":
      loadLeaderDashboard();
      break;
    case "campaigns":
      loadCampaigns();
      break;
    case "predictions":
      loadPredictions();
      break;
    case "assignments":
      loadAssignments();
      break;
    case "agents":
      loadAgents();
      break;
    case "calls":
      loadCallLogs();
      break;
    case "followups":
      loadFollowups();
      break;
    case "analytics":
      loadAnalyticsView();
      break;
    case "customers":
      loadCustomerPool();
      break;
    case "agent-dashboard":
      loadAgentDashboard();
      break;
    case "agent-queue":
      loadAgentQueueFull();
      break;
    case "agent-history":
      loadAgentCallHistory();
      break;
    case "agent-followups":
      loadAgentFollowups();
      break;
    case "agent-performance":
      loadAgentPerformanceMetrics();
      break;
  }
}

// ============================================================================
// DATA LOADERS & RENDERERS
// ============================================================================

// 1. Leader Dashboard
async function loadLeaderDashboard() {
  try {
    const data = await apiRequest(`/api/analytics/leader-dashboard?campaign_id=${state.activeCampaignId || 1}`);
    const kpis = data.analytics.kpis;

    document.getElementById("kpiTotalCustomers").textContent = kpis.total_customers;
    document.getElementById("kpiCallsCompleted").textContent = kpis.calls_completed;
    document.getElementById("kpiSubscriptions").textContent = kpis.successful_subscriptions;
    document.getElementById("kpiConversionRate").textContent = `${kpis.conversion_rate}%`;
    document.getElementById("kpiHighPriorityRemaining").textContent = kpis.high_priority_remaining;

    // Needs Attention Container
    const needsContainer = document.getElementById("needsAttentionContainer");
    if (data.analytics.needs_attention && data.analytics.needs_attention.length > 0) {
      needsContainer.innerHTML = data.analytics.needs_attention.map(item => `
        <div class="alert-card ${item.severity}">
          <div class="alert-body">
            <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <div>
              <div class="alert-text-main">${item.message}</div>
              <div class="alert-text-sub">${item.due_date ? `Scheduled callback: ${new Date(item.due_date).toLocaleString()}` : 'Campaign backlog action needed'}</div>
            </div>
          </div>
          <button class="btn btn-sm btn-outline" onclick="navigateToView('${item.type.includes('followup') ? 'followups' : 'assignments'}')">
            Review
          </button>
        </div>
      `).join("");
    } else {
      needsContainer.innerHTML = `
        <div class="empty-state" style="padding: 1.5rem;">
          <p>All follow-ups are up to date and high-priority customers are assigned.</p>
        </div>
      `;
    }

    // Render Charts
    renderAgentPerformanceChart(data.analytics.agent_performance);
    renderCallOutcomesChart(data.analytics.outcome_distribution);

    // Load active campaigns table
    loadDashboardCampaigns();
  } catch (err) {
    console.error("Leader dashboard load error", err);
  }
}

// 2. Campaigns View & Mini Table
async function loadCampaigns() {
  try {
    const data = await apiRequest("/api/campaigns");
    const campaigns = data.campaigns || [];

    const tbody = document.getElementById("allCampaignsTbody");
    if (!campaigns.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No campaigns found. Create your first campaign above.</td></tr>`;
      return;
    }

    tbody.innerHTML = campaigns.map(c => `
      <tr>
        <td><strong>#${c.id}</strong></td>
        <td>
          <div style="font-weight: 700; color: var(--color-text-primary);">${c.name}</div>
          <div style="font-size: 0.75rem; color: var(--color-text-secondary);">${c.description || 'Target deposit campaign'}</div>
        </td>
        <td>
          <div style="font-weight: 700;">${c.calls_completed || 0} / ${c.target_calls}</div>
          <div style="font-size: 0.72rem; color: var(--color-text-secondary);">${c.target_progress || 0}% completed</div>
        </td>
        <td><span class="badge ${c.status === 'active' ? 'badge-success' : 'badge-draft'}">${c.status.toUpperCase()}</span></td>
        <td><strong>${c.total_prioritized}</strong> scored</td>
        <td>
          <span class="badge badge-high">${c.high_priority_count} H</span>
          <span class="badge badge-med">${c.medium_priority_count} M</span>
          <span class="badge badge-low">${c.low_priority_count} L</span>
        </td>
        <td style="font-size: 0.8rem; color: var(--color-text-muted);">${c.created_at ? new Date(c.created_at).toLocaleDateString() : '--'}</td>
        <td>
          ${c.status === 'draft' ? `
            <button class="btn btn-sm btn-primary" onclick="launchCampaignAction(${c.id})">
              Launch & Prioritize
            </button>
          ` : `
            <button class="btn btn-sm btn-outline" onclick="viewCampaignPredictions(${c.id})">
              View Prioritization
            </button>
          `}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Error loading campaigns", err);
  }
}

async function loadDashboardCampaigns() {
  try {
    const data = await apiRequest("/api/campaigns");
    const campaigns = data.campaigns || [];
    const tbody = document.getElementById("dashboardCampaignsTbody");

    if (!campaigns.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--color-text-muted); padding: 1.5rem;">No active campaigns. Click "+ New Campaign" to create one.</td></tr>`;
      return;
    }

    tbody.innerHTML = campaigns.map(c => `
      <tr>
        <td>
          <strong>${c.name}</strong>
          <div style="font-size: 0.75rem; color: var(--color-text-muted);">ID: #${c.id}</div>
        </td>
        <td>
          <strong>${c.calls_completed || 0} / ${c.target_calls}</strong> calls
          <div style="font-size: 0.72rem; color: var(--color-text-muted);">${c.target_progress || 0}% goal reached</div>
        </td>
        <td><span class="badge ${c.status === 'active' ? 'badge-success' : 'badge-draft'}">${c.status.toUpperCase()}</span></td>
        <td>${c.total_prioritized} Customers</td>
        <td>
          <span class="badge badge-high">${c.high_priority_count} High</span>
          <span class="badge badge-med">${c.medium_priority_count} Med</span>
          <span class="badge badge-low">${c.low_priority_count} Low</span>
        </td>
        <td>
          ${c.status === 'draft' ? `
            <button class="btn btn-sm btn-primary" onclick="launchCampaignAction(${c.id})">
              Launch & Prioritize
            </button>
          ` : `
            <button class="btn btn-sm btn-outline" onclick="navigateToView('predictions')">
              Calling Queue
            </button>
          `}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Dashboard campaigns load error", err);
  }
}

async function launchCampaignAction(campaignId) {
  try {
    showToast("Scoring customer pool via background XGBoost ML models...", "info");
    const res = await apiRequest(`/api/campaigns/${campaignId}/launch`, { method: "POST" });
    showToast(`Campaign launched! Prioritized ${res.data.total_customers_scored} customers.`);
    state.activeCampaignId = campaignId;
    loadCampaigns();
    loadLeaderDashboard();
  } catch (err) {
    // Handled in apiRequest
  }
}

function viewCampaignPredictions(campaignId) {
  state.activeCampaignId = campaignId;
  navigateToView("predictions");
}

// 3. Customer Prioritization View
async function loadPredictions() {
  try {
    const priority = document.getElementById("selectPriorityFilter").value;
    const page = state.predictionsPage || 1;
    const pageSize = state.predictionsPageSize || 10;

    let url = `/api/campaigns/${state.activeCampaignId || 1}/prioritized-customers?page=${page}&page_size=${pageSize}`;
    if (priority) url += `&priority=${priority}`;

    const data = await apiRequest(url);
    const customers = data.customers || [];
    const tbody = document.getElementById("prioritizedCustomersTbody");
    const pageInfo = document.getElementById("predictionsPageInfo");
    const btnPrev = document.getElementById("btnPredictionsPrev");
    const btnNext = document.getElementById("btnPredictionsNext");

    if (pageInfo) {
      const totalCount = data.total_count !== undefined ? data.total_count : customers.length;
      const totalPages = data.total_pages || 1;
      pageInfo.textContent = `Showing page ${data.page || 1} of ${totalPages} (${totalCount} prioritized leads)`;
      if (btnPrev) btnPrev.disabled = (data.page || 1) <= 1;
      if (btnNext) btnNext.disabled = (data.page || 1) >= totalPages;
    }

    if (!customers.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No prioritized customers found for this campaign.</td></tr>`;
      return;
    }

    tbody.innerHTML = customers.map(c => `
      <tr>
        <td><strong>#${c.rank}</strong></td>
        <td>
          <div style="font-weight: 700;">${c.customer_name}</div>
          <div style="font-size: 0.75rem; color: var(--color-text-muted);">ID: ${c.customer_id}</div>
        </td>
        <td>${c.customer_age} yrs, ${c.customer_job}</td>
        <td>${c.customer_phone}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <div style="flex: 1; height: 7px; background: var(--color-border); border-radius: 4px; overflow: hidden; width: 80px;">
              <div style="width: ${c.subscription_percentage}%; height: 100%; background: ${c.priority === 'High' ? 'var(--color-danger)' : c.priority === 'Medium' ? 'var(--color-warning)' : 'var(--color-secondary)'};"></div>
            </div>
            <strong>${c.subscription_percentage}%</strong>
          </div>
        </td>
        <td>
          <span class="badge ${c.priority === 'High' ? 'badge-high' : c.priority === 'Medium' ? 'badge-med' : 'badge-low'}">
            ${c.priority}
          </span>
        </td>
        <td style="font-size: 0.8rem;">${c.model_used}</td>
        <td style="font-size: 0.8rem; color: var(--color-text-secondary);">${c.scenario}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Predictions load error", err);
  }
}

// 4. Assignments View
async function loadAssignments() {
  try {
    const data = await apiRequest(`/api/assignments?campaign_id=${state.activeCampaignId || 1}`);
    const assignments = data.assignments || [];

    const total = assignments.length;
    const pending = assignments.filter(a => a.status === "pending").length;
    const completed = assignments.filter(a => a.status === "completed").length;

    document.getElementById("kpiAssignmentsTotal").textContent = total;
    document.getElementById("kpiAssignmentsPending").textContent = pending;
    document.getElementById("kpiAssignmentsCompleted").textContent = completed;

    const tbody = document.getElementById("assignmentsListTbody");
    if (!assignments.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No customers assigned yet. Click "Distribute Unassigned Customers" above.</td></tr>`;
      return;
    }

    tbody.innerHTML = assignments.map(a => `
      <tr>
        <td>#${a.id}</td>
        <td><strong>${a.customer_name}</strong></td>
        <td>${a.customer_phone}</td>
        <td><span class="badge badge-med">Agent #${a.agent_id}</span></td>
        <td><span class="badge ${a.priority === 'High' ? 'badge-high' : a.priority === 'Medium' ? 'badge-med' : 'badge-low'}">${a.priority}</span></td>
        <td><span class="badge ${a.status === 'completed' ? 'badge-success' : 'badge-warning'}">${a.status.toUpperCase()}</span></td>
        <td style="font-size: 0.8rem; color: var(--color-text-muted);">${a.assigned_at ? new Date(a.assigned_at).toLocaleDateString() : '--'}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Assignments load error", err);
  }
}

// 5. Calling Agents View
async function loadAgents() {
  try {
    const data = await apiRequest("/api/agents");
    const agents = data.agents || [];
    const tbody = document.getElementById("agentsListTbody");

    tbody.innerHTML = agents.map(a => `
      <tr>
        <td>
          <div style="font-weight: 700; color: var(--color-text-primary);">${a.full_name}</div>
          <div style="font-size: 0.75rem; color: var(--color-text-muted);">Role: Calling Agent</div>
        </td>
        <td><code>${a.username}</code></td>
        <td>${a.email || '--'}</td>
        <td><strong>${a.pending_load}</strong> pending</td>
        <td>${a.calls_completed} calls</td>
        <td><span class="badge badge-success">${a.subscriptions} Subscribed</span></td>
        <td><strong>${a.calls_completed > 0 ? Math.round((a.subscriptions / a.calls_completed) * 100) : 0}%</strong></td>
        <td><span class="badge badge-success">ACTIVE</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Agents load error", err);
  }
}

// 6. Global Call Logs View
async function loadCallLogs() {
  try {
    const data = await apiRequest("/api/calls");
    const calls = data.calls || [];
    const tbody = document.getElementById("callLogsTbody");

    if (!calls.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No call dispositions logged yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = calls.map(c => `
      <tr>
        <td>#${c.id}</td>
        <td><strong>${c.customer_name}</strong></td>
        <td>${c.customer_phone}</td>
        <td>Agent #${c.agent_id}</td>
        <td>
          <span class="badge ${c.call_outcome === 'Subscribed' ? 'badge-success' : c.call_outcome === 'Follow-up Required' ? 'badge-warning' : c.call_outcome === 'Interested' ? 'badge-med' : 'badge-danger'}">
            ${c.call_outcome}
          </span>
        </td>
        <td>${c.duration_seconds}s</td>
        <td style="font-size: 0.82rem; color: var(--color-text-secondary); max-width: 250px;">${c.remarks || '--'}</td>
        <td style="font-size: 0.8rem; color: var(--color-text-muted);">${c.called_at ? new Date(c.called_at).toLocaleString() : '--'}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Call logs load error", err);
  }
}

// 7. Follow-ups View
async function loadFollowups() {
  try {
    const data = await apiRequest("/api/followups");
    const followups = data.followups || [];
    const tbody = document.getElementById("followupsTbody");

    if (!followups.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No scheduled follow-up callbacks.</td></tr>`;
      return;
    }

    tbody.innerHTML = followups.map(f => `
      <tr>
        <td>#${f.id}</td>
        <td><strong>${f.customer_name}</strong></td>
        <td>${f.customer_phone}</td>
        <td>${f.agent_name || `Agent #${f.agent_id}`}</td>
        <td>
          <strong>${f.scheduled_date ? new Date(f.scheduled_date).toLocaleString() : '--'}</strong>
          ${f.is_overdue ? '<span class="badge badge-danger" style="margin-left: 0.4rem;">OVERDUE</span>' : ''}
        </td>
        <td style="font-size: 0.82rem; color: var(--color-text-secondary);">${f.notes || '--'}</td>
        <td><span class="badge ${f.status === 'completed' ? 'badge-success' : 'badge-warning'}">${f.status.toUpperCase()}</span></td>
        <td>
          ${f.status === 'pending' ? `
            <button class="btn btn-sm btn-outline" onclick="completeFollowupAction(${f.id})">
              Mark Complete
            </button>
          ` : `
            <span style="font-size: 0.8rem; color: var(--color-text-muted);">Resolved</span>
          `}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Followups load error", err);
  }
}

async function completeFollowupAction(id) {
  try {
    await apiRequest(`/api/followups/${id}/complete`, { method: "POST" });
    showToast("Follow-up marked as completed.");
    loadFollowups();
  } catch (err) {
    // Handled in apiRequest
  }
}

// 8. Analytics View
async function loadAnalyticsView() {
  try {
    const data = await apiRequest(`/api/analytics/leader-dashboard?campaign_id=${state.activeCampaignId || 1}`);
    renderAnalyticsAgentsChart(data.analytics.agent_performance);
    renderAnalyticsOutcomesChart(data.analytics.outcome_distribution);
  } catch (err) {
    console.error("Analytics view load error", err);
  }
}

// 9. Customer Pool
async function loadCustomerPool() {
  try {
    const page = state.customerPoolPage || 1;
    const pageSize = state.customerPoolPageSize || 10;
    const search = state.customerPoolSearch || "";

    let url = `/api/customers?page=${page}&page_size=${pageSize}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const data = await apiRequest(url);
    const customers = data.customers || [];
    const tbody = document.getElementById("customersTableTbody");
    const pageInfo = document.getElementById("customerPoolPageInfo");
    const btnPrev = document.getElementById("btnCustomerPrev");
    const btnNext = document.getElementById("btnCustomerNext");

    if (pageInfo) {
      pageInfo.textContent = `Showing page ${data.page} of ${data.total_pages} (${data.total_count} total bank customers)`;
      if (btnPrev) btnPrev.disabled = data.page <= 1;
      if (btnNext) btnNext.disabled = data.page >= data.total_pages;
    }

    if (!customers.length) {
      tbody.innerHTML = `<tr><td colspan="10" class="empty-state">No customers match your search criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = customers.map(c => `
      <tr>
        <td>#${c.id}</td>
        <td><strong>${c.name}</strong></td>
        <td>${c.phone}</td>
        <td>${c.age}</td>
        <td>${c.job || 'unknown'}</td>
        <td>${c.education || 'unknown'}</td>
        <td><span class="badge ${c.housing === 'yes' ? 'badge-med' : 'badge-draft'}">${(c.housing || 'unknown').toUpperCase()}</span></td>
        <td><span class="badge ${c.loan === 'yes' ? 'badge-danger' : 'badge-draft'}">${(c.loan || 'unknown').toUpperCase()}</span></td>
        <td>${c.campaign || 1}</td>
        <td><span class="badge ${c.poutcome === 'success' ? 'badge-success' : 'badge-draft'}">${c.poutcome || 'nonexistent'}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Customer pool load error", err);
  }
}

// ============================================================================
// CALLING AGENT WORKSPACE METHODS
// ============================================================================

async function loadAgentDashboard() {
  try {
    const agentId = state.currentUser.id;
    const [analyticsData, nextCallData, queueData] = await Promise.all([
      apiRequest(`/api/analytics/agent-dashboard?agent_id=${agentId}`),
      apiRequest(`/api/agent/next-call?agent_id=${agentId}`),
      apiRequest(`/api/agent/queue?agent_id=${agentId}&status=pending`)
    ]);

    const kpis = analyticsData.analytics.personal_kpis;
    document.getElementById("kpiAgentTotalAssigned").textContent = kpis.total_assigned;
    document.getElementById("kpiAgentCallsCompleted").textContent = kpis.calls_completed;
    document.getElementById("kpiAgentSubscriptions").textContent = kpis.successful_subscriptions;
    document.getElementById("kpiAgentConversionRate").textContent = `${kpis.conversion_rate}%`;
    document.getElementById("kpiAgentFollowupsDue").textContent = kpis.followups_due;

    // Render Smart Next Call Banner
    const nextCust = nextCallData.next_customer;
    const banner = document.getElementById("smartNextCallBanner");

    if (nextCust) {
      state.callingCustomer = nextCust;
      document.getElementById("nextCallReason").textContent = nextCust.recommendation_reason || "Recommended Next Customer";
      document.getElementById("nextCallName").textContent = nextCust.customer_name;
      document.getElementById("nextCallPhone").textContent = `Phone: ${nextCust.customer_phone}`;
      document.getElementById("nextCallDemographics").textContent = `${nextCust.age} yrs | ${nextCust.job || 'Client'}`;
      document.getElementById("nextCallPropensity").textContent = `Propensity: ${nextCust.subscription_percentage ? nextCust.subscription_percentage + '%' : 'High'}`;
      document.getElementById("btnInitiateNextCall").style.display = "inline-flex";
    } else {
      state.callingCustomer = null;
      document.getElementById("nextCallReason").textContent = "Queue Completed";
      document.getElementById("nextCallName").textContent = "All Assigned Calls Completed!";
      document.getElementById("nextCallPhone").textContent = "No pending calls in queue.";
      document.getElementById("nextCallDemographics").textContent = "Check back when team leader distributes more leads.";
      document.getElementById("nextCallPropensity").textContent = "";
      document.getElementById("btnInitiateNextCall").style.display = "none";
    }

    // Render Quick Queue Preview (first 5)
    const queue = queueData.queue || [];
    const tbody = document.getElementById("agentDashboardQueueTbody");

    if (!queue.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No pending calls remaining in your queue. Great job!</td></tr>`;
      return;
    }

    tbody.innerHTML = queue.slice(0, 5).map(q => `
      <tr>
        <td><strong>#${q.queue_position}</strong></td>
        <td><strong>${q.customer_name}</strong></td>
        <td>${q.customer_phone}</td>
        <td>${q.age} yrs, ${q.job}</td>
        <td><strong>${q.subscription_percentage || '--'}%</strong></td>
        <td><span class="badge ${q.priority === 'High' ? 'badge-high' : q.priority === 'Medium' ? 'badge-med' : 'badge-low'}">${q.priority}</span></td>
        <td>
          <button class="btn btn-sm btn-primary" onclick="initiateCallModal(${JSON.stringify(q).replace(/"/g, '&quot;')})">
            Call Customer
          </button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.error("Agent dashboard load error", err);
  }
}

async function loadAgentQueueFull() {
  try {
    const data = await apiRequest(`/api/agent/queue?agent_id=${state.currentUser.id}&status=all`);
    const queue = data.queue || [];
    const tbody = document.getElementById("agentFullQueueTbody");

    if (!queue.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No customers assigned to you in this campaign yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = queue.map(q => `
      <tr>
        <td>#${q.queue_position}</td>
        <td><strong>${q.customer_name}</strong></td>
        <td>${q.customer_phone}</td>
        <td>${q.age} yrs, ${q.job}</td>
        <td>H: ${q.housing_loan} | L: ${q.personal_loan}</td>
        <td><strong>${q.subscription_percentage}%</strong></td>
        <td><span class="badge ${q.priority === 'High' ? 'badge-high' : q.priority === 'Medium' ? 'badge-med' : 'badge-low'}">${q.priority}</span></td>
        <td>
          ${q.status === 'pending' || q.status === 'in_progress' ? `
            <button class="btn btn-sm btn-primary" onclick="initiateCallModal(${JSON.stringify(q).replace(/"/g, '&quot;')})">
              Call Now
            </button>
          ` : `
            <span class="badge badge-success">COMPLETED</span>
          `}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Agent queue full load error", err);
  }
}

async function loadAgentCallHistory() {
  try {
    const data = await apiRequest(`/api/calls?agent_id=${state.currentUser.id}`);
    const calls = data.calls || [];
    const tbody = document.getElementById("agentHistoryTbody");

    if (!calls.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">You have not completed any calls yet today.</td></tr>`;
      return;
    }

    tbody.innerHTML = calls.map(c => `
      <tr>
        <td>#${c.id}</td>
        <td><strong>${c.customer_name}</strong></td>
        <td>${c.customer_phone}</td>
        <td><span class="badge ${c.call_outcome === 'Subscribed' ? 'badge-success' : c.call_outcome === 'Follow-up Required' ? 'badge-warning' : 'badge-danger'}">${c.call_outcome}</span></td>
        <td>${c.duration_seconds} sec</td>
        <td style="font-size: 0.82rem; color: var(--color-text-secondary);">${c.remarks || '--'}</td>
        <td style="font-size: 0.8rem; color: var(--color-text-muted);">${c.called_at ? new Date(c.called_at).toLocaleString() : '--'}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Agent history load error", err);
  }
}

async function loadAgentFollowups() {
  try {
    const data = await apiRequest(`/api/followups?agent_id=${state.currentUser.id}`);
    const followups = data.followups || [];
    const tbody = document.getElementById("agentFollowupsTbody");

    if (!followups.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No scheduled follow-up callbacks for your queue.</td></tr>`;
      return;
    }

    tbody.innerHTML = followups.map(f => `
      <tr>
        <td>#${f.id}</td>
        <td><strong>${f.customer_name}</strong></td>
        <td>${f.customer_phone}</td>
        <td><strong>${f.scheduled_date ? new Date(f.scheduled_date).toLocaleString() : '--'}</strong></td>
        <td style="font-size: 0.82rem;">${f.notes || '--'}</td>
        <td><span class="badge ${f.status === 'completed' ? 'badge-success' : 'badge-warning'}">${f.status.toUpperCase()}</span></td>
        <td>
          ${f.status === 'pending' ? `
            <button class="btn btn-sm btn-outline" onclick="completeFollowupAction(${f.id})">
              Resolve
            </button>
          ` : `
            <span style="color: var(--color-text-muted); font-size: 0.8rem;">Resolved</span>
          `}
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Agent followups load error", err);
  }
}

async function loadAgentPerformanceMetrics() {
  try {
    const data = await apiRequest(`/api/analytics/agent-dashboard?agent_id=${state.currentUser.id}`);
    const kpis = data.analytics.personal_kpis;

    document.getElementById("kpiAgentPerfConv").textContent = `${kpis.conversion_rate}%`;
    document.getElementById("kpiAgentPerfCalls").textContent = kpis.calls_completed;
    document.getElementById("kpiAgentPerfPending").textContent = kpis.pending_queue;
  } catch (err) {
    console.error("Agent performance load error", err);
  }
}

// ============================================================================
// CALL DISPOSITION MODAL & TIMER
// ============================================================================

function initiateCallModal(customer) {
  state.callingCustomer = customer;

  document.getElementById("callModalCustName").textContent = customer.customer_name;
  document.getElementById("callModalCustPhone").textContent = customer.customer_phone;
  document.getElementById("callModalAssignmentId").value = customer.assignment_id || "";
  document.getElementById("callModalCustomerId").value = customer.customer_id;
  document.getElementById("callModalCampaignId").value = customer.campaign_id || state.activeCampaignId || 1;

  document.getElementById("callModalProfileDetails").innerHTML = `
    <span>${customer.age ? customer.age + ' yrs, ' + (customer.job || 'Client') : 'Demographics verified'}</span>
    <span class="badge ${customer.priority === 'High' ? 'badge-high' : 'badge-med'}">${customer.priority || 'Medium'} Propensity (${customer.subscription_percentage || 50}%)</span>
  `;

  // Reset form
  document.querySelectorAll("input[name='callOutcomeRadio']").forEach(r => r.checked = false);
  document.getElementById("callModalRemarks").value = "";
  document.getElementById("callModalFollowupDate").value = "";
  document.getElementById("groupFollowupDate").style.display = "none";

  // Start Call Timer
  clearInterval(state.callTimerInterval);
  state.callTimerSeconds = 0;
  updateTimerDisplay();

  state.callTimerInterval = setInterval(() => {
    state.callTimerSeconds++;
    updateTimerDisplay();
  }, 1000);

  openModal("modalCallDisposition");
}

function updateTimerDisplay() {
  const m = String(Math.floor(state.callTimerSeconds / 60)).padStart(2, "0");
  const s = String(state.callTimerSeconds % 60).padStart(2, "0");
  document.getElementById("callModalTimer").textContent = `${m}:${s}`;
}

async function submitCallOutcome() {
  const outcomeRadio = document.querySelector("input[name='callOutcomeRadio']:checked");
  if (!outcomeRadio) {
    showToast("Please select a call disposition outcome.", "error");
    return;
  }

  const assignmentId = document.getElementById("callModalAssignmentId").value;
  const customerId = document.getElementById("callModalCustomerId").value;
  const campaignId = document.getElementById("callModalCampaignId").value;
  const remarks = document.getElementById("callModalRemarks").value;
  const followupDate = document.getElementById("callModalFollowupDate").value;

  const payload = {
    assignment_id: assignmentId ? parseInt(assignmentId) : null,
    customer_id: parseInt(customerId),
    agent_id: state.currentUser.id,
    campaign_id: campaignId ? parseInt(campaignId) : 1,
    call_outcome: outcomeRadio.value,
    duration_seconds: state.callTimerSeconds,
    remarks: remarks,
    followup_date: followupDate || null
  };

  try {
    clearInterval(state.callTimerInterval);
    const res = await apiRequest("/api/calls/log", {
      method: "POST",
      body: payload
    });

    showToast(`Call logged: ${outcomeRadio.value}!`);
    closeModal("modalCallDisposition");

    state.callingCustomer = null;

    // Refresh current view
    await loadViewData(state.activeView);
  } catch (err) {
    // Handled in apiRequest
  }
}

// ============================================================================
// WORKLOAD DISTRIBUTION MODAL & PREVIEW
// ============================================================================

async function openWorkloadDistributionModal() {
  try {
    const data = await apiRequest("/api/campaigns");
    const campaigns = data.campaigns || [];
    const select = document.getElementById("distributeCampSelect");

    select.innerHTML = campaigns.map(c => `
      <option value="${c.id}" ${c.id === state.activeCampaignId ? 'selected' : ''}>${c.name} (${c.total_prioritized} prioritized)</option>
    `).join("");

    document.getElementById("distributionPreviewContainer").style.display = "none";
    document.getElementById("btnCommitDistribution").disabled = true;

    openModal("modalDistribute");
  } catch (err) {
    console.error("Open distribute modal error", err);
  }
}

async function generateWorkloadPreview() {
  const campId = document.getElementById("distributeCampSelect").value;
  const maxPerAgent = document.getElementById("distributeMaxPerAgent").value;

  try {
    const data = await apiRequest("/api/assignments/preview", {
      method: "POST",
      body: {
        campaign_id: parseInt(campId),
        max_per_agent: maxPerAgent ? parseInt(maxPerAgent) : null
      }
    });

    const preview = data.preview;
    const cardsContainer = document.getElementById("distributionPreviewCards");

    cardsContainer.innerHTML = preview.agent_distributions.map(a => `
      <div style="background-color: var(--color-background); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: 0.75rem 1rem; display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="font-weight: 700;">${a.agent_name} (${a.username})</div>
          <div style="font-size: 0.75rem; color: var(--color-text-secondary);">Current Queue: ${a.current_pending_load} calls</div>
        </div>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          <span class="badge badge-high">+${a.high_priority} High</span>
          <span class="badge badge-med">+${a.medium_priority} Med</span>
          <span class="badge badge-low">+${a.low_priority} Low</span>
          <strong style="font-size: 0.95rem; margin-left: 0.5rem;">= ${a.simulated_total} Total</strong>
        </div>
      </div>
    `).join("");

    document.getElementById("distributionPreviewContainer").style.display = "block";
    document.getElementById("btnCommitDistribution").disabled = (preview.total_to_assign === 0);

    showToast(`Simulation complete: ${preview.total_to_assign} leads to distribute.`);
  } catch (err) {
    // Handled in apiRequest
  }
}

async function commitWorkloadDistribution() {
  const campId = document.getElementById("distributeCampSelect").value;
  const maxPerAgent = document.getElementById("distributeMaxPerAgent").value;

  try {
    const data = await apiRequest("/api/assignments/distribute", {
      method: "POST",
      body: {
        campaign_id: parseInt(campId),
        max_per_agent: maxPerAgent ? parseInt(maxPerAgent) : null
      }
    });

    showToast(`Successfully created ${data.data.total_assignments_created} assignments!`);
    closeModal("modalDistribute");
    loadAssignments();
  } catch (err) {
    // Handled in apiRequest
  }
}

// ============================================================================
// MODAL CONTROLLERS & EVENT LISTENERS
// ============================================================================

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
  if (modalId === "modalCallDisposition") {
    clearInterval(state.callTimerInterval);
  }
}

function setupEventListeners() {
  // Navigation sidebar item clicks
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const viewId = item.getAttribute("data-view");
      if (viewId) navigateToView(viewId);
    });
  });

  // Switch User Modal triggers
  document.getElementById("btnQuickSwitch").addEventListener("click", () => {
    openModal("modalSwitchUser");
  });

  document.getElementById("btnCloseSwitchUserModal").addEventListener("click", () => {
    closeModal("modalSwitchUser");
  });

  document.querySelectorAll(".user-switch-card").forEach(card => {
    card.addEventListener("click", () => {
      const uname = card.getAttribute("data-username");
      const urole = card.getAttribute("data-role");
      switchUserRole(uname, urole);
    });
  });

  // New Campaign Modal triggers
  const btnNewCamp = document.getElementById("btnOpenNewCampaignModal");
  if (btnNewCamp) btnNewCamp.addEventListener("click", () => openModal("modalNewCampaign"));

  const btnNewCamp2 = document.getElementById("btnOpenNewCampaignModal2");
  if (btnNewCamp2) btnNewCamp2.addEventListener("click", () => openModal("modalNewCampaign"));

  document.getElementById("btnCloseNewCampaignModal").addEventListener("click", () => closeModal("modalNewCampaign"));
  document.getElementById("btnCancelNewCampaignModal").addEventListener("click", () => closeModal("modalNewCampaign"));

  document.getElementById("btnSubmitNewCampaign").addEventListener("click", async () => {
    const name = document.getElementById("newCampName").value;
    const desc = document.getElementById("newCampDescription").value;
    const target = document.getElementById("newCampTarget").value;

    if (!name) {
      showToast("Please enter a campaign name.", "error");
      return;
    }

    try {
      await apiRequest("/api/campaigns", {
        method: "POST",
        body: {
          name: name,
          description: desc,
          target_calls: parseInt(target) || 50
        }
      });
      showToast("Campaign draft created!");
      closeModal("modalNewCampaign");
      loadCampaigns();
    } catch (err) {}
  });

  // Workload Distribution Modal triggers
  const btnOpenDist = document.getElementById("btnOpenDistributeModal");
  if (btnOpenDist) btnOpenDist.addEventListener("click", openWorkloadDistributionModal);

  document.getElementById("btnCloseDistributeModal").addEventListener("click", () => closeModal("modalDistribute"));
  document.getElementById("btnCancelDistributeModal").addEventListener("click", () => closeModal("modalDistribute"));
  document.getElementById("btnPreviewDistribution").addEventListener("click", generateWorkloadPreview);
  document.getElementById("btnCommitDistribution").addEventListener("click", commitWorkloadDistribution);

  // Call Disposition Modal triggers
  document.getElementById("btnCloseCallModal").addEventListener("click", () => closeModal("modalCallDisposition"));
  document.getElementById("btnCancelCallModal").addEventListener("click", () => closeModal("modalCallDisposition"));
  document.getElementById("btnSaveCallOutcome").addEventListener("click", submitCallOutcome);

  document.querySelectorAll("input[name='callOutcomeRadio']").forEach(radio => {
    radio.addEventListener("change", (e) => {
      const followupGroup = document.getElementById("groupFollowupDate");
      followupGroup.style.display = (e.target.value === "Follow-up Required") ? "block" : "none";
    });
  });

  // Agent workspace quick actions
  const btnNextCall = document.getElementById("btnInitiateNextCall");
  if (btnNextCall) {
    btnNextCall.addEventListener("click", () => {
      if (state.callingCustomer) initiateCallModal(state.callingCustomer);
    });
  }

  const btnGoQueue = document.getElementById("btnGoToFullQueue");
  if (btnGoQueue) {
    btnGoQueue.addEventListener("click", () => navigateToView("agent-queue"));
  }

  // Priority filter dropdown
  const selectPriority = document.getElementById("selectPriorityFilter");
  if (selectPriority) {
    selectPriority.addEventListener("change", () => {
      state.predictionsPage = 1;
      loadPredictions();
    });
  }

  // Prioritized Customers pagination
  const btnPredPrev = document.getElementById("btnPredictionsPrev");
  if (btnPredPrev) {
    btnPredPrev.addEventListener("click", () => {
      if ((state.predictionsPage || 1) > 1) {
        state.predictionsPage--;
        loadPredictions();
      }
    });
  }
  const btnPredNext = document.getElementById("btnPredictionsNext");
  if (btnPredNext) {
    btnPredNext.addEventListener("click", () => {
      state.predictionsPage = (state.predictionsPage || 1) + 1;
      loadPredictions();
    });
  }

  // Customer Pool pagination & search
  const btnCustPrev = document.getElementById("btnCustomerPrev");
  if (btnCustPrev) {
    btnCustPrev.addEventListener("click", () => {
      if ((state.customerPoolPage || 1) > 1) {
        state.customerPoolPage--;
        loadCustomerPool();
      }
    });
  }
  const btnCustNext = document.getElementById("btnCustomerNext");
  if (btnCustNext) {
    btnCustNext.addEventListener("click", () => {
      state.customerPoolPage = (state.customerPoolPage || 1) + 1;
      loadCustomerPool();
    });
  }
  const inputCustSearch = document.getElementById("inputCustomerSearch");
  if (inputCustSearch) {
    let searchTimeout = null;
    inputCustSearch.addEventListener("input", (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.customerPoolSearch = e.target.value.trim();
        state.customerPoolPage = 1;
        loadCustomerPool();
      }, 300);
    });
  }

  // Refresh button
  document.getElementById("btnRefreshData").addEventListener("click", () => {
    loadViewData(state.activeView);
    showToast("Dashboard synchronized with database.");
  });

  // Global search filtering
  document.getElementById("globalSearchInput").addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    const rows = document.querySelectorAll("tbody tr");
    rows.forEach(r => {
      const text = r.textContent.toLowerCase();
      r.style.display = text.includes(term) ? "" : "none";
    });
  });
}

// ============================================================================
// CHART.JS VISUALIZATION CONTROLLERS
// ============================================================================

function renderCallOutcomesChart(distribution) {
  const ctx = document.getElementById("chartCallOutcomes");
  if (!ctx) return;

  if (state.charts.callOutcomes) {
    state.charts.callOutcomes.destroy();
  }

  const labels = Object.keys(distribution);
  const data = Object.values(distribution);

  const colors = [
    "#10b981", // Subscribed (Emerald)
    "#3b82f6", // Interested (Blue)
    "#f59e0b", // Follow-up Required (Amber)
    "#94a3b8", // Unreachable (Grey)
    "#ef4444"  // Not Interested (Red)
  ];

  state.charts.callOutcomes = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: "#ffffff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 12, font: { size: 11, family: "Inter" } }
        }
      },
      cutout: "68%"
    }
  });
}

function renderAgentPerformanceChart(agentPerformance) {
  const ctx = document.getElementById("chartAgentPerformance");
  if (!ctx) return;

  if (state.charts.agentPerf) {
    state.charts.agentPerf.destroy();
  }

  const labels = agentPerformance.map(a => a.agent_name.split(" ")[0]);
  const callsCompleted = agentPerformance.map(a => a.calls_completed);
  const subscriptions = agentPerformance.map(a => a.successful_subscriptions);

  state.charts.agentPerf = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Calls Completed",
          data: callsCompleted,
          backgroundColor: "#1e40af",
          borderRadius: 6
        },
        {
          label: "Subscriptions",
          data: subscriptions,
          backgroundColor: "#10b981",
          borderRadius: 6
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top",
          labels: { boxWidth: 12, font: { size: 11, family: "Inter" } }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 11, family: "Inter" } },
          grid: { color: "#f1f5f9" }
        },
        x: {
          grid: { display: false },
          ticks: { font: { size: 11, family: "Inter" } }
        }
      }
    }
  });
}

function renderAnalyticsAgentsChart(agentPerformance) {
  const ctx = document.getElementById("chartAnalyticsAgents");
  if (!ctx) return;

  if (state.charts.analyticsAgents) {
    state.charts.analyticsAgents.destroy();
  }

  const labels = agentPerformance.map(a => a.agent_name);
  const conversionRates = agentPerformance.map(a => a.conversion_rate);

  state.charts.analyticsAgents = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Conversion Rate (%)",
        data: conversionRates,
        backgroundColor: "#0d9488",
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: { callback: v => v + "%" },
          grid: { color: "#f1f5f9" }
        },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderAnalyticsOutcomesChart(distribution) {
  const ctx = document.getElementById("chartAnalyticsOutcomes");
  if (!ctx) return;

  if (state.charts.analyticsOutcomes) {
    state.charts.analyticsOutcomes.destroy();
  }

  state.charts.analyticsOutcomes = new Chart(ctx, {
    type: "pie",
    data: {
      labels: Object.keys(distribution),
      datasets: [{
        data: Object.values(distribution),
        backgroundColor: ["#10b981", "#3b82f6", "#f59e0b", "#94a3b8", "#ef4444"],
        borderColor: "#ffffff",
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  navigateToView("leader-dashboard");
});
